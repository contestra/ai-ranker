"""
Celery tasks for prompt execution outside HTTP context.
This bypasses the web API layer where the DE leak occurs.
"""

from celery import Task
from app.celery_app import celery_app
from typing import Dict, Any
import asyncio
from sqlalchemy import text
import json

# Import required modules
from app.database import engine
from app.llm.langchain_adapter import LangChainAdapter
from app.services.als import als_service
from app.services.als.country_codes import country_to_num, num_to_country


class PromptExecutionTask(Task):
    """Base task class with database connection handling"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        run_id = kwargs.get('run_id')
        if run_id:
            with engine.begin() as conn:
                error_query = text("""
                    UPDATE prompt_runs 
                    SET status = 'failed', error_message = :error, completed_at = datetime('now')
                    WHERE id = :id
                """)
                conn.execute(error_query, {"id": run_id, "error": str(exc)})


@celery_app.task(bind=True, base=PromptExecutionTask, name='execute_prompt')
def execute_prompt(
    self,
    run_id: int,
    template_id: int,
    brand_name: str,
    model_name: str,
    country_iso: str,
    grounding_mode: str,
    prompt_text: str
) -> Dict[str, Any]:
    """
    Execute a single prompt test in Celery worker (outside HTTP context).
    This should fix the DE leak issue.
    """
    
    # Run async code in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _execute_prompt_async(
                run_id, template_id, brand_name, model_name,
                country_iso, grounding_mode, prompt_text
            )
        )
        return result
    finally:
        loop.close()


async def _execute_prompt_async(
    run_id: int,
    template_id: int,
    brand_name: str,
    model_name: str,
    country_iso: str,
    grounding_mode: str,
    prompt_text: str
) -> Dict[str, Any]:
    """Async implementation of prompt execution"""
    
    try:
        # Convert country code to numeric ID to prevent AI detection
        country_num = country_to_num(country_iso)
        
        # Create NEW adapter instance for complete isolation
        adapter = LangChainAdapter()
        
        # Build Ambient Block for country-specific testing
        ambient_block = ""
        if country_num != 0:  # 0 is NONE
            if country_iso in ['DE', 'CH', 'US', 'GB', 'AE', 'SG', 'IT', 'FR']:
                try:
                    ambient_block = als_service.build_als_block(country_iso)
                except Exception as e:
                    print(f"Failed to build Ambient Block for {country_iso}: {e}")
                    ambient_block = ""
        
        # Prepare prompt based on mode
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
                full_prompt = prompt_text  # NAKED prompt
                context_message = ambient_block  # Separate context
            else:
                # Fallback if no ambient block
                if grounding_mode == "web":
                    full_prompt = f"""Please use web search to answer this question accurately:

{prompt_text}"""
                else:
                    full_prompt = f"""Based only on your training data (do not search the web):

{prompt_text}"""
                context_message = None
        
        # Log execution context
        print(f"\n{'='*60}")
        print(f"CELERY TASK - EXECUTING PROMPT")
        print(f"Run ID: {run_id}")
        print(f"Model: {model_name}")
        print(f"Country: {country_iso} (numeric: {country_num})")
        print(f"Grounding: {grounding_mode}")
        print(f"Has Ambient Block: {bool(context_message)}")
        print(f"{'='*60}\n")
        
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
        
        # Check for error or empty response
        if not response or len(response.strip()) == 0:
            print(f"[ERROR] Empty response received for run {run_id}")
            print(f"  Model: {model_name}")
            print(f"  Country: {country_iso}")
            print(f"  Grounding: {grounding_mode}")
            response = "[ERROR] Model returned empty response. Please try again."
        elif response.startswith("[ERROR]"):
            print(f"[ERROR] Error response for run {run_id}: {response[:100]}")
        
        # Log successful response length
        if response and not response.startswith("[ERROR]"):
            print(f"[SUCCESS] Response received for run {run_id}: {len(response)} characters")
        
        # Analyze response
        brand_mentioned = brand_name.lower() in response.lower() if response else False
        mention_count = response.lower().count(brand_name.lower()) if response else 0
        
        # Check for leaks
        leak_detected = False
        leak_terms = []
        if 'DE' in response:
            leak_detected = True
            leak_terms.append('DE')
        if 'Germany' in response:
            leak_detected = True
            leak_terms.append('Germany')
        if 'Deutschland' in response:
            leak_detected = True
            leak_terms.append('Deutschland')
        if 'location context' in response.lower():
            leak_detected = True
            leak_terms.append('location context')
        
        if leak_detected:
            print(f"[CELERY WARNING] Leak detected in worker: {', '.join(leak_terms)}")
            print(f"Response preview: {response[:200]}...")
        
        # Save result to database (simplified schema)
        with engine.begin() as conn:
            result_query = text("""
                INSERT INTO prompt_results 
                (run_id, prompt_text, model_response, brand_mentioned, mention_count, 
                 competitors_mentioned, confidence_score)
                VALUES (:run_id, :prompt, :response, :mentioned, :count, 
                        :competitors, :confidence)
                RETURNING id
            """)
            
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
            "country": country_iso,
            "grounding_mode": grounding_mode,
            "brand_mentioned": brand_mentioned,
            "mention_count": mention_count,
            "response_preview": response[:200] + "..." if len(response) > 200 else response,
            "status": "completed",
            "leak_detected": leak_detected,
            "leak_terms": leak_terms if leak_detected else []
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
        
        raise  # Re-raise for Celery retry mechanism


@celery_app.task(name='execute_prompt_batch')
def execute_prompt_batch(test_configs: list) -> list:
    """
    Execute multiple prompt tests in parallel using Celery.
    Each test runs in its own isolated worker process.
    """
    
    from celery import group
    
    # Create a group of tasks
    job = group(
        execute_prompt.s(
            run_id=config['run_id'],
            template_id=config['template_id'],
            brand_name=config['brand_name'],
            model_name=config['model_name'],
            country_iso=config['country'],
            grounding_mode=config['grounding_mode'],
            prompt_text=config['prompt_text']
        )
        for config in test_configs
    )
    
    # Execute all tasks in parallel
    result = job.apply_async()
    
    # Wait for all tasks to complete
    results = result.get(timeout=120)
    
    return results