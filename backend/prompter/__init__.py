# Prompter V7 Package
"""
Prompt deduplication and provider version tracking system.

Features:
- Config hash-based deduplication within brand workspaces
- Provider version tracking (OpenAI fingerprints, Gemini versions, etc.)
- PostgreSQL-only architecture (Neon)
- Redis idempotency guards (optional)
- Service layer pattern to prevent route recursion
"""

__version__ = "7.0.0"