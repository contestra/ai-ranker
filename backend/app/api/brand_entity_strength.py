"""
Brand Entity Strength Checker
Determines if a brand is a known entity in AI models (strong, weak, unknown)
Based on entity-checker V52 methodology
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, Literal
import sys
import io

def sanitize_for_windows(text: str) -> str:
    """Replace problematic Unicode characters for Windows"""
    if not text:
        return text
    
    if sys.platform == 'win32':
        # Turkish character replacements
        replacements = {
            '\u0130': 'I',  # Turkish İ
            '\u0131': 'i',  # Turkish ı  
            '\u015F': 's',  # Turkish ş
            '\u015E': 'S',  # Turkish Ş
            '\u011F': 'g',  # Turkish ğ
            '\u011E': 'G',  # Turkish Ğ
            '\u00E7': 'c',  # Turkish ç
            '\u00C7': 'C',  # Turkish Ç
            '\u00F6': 'o',  # Turkish ö
            '\u00D6': 'O',  # Turkish Ö
            '\u00FC': 'u',  # Turkish ü
            '\u00DC': 'U',  # Turkish Ü
            '\u2019': "'",  # Smart quote
            '\u2018': "'",  # Smart quote
            '\u201C': '"',  # Smart quote
            '\u201D': '"',  # Smart quote
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    return text
from pydantic import BaseModel
import json
from datetime import datetime
from json import JSONEncoder

class SafeJSONEncoder(JSONEncoder):
    """JSON encoder that handles encoding issues by replacing problematic characters"""
    def encode(self, o):
        # First convert to JSON string
        result = super().encode(o)
        # Then ensure it's safe for the response
        return result.encode('utf-8', errors='replace').decode('utf-8')
import httpx
from bs4 import BeautifulSoup
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings

router = APIRouter()

# Classification labels
EntityStrength = Literal["KNOWN_STRONG", "KNOWN_WEAK", "UNKNOWN", "EMPTY"]

class BrandEntityRequest(BaseModel):
    brand_name: str
    domain: Optional[str] = None  # e.g., "www.avea-life.com" - used to verify correct entity
    vendor: str = "openai"  # openai or google
    include_reasoning: bool = True

class EntityClassification(BaseModel):
    label: EntityStrength
    confidence: float  # 0-100
    reasoning: Optional[str] = None
    response_text: Optional[str] = None  # The AI's natural language response about the brand
    specific_claims: list[str] = []
    generic_claims: list[str] = []
    confusion_detected: Optional[bool] = False
    confusion_type: Optional[str] = None  # "wrong_entity", "mixed_entities", "disambiguation_needed"
    ai_thinks_industry: Optional[str] = None
    actual_industry: Optional[str] = None
    disambiguation_needed: Optional[bool] = False
    other_entities_list: Optional[list[str]] = []
    
class BrandEntityResponse(BaseModel):
    brand: str
    vendor: str
    classification: EntityClassification
    timestamp: datetime
    raw_response: Optional[str] = None

async def fetch_brand_info(domain: str) -> Dict[str, Any]:
    """
    Fetch and analyze a brand's website to understand what they actually do
    """
    if not domain:
        return {}
    
    # Clean up domain
    if not domain.startswith('http'):
        domain = f'https://{domain}'
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(domain)
            
            if response.status_code != 200:
                return {"error": f"Could not access website (status {response.status_code})"}
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key information
            title = soup.find('title')
            title_text = title.text.strip().lower() if title else ""
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = (meta_desc.get('content', '').lower() if meta_desc else "")
            
            # Also check Open Graph tags (common in Shopify)
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            og_description = (og_desc.get('content', '').lower() if og_desc else "")
            
            # Meta keywords (if present)
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            keywords_text = (meta_keywords.get('content', '').lower() if meta_keywords else "")
            
            # Extract text from common content areas in Shopify sites
            text_parts = []
            
            # Look for main content areas
            for selector in ['main', 'article', '.content', '.page-content', '.main-content']:
                elements = soup.select(selector)
                for elem in elements:
                    text_parts.append(elem.get_text(separator=' ', strip=True).lower())
            
            # Look for hero/banner text
            for selector in ['.hero', '.banner', '.hero-banner', 'section']:
                elements = soup.select(selector)
                for elem in elements[:3]:  # Just first few sections
                    text_parts.append(elem.get_text(separator=' ', strip=True).lower())
            
            # Look for headings which often contain key info
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                text_parts.append(heading.get_text(strip=True).lower())
            
            # Look for product-related content
            for selector in ['.product', '.collection', '.product-title', '.product-description']:
                elements = soup.select(selector)
                for elem in elements[:5]:  # First few products
                    text_parts.append(elem.get_text(separator=' ', strip=True).lower())
            
            # Combine unique text parts
            page_text = ' '.join(text_parts)[:5000]  # More text to analyze
            
            # Also get general text content as fallback
            general_text = soup.get_text(separator=' ', strip=True).lower()[:3000]
            
            # Combine all text sources for better detection
            combined_text = f"{title_text} {description} {og_description} {keywords_text} {page_text} {general_text}"
            
            # Remove excessive whitespace
            combined_text = ' '.join(combined_text.split())
            
            # Industry indicators - expanded for better detection
            industries = {
                "health/wellness": ["supplement", "health", "wellness", "nutrition", "vitamin", "longevity", 
                                  "nmn", "nad+", "nad", "collagen", "anti-aging", "antiaging", "vitality",
                                  "energy", "immune", "cellular", "mitochondria", "resveratrol", "quercetin"],
                "telecommunications": ["telecom", "mobile", "carrier", "network", "5g", "4g", "sim", 
                                      "roaming", "operator", "cellular service", "wireless", "phone plan"],
                "software/tech": ["software", "app", "platform", "api", "cloud", "saas", "technology", "digital"],
                "finance": ["bank", "finance", "investment", "trading", "payment", "crypto", "loan", "credit"],
                "retail": ["shop", "store", "buy", "cart", "product", "merchandise", "clothing", "fashion"],
                "media": ["news", "media", "publishing", "content", "video", "streaming", "broadcast"],
            }
            
            detected_industries = []
            for industry, keywords in industries.items():
                count = sum(1 for kw in keywords if kw in combined_text)
                if count >= 2:  # At least 2 keywords to qualify
                    detected_industries.append((industry, count))
            
            # Sort by relevance
            detected_industries.sort(key=lambda x: x[1], reverse=True)
            
            # No special cases for specific brands - let the generic detection work
            
            return {
                "domain": domain,
                "title": title_text,
                "description": description or og_description,
                "primary_industry": detected_industries[0][0] if detected_industries else "unknown",
                "all_industries": [ind[0] for ind in detected_industries],
                "industry_confidence": min(detected_industries[0][1] * 10, 90) if detected_industries else 0
            }
            
    except Exception as e:
        return {"error": str(e)}

def create_probe_prompt(brand_name: str, industry_hint: Optional[str] = None) -> tuple[str, str]:
    """
    Create the system and user prompts for entity checking
    """
    system_prompt = """You are evaluating whether a brand/company is genuinely known to you.

