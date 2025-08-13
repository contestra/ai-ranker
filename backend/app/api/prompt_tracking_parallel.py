"""
Parallel execution version of prompt tracking
"""

import asyncio
from typing import Dict, Any, Tuple
from app.llm.langchain_adapter import LangChainAdapter
from sqlalchemy import text
from app.database import engine
from app.services.als.country_codes import country_to_num, num_to_country

async def process_single_test(
    template_id: int,
    brand_name: str,
    model_name: str,
    country_orig: str,
    grounding_mode: str,
    prompt_text: str
) -> Dict[str, Any]:
    """Process a single test configuration in parallel"""
    
    # Convert country code to numeric ID to prevent AI detection
    country_num = country_to_num(country_orig)
    country_iso = country_orig  # Keep ISO for ALS and DB only
    
    # Create NEW adapter instance for this test to avoid state pollution
    adapter = LangChainAdapter()
    
    # Create run record
    with engine.begin() as conn:
        run_query = text("""
            INSERT INTO prompt_runs 
            (template_id, brand_name, model_name, country_code, grounding_mode, status, started_at)
            VALUES (:template_id, :brand, :model, :country, :grounding, 'running', datetime('now'))
            RETURNING id
        """)
        
        run_result = conn.execute(run_query, {
            "template_id": template_id,
            "brand": brand_name,
            "model": model_name,
            "country": country_iso,  # Store ISO in DB for display
            "grounding": grounding_mode
        })
        run_id = run_result.fetchone()[0]
    
    try:
        # Build Ambient Block for country-specific testing
        ambient_block = ""
        if country_num != 0:  # 0 is NONE
            # Use Ambient Blocks for clean, minimal civic signals
            if country_iso in ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']:
                try:
                    from app.services.als import als_service
                    ambient_block = als_service.build_als_block(country_iso)  # ALS needs ISO
                except Exception as e:
                    print(f"Failed to build Ambient Block for numeric {country_num} (ISO: {country_iso}): {e}")
                    ambient_block = ""
        
        # Prepare prompt
        if country_num == 0:  # NONE
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
                # Fallback if no ambient block
                if grounding_mode == "web":
                    full_prompt = f"""Please use web search to answer this question accurately:

{prompt_text}"""
                else:
                    full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
                context_message = None
        
        # Fixed parameters for reproducibility
        temperature = 0.0
        seed = 42
        
        # Get model response
        if model_name in ["gemini", "gemini-flash"]:
            response_data = await adapter.analyze_with_gemini(
                full_prompt,
                grounding_mode == "web",
                model_name="gemini-2.0-flash-exp" if model_name == "gemini-flash" else "gemini-2.5-pro",
                temperature=temperature,
                seed=seed,
                context=context_message
            )
        else:
            # GPT models
            response_data = await adapter.analyze_with_gpt4(
                full_prompt,
                model_name=model_name,
                temperature=temperature,
                seed=seed,
                context=context_message
            )
        
        # Extract response
        response = response_data.get("content", "") if isinstance(response_data, dict) else str(response_data)
        
        # Analyze response
        brand_mentioned = brand_name.lower() in response.lower()
        mention_count = response.lower().count(brand_name.lower())
        
        # Save result (simplified schema)
        with engine.begin() as conn:
            result_query = text("""
                INSERT INTO prompt_results 
                (run_id, prompt_text, model_response, brand_mentioned, mention_count, 
                 competitors_mentioned, confidence_score)
                VALUES (:run_id, :prompt, :response, :mentioned, :count, 
                        :competitors, :confidence)
                RETURNING id
            """)
            
            import json
            
            conn.execute(result_query, {
                "run_id": run_id,
                "prompt": full_prompt,
                "response": response,
                "mentioned": brand_mentioned,
                "count": mention_count,
                "competitors": json.dumps([]),
                "confidence": 0.8 if brand_mentioned else 0.3
            })
            
            # Update run status
            update_query = text("""
                UPDATE prompt_runs 
                SET status = 'completed', completed_at = datetime('now')
                WHERE id = :id
            """)
            conn.execute(update_query, {"id": run_id})
        
        return {
            "run_id": run_id,
            "country": country_iso,  # Return ISO for display
            "grounding_mode": grounding_mode,
            "brand_mentioned": brand_mentioned,
            "mention_count": mention_count,
            "response_preview": response[:200] + "..." if len(response) > 200 else response,
            "status": "completed"
        }
        
    except Exception as e:
        # Update run with error
        with engine.begin() as conn:
            error_query = text("""
                UPDATE prompt_runs 
                SET status = 'failed', error_message = :error, completed_at = datetime('now')
                WHERE id = :id
            """)
            conn.execute(error_query, {"id": run_id, "error": str(e)})
        
        return {
            "run_id": run_id,
            "country": country_iso,  # Return ISO for display
            "grounding_mode": grounding_mode,
            "error": str(e),
            "status": "failed"
        }

async def run_parallel_tests(
    template_id: int,
    brand_name: str,
    model_name: str,
    prompt_text: str,
    countries: list,
    grounding_modes: list
) -> list:
    """Run all test combinations in parallel"""
    
    # Create all test tasks
    tasks = []
    for country in countries:
        for grounding_mode in grounding_modes:
            task = process_single_test(
                template_id,
                brand_name,
                model_name,
                country,
                grounding_mode,
                prompt_text
            )
            tasks.append(task)
    
    # Run all tasks in parallel with a limit
    # Limit concurrent tasks to avoid overwhelming the API
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent API calls
    
    async def limited_task(task):
        async with semaphore:
            return await task
    
    limited_tasks = [limited_task(task) for task in tasks]
    results = await asyncio.gather(*limited_tasks, return_exceptions=True)
    
    # Process results
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            processed_results.append({
                "error": str(result),
                "status": "failed"
            })
        else:
            processed_results.append(result)
    
    return processed_results