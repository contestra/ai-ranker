# Prompter Service Package
"""
Production-ready prompt template management with:
- Multi-brand workspace support
- Config hash-based deduplication
- Provider version tracking
- Full audit trail
"""

from .prompt_versions import ensure_version_service
from .canonicalize import canonicalize_config

__all__ = [
    'ensure_version_service',
    'canonicalize_config',
]