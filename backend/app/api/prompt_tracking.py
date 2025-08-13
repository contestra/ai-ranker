"""
API endpoints for Prompt Tracking feature
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json
import asyncio
from sqlalchemy import text

from app.database import get_db, engine
from app.llm.langchain_adapter import LangChainAdapter
from app.config import settings
from app.services.evidence_pack_builder import evidence_pack_builder
from app.services.als import als_service
from app.services.als.country_codes import country_to_num, num_to_country

router = APIRouter(prefix="/api/prompt-tracking", tags=["prompt-tracking"])

# Pydantic models
class PromptTemplate(BaseModel):
    brand_name: str
    template_name: str
    prompt_text: str
    prompt_type: str = "custom"
    model_name: str = "gemini"  # Default model for the template
    countries: List[str] = ["US"]
    grounding_modes: List[str] = ["none"]
    is_active: bool = True

class PromptRunRequest(BaseModel):
    template_id: int
    brand_name: str
    model_name: str = "gemini"  # Default to Gemini since GPT-5 returns empty
    countries: Optional[List[str]] = None
    grounding_modes: Optional[List[str]] = None

class PromptSchedule(BaseModel):
    template_id: int
    schedule_type: str  # 'daily', 'weekly', 'monthly'
    run_time: str  # HH:MM format
    timezone: str = "UTC"
    is_active: bool = True

@router.get("/templates")
async def get_templates(brand_name: Optional[str] = None):
    """Get all prompt templates, optionally filtered by brand"""
    with engine.connect() as conn:
        if brand_name:
            query = text("""
                SELECT id, brand_name, template_name, prompt_text, prompt_type, 
                       countries, grounding_modes, is_active, created_at, updated_at, model_name
                FROM prompt_templates 
                WHERE brand_name = :brand OR brand_name = 'DEFAULT'
                ORDER BY created_at DESC
            """)
            result = conn.execute(query, {"brand": brand_name})
        else:
            query = text("""
                SELECT id, brand_name, template_name, prompt_text, prompt_type, 
                       countries, grounding_modes, is_active, created_at, updated_at, model_name
                FROM prompt_templates 
                ORDER BY created_at DESC
            """)
            result = conn.execute(query)
        
        templates = []
        for row in result:
            # Handle JSON strings for SQLite compatibility
            countries = row.countries
            if isinstance(countries, str):
                import json as json_lib
                countries = json_lib.loads(countries)
            
            grounding_modes = row.grounding_modes
            if isinstance(grounding_modes, str):
                import json as json_lib
                grounding_modes = json_lib.loads(grounding_modes)
            
            # Handle datetime - SQLite returns string, PostgreSQL returns datetime
            created_at = row.created_at
            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            
            # Get model_name with fallback to default
            model_name = row.model_name if hasattr(row, 'model_name') and row.model_name else 'gemini'
            
            templates.append({
                "id": row.id,
                "brand_name": row.brand_name,
                "template_name": row.template_name,
                "prompt_text": row.prompt_text,
                "prompt_type": row.prompt_type,
                "model_name": model_name,
                "countries": countries,
                "grounding_modes": grounding_modes,
                "is_active": row.is_active,
                "created_at": created_at
            })
        
        return {"templates": templates}

@router.post("/templates")
async def create_template(template: PromptTemplate):
    """Create a new prompt template"""
    with engine.begin() as conn:
        query = text("""
            INSERT INTO prompt_templates 
            (brand_name, template_name, prompt_text, prompt_type, model_name, countries, grounding_modes, is_active)
            VALUES (:brand, :name, :text, :type, :model, :countries, :modes, :active)
            RETURNING id
        """)
        
        # Convert arrays to JSON strings for SQLite
        import json as json_lib
        countries_json = json_lib.dumps(template.countries)
        modes_json = json_lib.dumps(template.grounding_modes)
        
        result = conn.execute(query, {
            "brand": template.brand_name,
            "name": template.template_name,
            "text": template.prompt_text,
            "type": template.prompt_type,
            "model": template.model_name,
            "countries": countries_json,
            "modes": modes_json,
            "active": template.is_active
        })
        
        template_id = result.fetchone()[0]
        
        return {"id": template_id, "message": "Template created successfully"}

@router.put("/templates/{template_id}")
async def update_template(template_id: int, template: PromptTemplate):
    """Update an existing prompt template"""
    with engine.begin() as conn:
        # Check if template exists
        check_query = text("SELECT id FROM prompt_templates WHERE id = :id")
        result = conn.execute(check_query, {"id": template_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Update template
        update_query = text("""
            UPDATE prompt_templates 
            SET template_name = :name, 
                prompt_text = :text, 
                prompt_type = :type,
                model_name = :model,
                countries = :countries,
                grounding_modes = :modes
            WHERE id = :id
        """)
        
        import json as json_lib
        countries_json = json_lib.dumps(template.countries)
        modes_json = json_lib.dumps(template.grounding_modes)
        
        conn.execute(update_query, {
            "id": template_id,
            "name": template.template_name,
            "text": template.prompt_text,
            "type": template.prompt_type,
            "model": template.model_name,
            "countries": countries_json,
            "modes": modes_json
        })
        
        return {"message": "Template updated successfully"}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: int):
    """Delete a prompt template"""
    with engine.begin() as conn:
        # Check if template exists
        check_query = text("SELECT id FROM prompt_templates WHERE id = :id")
        result = conn.execute(check_query, {"id": template_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Delete template (cascade will delete related runs and results)
        delete_query = text("DELETE FROM prompt_templates WHERE id = :id")
        conn.execute(delete_query, {"id": template_id})
        
        return {"message": "Template deleted successfully"}

@router.post("/run")
async def run_prompt(request: PromptRunRequest):
    """Execute a prompt template and get results - now with parallel execution!"""
    
    # Import parallel execution helper
    from app.api.prompt_tracking_parallel import run_parallel_tests
    
    # Get the template
    with engine.connect() as conn:
        template_query = text("SELECT * FROM prompt_templates WHERE id = :id")
        template = conn.execute(template_query, {"id": request.template_id}).fetchone()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
    
    # Parse JSON fields if needed
    template_countries = template.countries
    if isinstance(template_countries, str):
        import json as json_lib
        template_countries = json_lib.loads(template_countries)
    
    template_modes = template.grounding_modes
    if isinstance(template_modes, str):
        import json as json_lib
        template_modes = json_lib.loads(template_modes)
    
    # Prepare the prompt with brand name
    prompt_text = template.prompt_text.replace("{brand_name}", request.brand_name)
    
    # Determine countries and grounding modes to test
    countries = request.countries or template_countries or ["US"]
    grounding_modes = request.grounding_modes or template_modes or ["none"]
    
    # Check if we need parallel execution (more than 2 tests)
    total_tests = len(countries) * len(grounding_modes)
    
    if total_tests > 2:
        # Use parallel execution for multiple tests
        results = await run_parallel_tests(
            request.template_id,
            request.brand_name,
            request.model_name,
            prompt_text,
            countries,
            grounding_modes
        )
    else:
        # Use sequential execution for 1-2 tests
        results = []
        
        for country_orig in countries:
            # Immediately convert to numeric to avoid any "DE" leakage
            country_num = country_to_num(country_orig)
            country_iso = country_orig  # Keep ISO for ALS lookup only
            
            for grounding_mode in grounding_modes:
                # Use numeric ID everywhere except ALS building
                
                # Create NEW adapter instance for each test to avoid state pollution
                adapter = LangChainAdapter()
                # Create a run record
                with engine.begin() as conn:
                    run_query = text("""
                    INSERT INTO prompt_runs 
                    (template_id, brand_name, model_name, country_code, grounding_mode, status, started_at)
                    VALUES (:template_id, :brand, :model, :country, :grounding, 'running', datetime('now'))
                    RETURNING id
                """)
                
                run_result = conn.execute(run_query, {
                    "template_id": request.template_id,
                    "brand": request.brand_name,
                    "model": request.model_name,
                    "country": country_iso,  # Store ISO in DB for display
                    "grounding": grounding_mode
                })
                run_id = run_result.fetchone()[0]
            
            try:
                # Build Ambient Block for country-specific testing
                ambient_block = ""
                if country_num != 0:  # 0 is NONE
                    # Use Ambient Blocks for clean, minimal civic signals
                    # This avoids commercial content that could bias results
                    if country_iso in ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']:
                        try:
                            ambient_block = als_service.build_als_block(country_iso)  # ALS needs ISO code
                        except Exception as e:
                            print(f"Failed to build Ambient Block for numeric {country_num} (ISO: {country_iso}): {e}")
                            ambient_block = ""
                    else:
                        # Fallback for unsupported countries - use evidence pack
                        country_queries = {
                            'CH': 'SBB Fahrplan Zürich Halbtax',
                            'US': 'DMV license renewal California IRS tax forms',
                            'GB': 'NHS appointment booking UK driving licence DVLA',
                            'DE': 'Führerschein verlängern Deutsche Bahn AOK Krankenkasse',
                            'AE': 'Dubai RTA metro card Emirates ID renewal',
                            'SG': 'CPF contribution Singapore MRT card SingPass'
                        }
                        search_query = country_queries.get(country, 'health supplements pharmacy')
                        ambient_block = await evidence_pack_builder.build_evidence_pack(
                            search_query,
                            country,
                            max_snippets=5,
                            max_tokens=600
                        )
                
                # Prepare prompt based on mode
                if country_num == 0:  # NONE
                    # Base model testing - no location context at all
                    if grounding_mode == "web":
                        full_prompt = f"""Please use web search to answer this question accurately:

{prompt_text}"""
                    else:
                        full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
                    context_message = None
                else:
                    # Country-specific testing - Ambient Block as SEPARATE message
                    if ambient_block:
                        # Keep prompt NAKED - Ambient Block goes in separate context message
                        full_prompt = prompt_text  # UNMODIFIED user prompt
                        context_message = ambient_block  # Ambient Block as separate message
                    else:
                        # Fallback if no evidence pack
                        if grounding_mode == "web":
                            full_prompt = f"""Please use web search to answer this question accurately:

{prompt_text}"""
                        else:
                            full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
                        context_message = None
                
                # DEBUG: Log what we're about to send
                print(f"\n{'='*60}")
                print(f"PROMPT TRACKING API - ABOUT TO SEND:")
                print(f"Using numeric ID: {country_num} internally (never passing ISO '{country_iso}' to AI)")
                print(f"Model: {request.model_name}")
                print(f"Naked Prompt: {full_prompt[:100]}...")
                print(f"Has Ambient Block: {bool(context_message)}")
                if context_message:
                    print(f"Ambient Block preview: {context_message[:100]}...")
                print(f"{'='*60}\n")
                
                # Use fixed parameters for reproducibility
                temperature = 0.0  # Deterministic
                seed = 42  # Fixed seed for reproducibility
                
                # Get model response based on selected model
                # Now passing context as SEPARATE parameter, not concatenated!
                if request.model_name in ["gemini", "gemini-flash"]:
                    response_data = await adapter.analyze_with_gemini(
                        full_prompt,  # Naked prompt
                        grounding_mode == "web",  # Enable grounding for web mode
                        model_name="gemini-2.0-flash-exp" if request.model_name == "gemini-flash" else "gemini-2.5-pro",
                        temperature=temperature,
                        seed=seed,
                        context=context_message  # Context as separate parameter
                    )
                elif request.model_name in ["gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4o", "gpt-4o-mini"]:
                    # Use GPT models (note: GPT-5 models currently return empty responses)
                    response_data = await adapter.analyze_with_gpt4(
                        full_prompt,  # Naked prompt
                        model_name=request.model_name,
                        temperature=temperature,
                        seed=seed,
                        context=context_message  # Context as separate parameter
                    )
                else:
                    # Default fallback to Gemini
                    response_data = await adapter.analyze_with_gemini(
                        full_prompt,  # Naked prompt
                        grounding_mode == "web",
                        temperature=temperature,
                        seed=seed,
                        context=context_message  # Context as separate parameter
                    )
                
                # Extract response content and metadata
                response = response_data.get("content", "") if isinstance(response_data, dict) else str(response_data)
                
                # Analyze the response for brand mentions
                brand_mentioned = request.brand_name.lower() in response.lower()
                mention_count = response.lower().count(request.brand_name.lower())
                
                # Extract competitor mentions (simple approach)
                competitors = []
                competitor_keywords = ["competitor", "alternative", "rival", "competes with", "similar to"]
                for keyword in competitor_keywords:
                    if keyword in response.lower():
                        # Extract sentence containing the keyword
                        sentences = response.split('.')
                        for sentence in sentences:
                            if keyword in sentence.lower():
                                competitors.append(sentence.strip())
                
                # Save the result (simplified schema)
                with engine.begin() as conn:
                    result_query = text("""
                        INSERT INTO prompt_results 
                        (run_id, prompt_text, model_response, brand_mentioned, mention_count, 
                         competitors_mentioned, confidence_score)
                        VALUES (:run_id, :prompt, :response, :mentioned, :count, 
                                :competitors, :confidence)
                        RETURNING id
                    """)
                    
                    # Convert list to JSON string for SQLite
                    import json as json_lib
                    competitors_json = json_lib.dumps(competitors[:5] if competitors else [])
                    
                    conn.execute(result_query, {
                        "run_id": run_id,
                        "prompt": full_prompt,  # Save the full prompt with evidence pack
                        "response": response,
                        "mentioned": brand_mentioned,
                        "count": mention_count,
                        "competitors": competitors_json,
                        "confidence": 0.8 if brand_mentioned else 0.3
                    })
                    
                    # Update run status
                    update_query = text("""
                        UPDATE prompt_runs 
                        SET status = 'completed', completed_at = datetime('now')
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {"id": run_id})
                
                results.append({
                    "run_id": run_id,
                    "country": country_iso,  # Return ISO for display
                    "grounding_mode": grounding_mode,
                    "brand_mentioned": brand_mentioned,
                    "mention_count": mention_count,
                    "response_preview": response[:200] + "..." if len(response) > 200 else response
                })
                
            except Exception as e:
                # Update run with error
                with engine.begin() as conn:
                    error_query = text("""
                        UPDATE prompt_runs 
                        SET status = 'failed', error_message = :error, completed_at = datetime('now')
                        WHERE id = :id
                    """)
                    conn.execute(error_query, {"id": run_id, "error": str(e)})
                
                results.append({
                    "run_id": run_id,
                    "country": country_iso,  # Return ISO for display
                    "grounding_mode": grounding_mode,
                    "error": str(e)
                })
    
    return {
        "template_name": template.template_name,
        "brand_name": request.brand_name,
        "results": results
    }