Classify responses into one of these categories:
- OK_STRONG: You have specific, verifiable facts about this real entity (founding date, location, products, leadership, etc.)
- OK_WEAK: You recognize the name or have some context but lack specific details
- CLARIFY: You have no information about this brand - it's completely unknown to you
- BLOCKED: You cannot or will not provide information

Important: 
1. Be honest about what you don't know. If you have zero information about a brand, classify it as CLARIFY.
2. If multiple entities share the same name, mention all of them and indicate which one you know best.
3. If an industry hint is provided, focus on that specific entity.

Be honest about what you actually know vs. what you're inferring."""

    # Adjust prompt based on industry hint
    if industry_hint:
        user_prompt = f"""Tell me about {brand_name} (the {industry_hint} company). What do they do, where are they based, and what are they known for?

IMPORTANT: Focus specifically on the {industry_hint} company called {brand_name}, not other companies with similar names.

Provide your response in this JSON format:
{{
    "classification": "OK_STRONG|OK_WEAK|CLARIFY|HALLUCINATION|BLOCKED",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your classification",
    "specific_claims": ["List of specific, verifiable facts you know"],
    "generic_claims": ["List of generic or inferred statements"],
    "response_text": "Your natural language response about the brand",
    "disambiguation_needed": true/false,
    "other_entities": ["List of other entities with the same name if any"]
}}"""
    else:
        user_prompt = f"""Tell me about {brand_name}. What do they do, where are they based, and what are they known for?

Provide your response in this JSON format:
{{
    "classification": "OK_STRONG|OK_WEAK|CLARIFY|HALLUCINATION|BLOCKED",
    "confidence": 0-100,
    "reasoning": "Brief explanation of your classification",
    "specific_claims": ["List of specific, verifiable facts you know"],
    "generic_claims": ["List of generic or inferred statements"],
    "response_text": "Your natural language response about the brand",
    "disambiguation_needed": true/false,
    "other_entities": ["List of other entities with the same name if any"]
}}"""

    return system_prompt, user_prompt

