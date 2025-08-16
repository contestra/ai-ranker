"""
Service layer for Prompter V7 - Provider version tracking
Prevents route recursion and provides shared functionality
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.prompt_v7 import PromptVersion, Workspace, Organization
from prompter.provider_probe import probe_langchain


def get_or_create_workspace(
    db: Session,
    org_id: str,
    brand_name: str
) -> Workspace:
    """Get or create workspace for a brand"""
    # Check if workspace exists for this brand
    workspace = db.query(Workspace).filter_by(
        org_id=org_id,
        brand_name=brand_name,
        deleted_at=None
    ).first()
    
    if workspace:
        return workspace
    
    # Create new workspace
    workspace = Workspace(
        id=str(uuid.uuid4()),
        org_id=org_id,
        brand_name=brand_name,
        name=f"{brand_name} Workspace"
    )
    db.add(workspace)
    db.flush()
    
    return workspace


def ensure_version_service(
    db: Session,
    *,
    org_id: str,
    workspace_id: str,
    provider: str,
    model_id: str,
    adapter=None
) -> Tuple[Optional[str], datetime]:
    """
    Ensure provider version is tracked (service layer).
    This is called by routes to track provider versions without recursion.
    
    Returns:
        (provider_version_key, captured_at)
    """
    # Check if probe is disabled
    if os.getenv("PROMPTER_PROBE_DISABLED", "false").lower() == "true":
        return None, datetime.now(timezone.utc)
    
    # Check existing version record
    version_record = db.query(PromptVersion).filter_by(
        org_id=org_id,
        workspace_id=workspace_id,
        provider=provider,
        model_id=model_id
    ).first()
    
    # Probe for current version (async operation made sync for service layer)
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        provider_version_key, captured_at = loop.run_until_complete(
            probe_langchain(provider, model_id, adapter)
        )
    finally:
        loop.close()
    
    if not provider_version_key:
        return None, captured_at
    
    # Update or create version record
    if version_record:
        # Update existing record
        version_record.provider_version_key = provider_version_key
        version_record.last_seen_at = captured_at
        version_record.probe_count += 1
    else:
        # Create new record
        version_record = PromptVersion(
            id=str(uuid.uuid4()),
            org_id=org_id,
            workspace_id=workspace_id,
            provider=provider,
            model_id=model_id,
            provider_version_key=provider_version_key,
            first_seen_at=captured_at,
            last_seen_at=captured_at,
            probe_count=1
        )
        db.add(version_record)
    
    db.flush()
    
    return provider_version_key, captured_at


# Redis idempotency (optional, for production)
def check_idempotency(
    redis_client,
    org_id: str,
    workspace_id: str,
    config_hash: str,
    hour_bucket: str
) -> bool:
    """
    Check Redis for duplicate within hour bucket.
    Returns True if duplicate found.
    """
    if not redis_client:
        return False
    
    key = f"prompter:idempotency:{org_id}:{workspace_id}:{hour_bucket}:{config_hash}"
    
    # Check if key exists
    if redis_client.exists(key):
        return True
    
    # Set key with 2-hour expiry
    redis_client.setex(key, 7200, "1")
    return False