"""
Celery configuration for background task processing.
Uses Upstash Redis as broker to bypass HTTP context and fix DE leak.
"""

from celery import Celery
from app.config import settings
import os

# For Windows development, use local Redis
# Note: Upstash REST API doesn't work as Celery broker
# For production on Fly.io, you'll need a proper Redis instance
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Alternative: If you have a direct Redis connection to Upstash
# You would need the direct Redis endpoint, not the REST API endpoint
# Example: rediss://default:password@host.upstash.io:6379

# Create Celery app
celery_app = Celery(
    'ai_ranker',
    broker=redis_url,
    backend=redis_url,
    include=['app.tasks.prompt_tasks']  # Include our task modules
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=120,  # 2 minutes max per task
    task_soft_time_limit=90,  # Soft limit at 90 seconds
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    
    # Queue settings
    task_default_queue='prompt_queue',
    task_routes={
        'app.tasks.prompt_tasks.*': {'queue': 'prompt_queue'},
    },
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_retry_backoff=True,
    task_retry_backoff_max=60,
    task_retry_jitter=True,
)

# For debugging
celery_app.conf.update(
    worker_hijack_root_logger=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
)