@router.get("/runs")
async def get_runs(
    brand_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get prompt run history"""
    with engine.connect() as conn:
        query_parts = ["SELECT * FROM prompt_runs WHERE 1=1"]
        params = {}
        
        if brand_name:
            query_parts.append("AND brand_name = :brand")
            params["brand"] = brand_name
        
        if status:
            query_parts.append("AND status = :status")
            params["status"] = status
        
        query_parts.append("ORDER BY created_at DESC")
        query_parts.append("LIMIT :limit")
        params["limit"] = limit
        
        query = text(" ".join(query_parts))
        result = conn.execute(query, params)
        
        runs = []
        for row in result:
            runs.append({
                "id": row.id,
                "template_id": row.template_id,
                "brand_name": row.brand_name,
                "model_name": row.model_name,
                "country_code": row.country_code,
                "grounding_mode": row.grounding_mode,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at and hasattr(row.started_at, 'isoformat') else row.started_at,
                "completed_at": row.completed_at.isoformat() if row.completed_at and hasattr(row.completed_at, 'isoformat') else row.completed_at,
                "error_message": row.error_message,
                "created_at": row.created_at.isoformat() if row.created_at and hasattr(row.created_at, 'isoformat') else row.created_at
            })
        
        return {"runs": runs}

@router.get("/results/{run_id}")
async def get_run_results(run_id: int):
    """Get detailed results for a specific run"""
    with engine.connect() as conn:
        # Get run info
        run_query = text("SELECT * FROM prompt_runs WHERE id = :id")
        run = conn.execute(run_query, {"id": run_id}).fetchone()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Get results
        results_query = text("SELECT * FROM prompt_results WHERE run_id = :id")
        result = conn.execute(results_query, {"id": run_id}).fetchone()
        
        if not result:
            return {
                "run": {
                    "id": run.id,
                    "status": run.status,
                    "error_message": run.error_message
                },
                "result": None
            }
        
        # Parse JSON fields if needed
        competitors = result.competitors_mentioned
        if isinstance(competitors, str):
            import json as json_lib
            competitors = json_lib.loads(competitors)
        
        return {
            "run": {
                "id": run.id,
                "brand_name": run.brand_name,
                "model_name": run.model_name,
                "country_code": run.country_code,
                "grounding_mode": run.grounding_mode,
                "status": run.status,
                "completed_at": run.completed_at.isoformat() if run.completed_at and hasattr(run.completed_at, 'isoformat') else run.completed_at
            },
            "result": {
                "prompt_text": result.prompt_text,
                "model_response": result.model_response,
                "brand_mentioned": result.brand_mentioned,
                "mention_count": result.mention_count,
                "competitors_mentioned": competitors,
                "confidence_score": result.confidence_score
            }
        }

@router.get("/analytics/{brand_name}")
async def get_brand_analytics(brand_name: str):
    """Get analytics for a brand's prompt tracking"""
    with engine.connect() as conn:
        # Get summary statistics
        stats_query = text("""
            SELECT 
                COUNT(DISTINCT pr.id) as total_runs,
                COUNT(DISTINCT pr.id) FILTER (WHERE pr.status = 'completed') as successful_runs,
                COUNT(DISTINCT pr.id) FILTER (WHERE pr.status = 'failed') as failed_runs,
                AVG(CASE WHEN res.brand_mentioned THEN 1 ELSE 0 END) * 100 as mention_rate,
                AVG(res.mention_count) as avg_mentions,
                AVG(res.confidence_score) * 100 as avg_confidence
            FROM prompt_runs pr
            LEFT JOIN prompt_results res ON pr.id = res.run_id
            WHERE pr.brand_name = :brand
        """)
        
        stats = conn.execute(stats_query, {"brand": brand_name}).fetchone()
        
        # Get grounding mode comparison
        grounding_query = text("""
            SELECT 
                pr.grounding_mode,
                COUNT(*) as run_count,
                AVG(CASE WHEN res.brand_mentioned THEN 1 ELSE 0 END) * 100 as mention_rate
            FROM prompt_runs pr
            LEFT JOIN prompt_results res ON pr.id = res.run_id
            WHERE pr.brand_name = :brand AND pr.status = 'completed'
            GROUP BY pr.grounding_mode
        """)
        
        grounding_results = conn.execute(grounding_query, {"brand": brand_name})
        grounding_comparison = {}
        for row in grounding_results:
            grounding_comparison[row.grounding_mode] = {
                "run_count": row.run_count,
                "mention_rate": float(row.mention_rate) if row.mention_rate else 0
            }
        
        # Get country comparison
        country_query = text("""
            SELECT 
                pr.country_code,
                COUNT(*) as run_count,
                AVG(CASE WHEN res.brand_mentioned THEN 1 ELSE 0 END) * 100 as mention_rate
            FROM prompt_runs pr
            LEFT JOIN prompt_results res ON pr.id = res.run_id
            WHERE pr.brand_name = :brand AND pr.status = 'completed'
            GROUP BY pr.country_code
        """)
        
        country_results = conn.execute(country_query, {"brand": brand_name})
        country_comparison = {}
        for row in country_results:
            country_comparison[row.country_code] = {
                "run_count": row.run_count,
                "mention_rate": float(row.mention_rate) if row.mention_rate else 0
            }
        
        return {
            "brand_name": brand_name,
            "statistics": {
                "total_runs": stats.total_runs,
                "successful_runs": stats.successful_runs,
                "failed_runs": stats.failed_runs,
                "mention_rate": float(stats.mention_rate) if stats.mention_rate else 0,
                "avg_mentions_per_response": float(stats.avg_mentions) if stats.avg_mentions else 0,
                "avg_confidence": float(stats.avg_confidence) if stats.avg_confidence else 0
            },
            "grounding_comparison": grounding_comparison,
            "country_comparison": country_comparison
        }