"""
Background-based prompt tracking API that runs outside HTTP context.
This should fix the DE leak issue by executing prompts in separate threads.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import text
import json

from app.database import engine
from app.services.background_runner import background_runner

router = APIRouter(prefix="/api/prompt-tracking-background", tags=["prompt-tracking-background"])


class PromptRunBackgroundRequest(BaseModel):
    template_id: int
    brand_name: str
    model_name: str = "gemini"
    countries: Optional[List[str]] = None
    grounding_modes: Optional[List[str]] = None
    wait_for_completion: bool = False  # If True, wait for tasks to complete


@router.post("/run")
async def run_prompt_background(request: PromptRunBackgroundRequest):
    """
    Execute prompt template using background threads (outside HTTP context).
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
    
    # Submit tasks to background runner
    task_infos = []
    
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
            
            # Submit to background runner
            task_id = background_runner.submit_task(
                run_id=run_id,
                template_id=request.template_id,
                brand_name=request.brand_name,
                model_name=request.model_name,
                country_iso=country,
                grounding_mode=grounding_mode,
                prompt_text=prompt_text
            )
            
            task_infos.append({
                'task_id': task_id,
                'run_id': run_id,
                'country': country,
                'grounding_mode': grounding_mode
            })
    
    if request.wait_for_completion:
        # Wait for all tasks to complete (with timeout)
        import time
        max_wait = 60  # seconds
        start_time = time.time()
        
        results = []
        all_completed = False
        
        while time.time() - start_time < max_wait:
            all_completed = True
            temp_results = []
            
            for task_info in task_infos:
                status = background_runner.get_task_status(task_info['task_id'])
                
                if status['status'] in ['completed', 'failed']:
                    if status['status'] == 'completed':
                        temp_results.append(status['result'])
                    else:
                        temp_results.append({
                            "run_id": task_info['run_id'],
                            "country": task_info['country'],
                            "grounding_mode": task_info['grounding_mode'],
                            "error": status.get('error', 'Unknown error'),
                            "status": "failed"
                        })
                else:
                    all_completed = False
            
            if all_completed:
                results = temp_results
                break
            
            time.sleep(1)  # Check every second
        
        if not all_completed:
            return {
                "message": "Timeout waiting for tasks to complete",
                "partial_results": temp_results,
                "task_infos": task_infos
            }
        
        # Check for leaks
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
        
        print(f"\n{'='*60}")
        print(f"BACKGROUND EXECUTION COMPLETE")
        print(f"Total tests: {leak_summary['total_tests']}")
        print(f"Tests with leaks: {leak_summary['tests_with_leaks']}")
        if leak_summary['tests_with_leaks'] > 0:
            print(f"[WARNING] Leaks still detected in background execution!")
        else:
            print(f"[SUCCESS] No leaks detected in background execution!")
        print(f"{'='*60}\n")
        
        return {
            "template_name": template.template_name,
            "brand_name": request.brand_name,
            "results": results,
            "leak_summary": leak_summary
        }
    else:
        # Return immediately with task IDs
        return {
            "message": "Tasks submitted to background runners",
            "template_name": template.template_name,
            "brand_name": request.brand_name,
            "tasks": task_infos,
            "check_status_url": "/api/prompt-tracking-background/status"
        }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a background task"""
    
    status = background_runner.get_task_status(task_id)
    
    if status['status'] == 'not_found':
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@router.post("/batch-status")
async def get_batch_status(task_ids: List[str]):
    """Check the status of multiple background tasks"""
    
    results = []
    for task_id in task_ids:
        status = background_runner.get_task_status(task_id)
        results.append({
            "task_id": task_id,
            **status
        })
    
    # Summary statistics
    summary = {
        "total": len(task_ids),
        "pending": sum(1 for r in results if r.get('status') == 'pending'),
        "running": sum(1 for r in results if r.get('status') == 'running'),
        "completed": sum(1 for r in results if r.get('status') == 'completed'),
        "failed": sum(1 for r in results if r.get('status') == 'failed'),
        "not_found": sum(1 for r in results if r.get('status') == 'not_found')
    }
    
    # Leak detection summary
    completed_results = [r for r in results if r.get('status') == 'completed' and r.get('result')]
    leak_summary = {
        "tests_completed": len(completed_results),
        "tests_with_leaks": sum(1 for r in completed_results if r.get('result', {}).get('leak_detected', False))
    }
    
    return {
        "tasks": results,
        "summary": summary,
        "leak_summary": leak_summary
    }


@router.get("/all-tasks")
async def get_all_tasks():
    """Get status of all background tasks"""
    
    tasks = background_runner.get_all_tasks()
    
    # Calculate summary
    summary = {
        "total": len(tasks),
        "pending": sum(1 for t in tasks.values() if t['status'] == 'pending'),
        "running": sum(1 for t in tasks.values() if t['status'] == 'running'),
        "completed": sum(1 for t in tasks.values() if t['status'] == 'completed'),
        "failed": sum(1 for t in tasks.values() if t['status'] == 'failed')
    }
    
    return {
        "tasks": tasks,
        "summary": summary
    }