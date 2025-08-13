"""
Celery-based prompt tracking API that runs outside HTTP context.
This should fix the DE leak issue by executing prompts in worker processes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import text
import json

from app.database import engine
from app.tasks.prompt_tasks import execute_prompt, execute_prompt_batch
from app.celery_app import celery_app

router = APIRouter(prefix="/api/prompt-tracking-celery", tags=["prompt-tracking-celery"])


class PromptRunCeleryRequest(BaseModel):
    template_id: int
    brand_name: str
    model_name: str = "gemini"
    countries: Optional[List[str]] = None
    grounding_modes: Optional[List[str]] = None
    async_mode: bool = True  # Return task IDs immediately or wait for results


@router.post("/run")
async def run_prompt_celery(request: PromptRunCeleryRequest):
    """
    Execute prompt template using Celery workers (outside HTTP context).
    This bypasses the web API layer where the DE leak occurs.
    """
    
    # Get the template
    with engine.connect() as conn:
        template_query = text("SELECT * FROM prompt_templates WHERE id = :id")
        template = conn.execute(template_query, {"id": request.template_id}).fetchone()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
    
    # Parse JSON fields if needed
    template_countries = template.countries
    if isinstance(template_countries, str):
        template_countries = json.loads(template_countries)
    
    template_modes = template.grounding_modes
    if isinstance(template_modes, str):
        template_modes = json.loads(template_modes)
    
    # Prepare the prompt with brand name
    prompt_text = template.prompt_text.replace("{brand_name}", request.brand_name)
    
    # Determine countries and grounding modes to test
    countries = request.countries or template_countries or ["US"]
    grounding_modes = request.grounding_modes or template_modes or ["none"]
    
    # Create run records and prepare task configs
    task_configs = []
    task_ids = []
    
    for country in countries:
        for grounding_mode in grounding_modes:
            # Create run record
            with engine.begin() as conn:
                run_query = text("""
                    INSERT INTO prompt_runs 
                    (template_id, brand_name, model_name, country_code, grounding_mode, status, started_at)
                    VALUES (:template_id, :brand, :model, :country, :grounding, 'queued', datetime('now'))
                    RETURNING id
                """)
                
                run_result = conn.execute(run_query, {
                    "template_id": request.template_id,
                    "brand": request.brand_name,
                    "model": request.model_name,
                    "country": country,
                    "grounding": grounding_mode
                })
                run_id = run_result.fetchone()[0]
            
            # Prepare task config
            task_config = {
                'run_id': run_id,
                'template_id': request.template_id,
                'brand_name': request.brand_name,
                'model_name': request.model_name,
                'country': country,
                'grounding_mode': grounding_mode,
                'prompt_text': prompt_text
            }
            task_configs.append(task_config)
            
            # Submit task to Celery
            task = execute_prompt.apply_async(
                kwargs=task_config,
                queue='prompt_queue'
            )
            task_ids.append({
                'task_id': task.id,
                'run_id': run_id,
                'country': country,
                'grounding_mode': grounding_mode
            })
    
    if request.async_mode:
        # Return immediately with task IDs
        return {
            "message": "Tasks submitted to Celery workers",
            "template_name": template.template_name,
            "brand_name": request.brand_name,
            "tasks": task_ids,
            "check_status_url": "/api/prompt-tracking-celery/status"
        }
    else:
        # Wait for all tasks to complete
        results = []
        for task_info in task_ids:
            task = celery_app.AsyncResult(task_info['task_id'])
            try:
                # Wait up to 60 seconds for each task
                result = task.get(timeout=60)
                results.append(result)
            except Exception as e:
                results.append({
                    "run_id": task_info['run_id'],
                    "country": task_info['country'],
                    "grounding_mode": task_info['grounding_mode'],
                    "error": str(e),
                    "status": "failed"
                })
        
        # Check if any results have leaks
        leak_summary = {
            "total_tests": len(results),
            "tests_with_leaks": sum(1 for r in results if r.get('leak_detected', False)),
            "leak_details": [
                {
                    "country": r['country'],
                    "grounding_mode": r['grounding_mode'],
                    "leak_terms": r.get('leak_terms', [])
                }
                for r in results if r.get('leak_detected', False)
            ]
        }
        
        return {
            "template_name": template.template_name,
            "brand_name": request.brand_name,
            "results": results,
            "leak_summary": leak_summary
        }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a Celery task"""
    
    task = celery_app.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {
            "task_id": task_id,
            "state": task.state,
            "status": "Task is waiting to be executed"
        }
    elif task.state == 'STARTED':
        return {
            "task_id": task_id,
            "state": task.state,
            "status": "Task is currently running"
        }
    elif task.state == 'SUCCESS':
        return {
            "task_id": task_id,
            "state": task.state,
            "status": "Task completed successfully",
            "result": task.result
        }
    elif task.state == 'FAILURE':
        return {
            "task_id": task_id,
            "state": task.state,
            "status": "Task failed",
            "error": str(task.info)
        }
    else:
        return {
            "task_id": task_id,
            "state": task.state,
            "status": f"Unknown state: {task.state}"
        }


@router.post("/batch-status")
async def get_batch_status(task_ids: List[str]):
    """Check the status of multiple Celery tasks"""
    
    results = []
    for task_id in task_ids:
        task = celery_app.AsyncResult(task_id)
        
        task_info = {
            "task_id": task_id,
            "state": task.state
        }
        
        if task.state == 'SUCCESS':
            task_info["result"] = task.result
        elif task.state == 'FAILURE':
            task_info["error"] = str(task.info)
        
        results.append(task_info)
    
    # Summary statistics
    summary = {
        "total": len(task_ids),
        "pending": sum(1 for r in results if r['state'] == 'PENDING'),
        "started": sum(1 for r in results if r['state'] == 'STARTED'),
        "success": sum(1 for r in results if r['state'] == 'SUCCESS'),
        "failed": sum(1 for r in results if r['state'] == 'FAILURE')
    }
    
    return {
        "tasks": results,
        "summary": summary
    }


@router.get("/test-celery")
async def test_celery_connection():
    """Test if Celery is properly configured and can connect to Redis"""
    
    try:
        # Test Redis connection through Celery
        i = celery_app.control.inspect()
        stats = i.stats()
        active = i.active()
        
        return {
            "status": "connected",
            "workers": list(stats.keys()) if stats else [],
            "active_tasks": active,
            "broker_url": celery_app.conf.broker_url[:50] + "..." if celery_app.conf.broker_url else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "broker_url": celery_app.conf.broker_url[:50] + "..." if celery_app.conf.broker_url else None
        }