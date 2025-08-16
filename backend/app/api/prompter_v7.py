"""
Prompter V7 API Router - Integrates with existing prompt_tracking system
Provides deduplication and provider version tracking
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.llm.langchain_adapter import LangChainAdapter
from app.services.prompt_versions import ensure_version_service, get_or_create_workspace
from prompter.utils_prompting import calc_config_hash, infer_provider
from prompter.provider_probe import probe_langchain

router = APIRouter(prefix="/api/v7/prompter", tags=["prompter-v7"])

# Request/Response models
class CreateTemplateRequest(BaseModel):
    """Request to create a prompt template"""
    name: str
    config: Dict[str, Any]
    org_id: str = Field(default="default")
    workspace_id: Optional[str] = None
    brand_name: Optional[str] = None  # For backward compatibility

class RunTemplateRequest(BaseModel):
    """Request to run a prompt template"""
    template_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    model_id: Optional[str] = None
    provider: Optional[str] = None
    
class TemplateResponse(BaseModel):
    """Response for template operations"""
    id: str
    name: str
    config_hash: str
    is_duplicate: bool = False
    existing_id: Optional[str] = None
    created_at: datetime
    
class RunResponse(BaseModel):
    """Response for template runs"""
    run_id: str
    result: str
    system_fingerprint: Optional[str] = None
    provider_version_key: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new prompt template with deduplication.
    Returns existing template if duplicate found.
    """
    from app.models.prompt_v7 import PromptTemplateV7, Organization, Workspace
    
    # Calculate config hash for deduplication
    config_hash = calc_config_hash(request.config)
    
    # Get or create organization
    org = db.query(Organization).filter_by(id=request.org_id).first()
    if not org:
        org = Organization(
            id=request.org_id,
            name=request.org_id
        )
        db.add(org)
        db.flush()
    
    # Get or create workspace
    workspace_id = request.workspace_id
    if not workspace_id and request.brand_name:
        # Create workspace from brand_name for backward compatibility
        workspace = get_or_create_workspace(
            db=db,
            org_id=request.org_id,
            brand_name=request.brand_name
        )
        workspace_id = workspace.id
    elif not workspace_id:
        workspace_id = f"{request.org_id}-default"
        workspace = db.query(Workspace).filter_by(id=workspace_id).first()
        if not workspace:
            workspace = Workspace(
                id=workspace_id,
                org_id=request.org_id,
                brand_name="default",
                name="Default Workspace"
            )
            db.add(workspace)
            db.flush()
    
    # Check for duplicate (active templates only)
    existing = db.query(PromptTemplateV7).filter_by(
        org_id=request.org_id,
        workspace_id=workspace_id,
        config_hash=config_hash,
        deleted_at=None
    ).first()
    
    if existing:
        return TemplateResponse(
            id=existing.id,
            name=existing.name,
            config_hash=existing.config_hash,
            is_duplicate=True,
            existing_id=existing.id,
            created_at=existing.created_at
        )
    
    # Create new template
    template = PromptTemplateV7(
        id=str(uuid.uuid4()),
        org_id=request.org_id,
        workspace_id=workspace_id,
        name=request.name,
        config=request.config,
        config_hash=config_hash
    )
    
    db.add(template)
    db.commit()
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        config_hash=template.config_hash,
        is_duplicate=False,
        created_at=template.created_at
    )


