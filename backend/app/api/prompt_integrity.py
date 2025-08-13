"""
API endpoints for prompt integrity checking
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from app.database import engine
from app.services.prompt_hasher import (
    calculate_prompt_hash, 
    verify_prompt_integrity,
    detect_prompt_modification,
    find_duplicate_prompts
)

router = APIRouter(prefix="/api/prompt-integrity", tags=["prompt-integrity"])

@router.get("/verify/{template_id}")
async def verify_template_integrity(template_id: int):
    """
    Verify that a template's prompt hasn't been corrupted.
    Recalculates hash and compares with stored hash.
    """
    with engine.connect() as conn:
        query = text("""
            SELECT prompt_text, prompt_hash 
            FROM prompt_templates 
            WHERE id = :id
        """)
        result = conn.execute(query, {"id": template_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        
        prompt_text = result.prompt_text
        stored_hash = result.prompt_hash
        
        # Recalculate and verify
        is_valid, current_hash = verify_prompt_integrity(stored_hash, prompt_text)
        
        return {
            "template_id": template_id,
            "is_valid": is_valid,
            "stored_hash": stored_hash,
            "current_hash": current_hash,
            "status": "intact" if is_valid else "corrupted",
            "message": "Prompt integrity verified" if is_valid else "WARNING: Prompt has been modified!"
        }

@router.get("/check-execution/{run_id}")
async def check_execution_integrity(run_id: int):
    """
    Check if a prompt was modified between template creation and execution.
    """
    with engine.connect() as conn:
        # Get the execution result and its template
        query = text("""
            SELECT 
                pr.prompt_hash as execution_hash,
                pr.prompt_text as execution_prompt,
                pt.prompt_hash as template_hash,
                pt.prompt_text as template_prompt,
                pr.run_id,
                pt.id as template_id
            FROM prompt_results pr
            JOIN prompt_runs prun ON pr.run_id = prun.id
            JOIN prompt_templates pt ON prun.template_id = pt.id
            WHERE pr.run_id = :run_id
        """)
        result = conn.execute(query, {"run_id": run_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Check if prompt was modified
        detection = detect_prompt_modification(
            result.template_hash,
            result.execution_hash
        )
        
        return {
            "run_id": run_id,
            "template_id": result.template_id,
            **detection,
            "execution_prompt_preview": result.execution_prompt[:200] + "..." if len(result.execution_prompt) > 200 else result.execution_prompt
        }

@router.get("/find-duplicates")
async def find_duplicate_templates(brand_name: Optional[str] = None):
    """
    Find duplicate prompt templates based on hash.
    """
    with engine.connect() as conn:
        query_parts = ["SELECT id, brand_name, template_name, prompt_text FROM prompt_templates WHERE 1=1"]
        params = {}
        
        if brand_name:
            query_parts.append("AND brand_name = :brand")
            params["brand"] = brand_name
        
        query = text(" ".join(query_parts))
        result = conn.execute(query, params)
        
        templates = []
        for row in result:
            templates.append({
                "id": row.id,
                "brand_name": row.brand_name,
                "template_name": row.template_name,
                "prompt_text": row.prompt_text
            })
        
        # Find duplicates
        duplicates = find_duplicate_prompts(templates)
        
        # Format response
        duplicate_groups = []
        for hash_val, ids in duplicates.items():
            group_templates = [t for t in templates if t["id"] in ids]
            duplicate_groups.append({
                "hash": hash_val,
                "count": len(ids),
                "template_ids": ids,
                "templates": group_templates
            })
        
        return {
            "total_templates": len(templates),
            "duplicate_groups": len(duplicate_groups),
            "duplicates": duplicate_groups
        }

@router.post("/rehash-all")
async def rehash_all_templates():
    """
    Recalculate and update hashes for all templates (migration helper).
    """
    with engine.begin() as conn:
        # Get all templates
        query = text("SELECT id, prompt_text FROM prompt_templates")
        templates = conn.execute(query).fetchall()
        
        updated_count = 0
        for template in templates:
            # Calculate hash
            prompt_hash = calculate_prompt_hash(template.prompt_text)
            
            # Update template
            update_query = text("""
                UPDATE prompt_templates 
                SET prompt_hash = :hash 
                WHERE id = :id
            """)
            conn.execute(update_query, {
                "id": template.id,
                "hash": prompt_hash
            })
            updated_count += 1
        
        return {
            "message": f"Successfully rehashed {updated_count} templates",
            "count": updated_count
        }

@router.get("/stats")
async def get_integrity_stats():
    """
    Get overall integrity statistics.
    """
    with engine.connect() as conn:
        # Count templates with and without hashes
        template_stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(prompt_hash) as with_hash,
                COUNT(CASE WHEN prompt_hash IS NULL THEN 1 END) as without_hash
            FROM prompt_templates
        """)).fetchone()
        
        # Count results with integrity issues
        integrity_issues = conn.execute(text("""
            SELECT COUNT(DISTINCT pr.run_id) as modified_executions
            FROM prompt_results pr
            JOIN prompt_runs prun ON pr.run_id = prun.id
            JOIN prompt_templates pt ON prun.template_id = pt.id
            WHERE pr.prompt_hash != pt.prompt_hash
            AND pr.prompt_hash IS NOT NULL
            AND pt.prompt_hash IS NOT NULL
        """)).fetchone()
        
        return {
            "templates": {
                "total": template_stats.total,
                "with_hash": template_stats.with_hash,
                "without_hash": template_stats.without_hash,
                "hash_coverage": f"{(template_stats.with_hash / template_stats.total * 100):.1f}%" if template_stats.total > 0 else "0%"
            },
            "integrity_issues": {
                "modified_executions": integrity_issues.modified_executions if integrity_issues else 0,
                "description": "Number of runs where prompt was modified between template and execution"
            }
        }