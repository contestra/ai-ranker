from fastapi import Header, HTTPException, Depends
from .db import db_session
import re
from uuid import UUID

LANG_RE = re.compile(r"^(?=.{2,32}$)[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

def require_tenant_id(x_tenant_id: str = Header(..., alias="X-Tenant-ID")) -> str:
    try:
        _ = UUID(x_tenant_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID (UUID required)")
    return x_tenant_id

def get_db(tenant_id: str = Depends(require_tenant_id)):
    with db_session(tenant_id) as s:
        yield s

def get_idempotency_key(idempotency_key: str | None = Header(None, alias="Idempotency-Key")) -> str | None:
    return idempotency_key

def validate_language(lang: str | None) -> str:
    if not lang:
        return "en-US"
    return lang if LANG_RE.match(lang) else "en-US"