@router.post("/templates/{template_id}/run", response_model=RunResponse)
async def run_template(
    template_id: str,
    request: RunTemplateRequest,
    db: Session = Depends(get_db)
):
    """
    Run a prompt template with provider version tracking.
    """
    from app.models.prompt_v7 import PromptTemplateV7, PromptRunV7, PromptResultV7
    import time
    
    # Get template
    template = db.query(PromptTemplateV7).filter_by(
        id=template_id,
        deleted_at=None
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Determine provider and model
    provider = request.provider
    model_id = request.model_id
    
    if not provider and model_id:
        provider = infer_provider(model_id)
    
    if not provider:
        provider = "google"  # Default to Gemini
    
    if not model_id:
        if provider == "openai":
            model_id = "gpt-4o"  # GPT-5 returns empty responses
        elif provider == "google":
            model_id = "gemini-2.5-pro"
        elif provider == "anthropic":
            model_id = "claude-3-5-sonnet-20241022"
        else:
            model_id = "unknown"
    
    # Ensure provider version is tracked
    ensure_version_service(
        db=db,
        org_id=template.org_id,
        workspace_id=template.workspace_id,
        provider=provider,
        model_id=model_id
    )
    
    # Build prompt from template and variables
    prompt_text = template.config.get("prompt", "")
    for key, value in request.variables.items():
        prompt_text = prompt_text.replace(f"{{{key}}}", str(value))
    
    # Create run record
    run = PromptRunV7(
        id=str(uuid.uuid4()),
        template_id=template_id,
        brand_name=template.workspace.brand_name,
        model_name=model_id,
        status="running",
        provider=provider,
        config_hash=template.config_hash
    )
    db.add(run)
    db.flush()
    
    try:
        start_time = time.time()
        
        # Execute with LangChain adapter
        adapter = LangChainAdapter()
        
        # Get provider version via probe
        provider_version_key, _ = await probe_langchain(provider, model_id, adapter)
        run.provider_version_key = provider_version_key
        
        # Run the actual prompt
        if provider == "openai":
            result = await adapter.analyze_with_gpt4(
                prompt=prompt_text,
                model_name=model_id,
                temperature=template.config.get("temperature", 0.1)
            )
        elif provider == "google":
            result = await adapter.analyze_with_gemini(
                prompt=prompt_text,
                model_name=model_id,
                temperature=template.config.get("temperature", 0.1)
            )
        else:
            result = await adapter.generate(
                vendor=provider,
                prompt=prompt_text,
                temperature=template.config.get("temperature", 0.1)
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Extract response data
        if isinstance(result, dict):
            response_text = result.get("content", result.get("text", ""))
            system_fingerprint = result.get("system_fingerprint")
            token_count = result.get("token_count", {})
            metadata = result.get("metadata", {})
        else:
            response_text = str(result)
            system_fingerprint = None
            token_count = {}
            metadata = {}
        
        # Update run status
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.tokens_used = token_count.get("total_tokens")
        
        # Create result record
        result_record = PromptResultV7(
            id=str(uuid.uuid4()),
            run_id=run.id,
            prompt_text=prompt_text,
            prompt_hash=calc_config_hash({"prompt": prompt_text}),
            model_response=response_text,
            system_fingerprint=system_fingerprint,
            provider_version_key=provider_version_key,
            model_version=model_id,
            temperature=template.config.get("temperature", 0.1),
            response_time_ms=response_time_ms,
            token_count=token_count
        )
        db.add(result_record)
        db.commit()
        
        return RunResponse(
            run_id=run.id,
            result=response_text,
            system_fingerprint=system_fingerprint,
            provider_version_key=provider_version_key,
            tokens_used=run.tokens_used,
            response_time_ms=response_time_ms,
            metadata=metadata
        )
        
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Get a prompt template by ID"""
    from app.models.prompt_v7 import PromptTemplateV7
    
    template = db.query(PromptTemplateV7).filter_by(
        id=template_id,
        deleted_at=None
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "config": template.config,
        "config_hash": template.config_hash,
        "org_id": template.org_id,
        "workspace_id": template.workspace_id,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }


@router.get("/versions")
async def get_provider_versions(
    org_id: str = "default",
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get provider version tracking data"""
    from app.models.prompt_v7 import PromptVersion
    
    query = db.query(PromptVersion).filter_by(org_id=org_id)
    
    if workspace_id:
        query = query.filter_by(workspace_id=workspace_id)
    
    versions = query.all()
    
    return [
        {
            "provider": v.provider,
            "model_id": v.model_id,
            "provider_version_key": v.provider_version_key,
            "first_seen_at": v.first_seen_at,
            "last_seen_at": v.last_seen_at,
            "probe_count": v.probe_count,
            "metadata": v.version_metadata
        }
        for v in versions
    ]