def classify_response(response_data: Dict[str, Any], brand_name: str = None, brand_info: Dict[str, Any] = None) -> EntityClassification:
    """
    Process the model's response and classify entity strength
    """
    # Map internal labels to public labels
    label_map = {
        "OK_STRONG": "KNOWN_STRONG",
        "OK_WEAK": "KNOWN_WEAK",
        "CLARIFY": "UNKNOWN",
        "BLOCKED": "EMPTY"
    }
    
    raw_label = response_data.get("classification", "CLARIFY")
    label = label_map.get(raw_label, "UNKNOWN")
    
    # Extract confidence score
    confidence = float(response_data.get("confidence", 30))  # Default to low confidence
    
    # Check if disambiguation is needed (multiple entities with same name)
    disambiguation_needed = response_data.get("disambiguation_needed", False)
    other_entities = response_data.get("other_entities", [])
    
    # Store disambiguation info but don't change label yet - do wrong entity check first
    if disambiguation_needed and other_entities:
        # Prepare disambiguation info for user
        response_data["disambiguation_needed"] = True
        response_data["other_entities_list"] = other_entities
    
    # Check for wrong entity confusion indicators
    response_text = response_data.get("response_text", "").lower()
    specific_claims = [claim.lower() for claim in response_data.get("specific_claims", [])]
    all_text = response_text + " ".join(specific_claims)
    
    # Look for phrases that indicate confusion or multiple entities
    confusion_indicators = [
        "may also refer to",
        "other entities named",
        "without clarification",
        "most common reference",
        "now folded into",
        "formerly known as",
        "merged with",
        "acquired by",
        "there are other",
        "multiple companies",
        "disambiguation",
        "not to be confused with"
    ]
    
    has_confusion = any(indicator in all_text for indicator in confusion_indicators)
    
    # If we have actual brand info from their website, check for industry mismatch
    if brand_info and brand_info.get("primary_industry"):
        actual_industry = brand_info["primary_industry"]
        
        # Map industries to keywords that would appear in GPT's response
        industry_indicators = {
            "health/wellness": ["supplement", "health", "wellness", "nutrition", "vitamin", "longevity", "nmn", "nad", "collagen", "swiss longevity", "aging", "anti-aging"],
            "telecommunications": ["telecom", "mobile", "carrier", "network", "5g", "4g", "sim", "roaming", "operator"],
            "software/tech": ["software", "app", "platform", "api", "cloud", "saas", "technology", "digital"],
            "finance": ["bank", "finance", "investment", "trading", "payment", "crypto", "loan", "credit"],
            "retail": ["shop", "store", "retail", "merchandise", "clothing", "fashion", "ecommerce"],
            "media": ["news", "media", "publishing", "content", "video", "streaming", "broadcast"],
        }
        
        # Check if GPT's response matches the actual industry
        if actual_industry in industry_indicators:
            expected_keywords = industry_indicators[actual_industry]
            has_correct_industry = any(kw in all_text for kw in expected_keywords)
            
            # Check if GPT is talking about a different industry
            wrong_industry = False
            for other_industry, other_keywords in industry_indicators.items():
                if other_industry != actual_industry:
                    if sum(1 for kw in other_keywords if kw in all_text) >= 3:  # Strong signal of wrong industry
                        wrong_industry = other_industry
                        break
            
            if wrong_industry and not has_correct_industry:
                # GPT is definitely talking about wrong entity
                # But if there's disambiguation, keep it as WEAK not UNKNOWN
                if response_data.get("disambiguation_needed") or response_data.get("other_entities"):
                    label = "KNOWN_WEAK"
                    confidence = min(confidence, 40)
                    response_data["reasoning"] = f"AI recognizes multiple entities named '{brand_name}' but primarily associates it with {wrong_industry} industry, not your {actual_industry} business."
                else:
                    label = "UNKNOWN" 
                    confidence = 20
                    response_data["reasoning"] = f"AI identified a {wrong_industry} company, but actual brand is {actual_industry}. The AI is confusing your brand with a different company."
                # Add confusion details to help user understand
                response_data["confusion_detected"] = True
                response_data["ai_thinks_industry"] = wrong_industry
                response_data["actual_industry"] = actual_industry
            elif has_confusion or (wrong_industry and has_correct_industry):
                # Mixed signals - downgrade confidence
                if label == "KNOWN_STRONG":
                    label = "KNOWN_WEAK"
                    confidence = min(confidence, 50)
                response_data["reasoning"] = f"Possible confusion detected: Your brand operates in {actual_industry} but AI also mentions {wrong_industry or 'multiple industries'}. The AI may be mixing up multiple companies with similar names."
                response_data["confusion_detected"] = True
                response_data["confusion_type"] = "mixed_entities"
    
    # If there's general confusion but no brand info to verify against
    elif has_confusion:
        if label == "KNOWN_STRONG":
            label = "KNOWN_WEAK"
            confidence = min(confidence, 60)
        response_data["reasoning"] = "Multiple entities with this name exist; disambiguation needed"
    
    # Adjust confidence based on classification
    if label == "KNOWN_STRONG" and len(response_data.get("specific_claims", [])) < 2:
        # Downgrade if not enough specific claims
        label = "KNOWN_WEAK"
        confidence = min(confidence, 60)
    elif label == "KNOWN_WEAK" and len(response_data.get("specific_claims", [])) > 3:
        # Upgrade if many specific claims
        label = "KNOWN_STRONG"
        confidence = max(confidence, 70)
    elif label == "UNKNOWN":
        # For completely unknown brands, cap the confidence
        specific_claims = response_data.get("specific_claims", [])
        generic_claims = response_data.get("generic_claims", [])
        
        # If model has zero information, ensure low confidence
        if len(specific_claims) == 0 and len(generic_claims) == 0:
            confidence = min(confidence, 30)  # Very low confidence for unknowns
    
    # FINAL CHECK: If disambiguation is needed, downgrade strength
    # This happens AFTER all other checks to ensure it takes precedence
    if disambiguation_needed and other_entities:
        if label == "KNOWN_STRONG":
            label = "KNOWN_WEAK"  # Downgrade because brand isn't uniquely identified
        confidence = min(confidence, 60)  # Cap confidence at 60%
        
        # Update reasoning if not already set
        if "Multiple entities" not in response_data.get("reasoning", ""):
            entities_str = "; ".join(other_entities[:3])  # Show first 3
            response_data["reasoning"] = f"Multiple entities share the name '{brand_name}': {entities_str}. Your brand lacks unique recognition in AI systems."
    
    # Clean all string fields to avoid encoding issues
    def clean_string(s):
        if s:
            return s.encode('utf-8', errors='replace').decode('utf-8')
        return s
    
    def clean_list(lst):
        return [clean_string(item) for item in lst] if lst else []
    
    return EntityClassification(
        label=label,
        confidence=confidence,
        reasoning=clean_string(response_data.get("reasoning")),
        response_text=clean_string(response_data.get("response_text")),  # Add the AI's response text
        specific_claims=clean_list(response_data.get("specific_claims", [])),
        generic_claims=clean_list(response_data.get("generic_claims", [])),
        confusion_detected=response_data.get("confusion_detected", False),
        confusion_type=response_data.get("confusion_type"),
        ai_thinks_industry=clean_string(response_data.get("ai_thinks_industry")),
        actual_industry=clean_string(response_data.get("actual_industry")),
        disambiguation_needed=response_data.get("disambiguation_needed", False),
        other_entities_list=clean_list(response_data.get("other_entities_list", []))
    )

