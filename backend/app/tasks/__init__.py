"""
Celery tasks module for background processing.
"""

from .prompt_tasks import execute_prompt, execute_prompt_batch

__all__ = ['execute_prompt', 'execute_prompt_batch']