@router.post("/brand-entity-strength") 
async def check_brand_entity_strength(request: BrandEntityRequest):
    """
    Check if a brand is a known entity in the AI model
    Returns classification of entity strength with confidence score
    """
    
    adapter = LangChainAdapter()
    
    # Fetch actual brand info from their website if domain provided
    brand_info = {}
    if request.domain:
        brand_info = await fetch_brand_info(request.domain)
        # print(f"DEBUG: Brand info for {request.domain}: {brand_info}")
    
    # Create probe prompts WITHOUT industry hint - we want naked brand token!
    # The brand_info is only used AFTER to check if GPT is talking about the right entity
    system_prompt, user_prompt = create_probe_prompt(request.brand_name, industry_hint=None)
    
    try:
        # Query the model
        # Note: Using GPT-4 Turbo as GPT-5 returns empty responses
        temperature = 0.3  # Lower temperature for more consistent results
        
        # GPT-4 needs sufficient tokens for detailed responses
        max_tokens = 2000 if request.vendor == "openai" else 500
        
        try:
            import asyncio
            # Add timeout for LLM generation (60 seconds for GPT-4, 30 for others)
            timeout_seconds = 60 if request.vendor == "openai" else 30
            
            response = await asyncio.wait_for(
                adapter.generate(
                    vendor=request.vendor,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # If GPT-5 times out, return a meaningful response
            if request.vendor == "openai":
                # Return a timeout response that indicates GPT-5 is being slow
                response = {
                    "text": json.dumps({
                        "classification": "CLARIFY",
                        "confidence": 0,
                        "reasoning": "GPT-5 response timed out after 90 seconds. The model is experiencing delays.",
                        "specific_claims": [],
                        "generic_claims": [],
                        "response_text": "Request timed out - GPT-5 is currently very slow",
                        "disambiguation_needed": False,
                        "other_entities": []
                    })
                }
            else:
                raise HTTPException(status_code=504, detail="LLM request timed out")
        except Exception as gen_error:
            # Sanitize error message
            safe_error = str(gen_error).encode('ascii', errors='replace').decode('ascii')
            raise HTTPException(status_code=500, detail=f"LLM generation error: {safe_error}")
        
        response_text = response.get("text", "")
        
        # Sanitize for Windows encoding issues IMMEDIATELY
        response_text = sanitize_for_windows(response_text)
        
        if not response_text:
            # print("WARNING: Empty response from GPT-5")
            pass
        
        # Try to parse JSON response
        response_data = {}
        json_parsed = False
        
        # Extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                # Clean up any encoding issues in the JSON
                json_str = json_str.encode('utf-8', errors='replace').decode('utf-8')
                response_data = json.loads(json_str)
                json_parsed = True
                # Log what fields are in the JSON for debugging
                with open('json_fields.log', 'w', encoding='utf-8') as f:
                    f.write(f"Fields in parsed JSON: {list(response_data.keys())}\n")
                    if 'response_text' in response_data:
                        f.write(f"response_text found: {response_data['response_text'][:100]}...\n")
                    else:
                        f.write("No response_text field in JSON\n")
            except (json.JSONDecodeError, UnicodeError) as e:
                json_parsed = False
        else:
            # No JSON found in response
            json_parsed = False
        
        # Only use fallback if JSON parsing failed
        if not json_parsed:
            # Using fallback parsing
            
            # Fallback: analyze response text manually
            response_lower = response_text.lower()
            
            if "i don't have" in response_lower or "i'm not aware" in response_lower or response_text.strip() == "":
                response_data = {
                    "classification": "CLARIFY",
                    "confidence": 20,  # Very low confidence for complete unknowns
                    "reasoning": "Model has no knowledge of this brand",
                    "response_text": response_text,  # Include the actual response
                    "specific_claims": [],
                    "generic_claims": []
                }
            elif "cannot provide" in response_lower or "unable to" in response_lower:
                response_data = {
                    "classification": "BLOCKED",
                    "confidence": 90,
                    "reasoning": "Model refused to provide information",
                    "response_text": response_text,
                    "specific_claims": [],
                    "generic_claims": []
                }
            else:
                # Try to determine from content
                specific_indicators = ["founded in", "headquartered in", "ceo", "$", "employees", "acquired"]
                specific_count = sum(1 for ind in specific_indicators if ind in response_lower)
                
                if specific_count >= 3:
                    response_data = {
                        "classification": "OK_STRONG",
                        "confidence": 70,
                        "reasoning": "Response contains specific details",
                        "response_text": response_text,
                        "specific_claims": [],
                        "generic_claims": []
                    }
                else:
                    response_data = {
                        "classification": "OK_WEAK",
                        "confidence": 50,
                        "reasoning": "Response is generic",
                        "response_text": response_text,
                        "specific_claims": [],
                        "generic_claims": []
                    }
        
        # Clean up response_data to avoid encoding issues
        if response_data:
            # Clean all string fields in response_data including response_text
            for key in ['reasoning', 'response_text']:
                if key in response_data and response_data[key]:
                    response_data[key] = sanitize_for_windows(response_data[key])
            
            # Clean lists of strings
            for key in ['specific_claims', 'generic_claims', 'other_entities']:
                if key in response_data and response_data[key]:
                    response_data[key] = [
                        sanitize_for_windows(claim) 
                        for claim in response_data[key]
                    ]
            
            # Successfully parsed the response
            with open('parse_fields.log', 'w', encoding='utf-8') as f:
                f.write(f"Parsed JSON fields: {list(response_data.keys())}\n")
                f.write(f"Has response_text: {'response_text' in response_data}\n")
        
        # Classify the response with brand name and actual brand info for disambiguation detection
        try:
            classification = classify_response(response_data, request.brand_name, brand_info)
        except Exception as e:
            # Safe error logging
            safe_error = str(e).encode('ascii', errors='replace').decode('ascii')
            import traceback
            # Write traceback to file instead of printing
            with open('error_log.txt', 'a', encoding='utf-8') as f:
                f.write(f"\nERROR in classify_response: {safe_error}\n")
                traceback.print_exc(file=f)
            raise HTTPException(status_code=500, detail=f"Classification error: {safe_error}")
        
        # Clean the raw response text to avoid encoding issues
        cleaned_response = None
        if request.include_reasoning and response_text:
            cleaned_response = response_text.encode('utf-8', errors='replace').decode('utf-8')
        
        # Create response without datetime object to avoid serialization issues
        response_data = {
            "brand": request.brand_name,
            "vendor": request.vendor,
            "classification": classification.dict(),
            "timestamp": datetime.now().isoformat(),
            "raw_response": cleaned_response
        }
        
        # Convert to dict and clean all strings recursively
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [clean_dict(v) for v in d]
            elif isinstance(d, str):
                return d.encode('utf-8', errors='replace').decode('utf-8')
            elif hasattr(d, 'isoformat'):  # Handle datetime objects
                return d.isoformat()
            else:
                return d
        
        # Clean all strings in the response
        response_data = clean_dict(response_data)
        
        # Return as regular dict - FastAPI will handle JSON serialization
        return response_data
        
    except Exception as e:
        import traceback
        # Write the actual error to a log file
        with open('api_error.log', 'w', encoding='utf-8') as f:
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
        
        # Sanitize error message to avoid encoding issues  
        error_msg = str(e).encode('ascii', errors='replace').decode('ascii')
        raise HTTPException(status_code=500, detail=f"Error checking brand entity: {error_msg}")

class BatchEntityRequest(BaseModel):
    brands: list[str]
    vendor: str = "openai"

@router.post("/brand-entity-strength/batch")
async def check_multiple_brands(request: BatchEntityRequest):
    """
    Check multiple brands at once
    """
    results = []
    
    for brand in request.brands[:10]:  # Limit to 10 for safety
        try:
            entity_request = BrandEntityRequest(brand_name=brand, vendor=request.vendor, include_reasoning=False)
            result = await check_brand_entity_strength(entity_request)
            # Result is now a dict, not a BrandEntityResponse object
            results.append({
                "brand": brand,
                "strength": result["classification"]["label"],
                "confidence": result["classification"]["confidence"]
            })
        except Exception as e:
            results.append({
                "brand": brand,
                "strength": "ERROR",
                "confidence": 0,
                "error": str(e)
            })
    
    return {"results": results}