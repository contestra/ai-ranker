"""
Health check endpoints for system monitoring
"""

from fastapi import APIRouter
from typing import Dict, Any
import time
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text

from app.database import engine
from app.config import settings
from app.cache.upstash_cache import cache
from app.services.background_runner import background_runner
from app.llm.langchain_adapter import LangChainAdapter

router = APIRouter(prefix="/api", tags=["health"])

# Cache for model health checks (to avoid spamming APIs)
model_health_cache = {
    'openai': {'last_check': None, 'status': 'unknown', 'response_time': None},
    'gemini': {'last_check': None, 'status': 'unknown', 'response_time': None}
}

# Cache for LangChain health check
langchain_health_cache = {
    'last_check': None,
    'status': 'unknown',
    'tracing_enabled': False,
    'project': None
}

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for all system components"""
    
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'response_time_ms': 0,
        'database': {'status': 'checking'},
        'cache': {'status': 'checking'},
        'models': {
            'openai': {'status': 'checking'},
            'gemini': {'status': 'checking'}
        },
        'background_runner': {'status': 'checking'},
        'langchain': {'status': 'checking'}
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM prompt_templates"))
            count = result.scalar()
            health_status['database'] = {
                'status': 'healthy',
                'message': f'{count} templates',
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
    except Exception as e:
        health_status['database'] = {
            'status': 'offline',
            'message': str(e)[:50]
        }
        health_status['status'] = 'degraded'
    
    # Check cache (Upstash Redis)
    try:
        cache_start = time.time()
        await cache.set('health_check', {'timestamp': datetime.utcnow().isoformat()}, ttl=60)
        cached = await cache.get('health_check')
        if cached:
            health_status['cache'] = {
                'status': 'healthy',
                'message': 'Connected',
                'response_time_ms': int((time.time() - cache_start) * 1000)
            }
        else:
            health_status['cache'] = {
                'status': 'degraded',
                'message': 'Write failed'
            }
    except Exception as e:
        health_status['cache'] = {
            'status': 'offline',
            'message': 'Not connected'
        }
        # Cache being offline is not critical
    
    # Check AI models (cached to avoid frequent API calls)
    now = datetime.utcnow()
    cache_duration = timedelta(minutes=5)
    
    # Check OpenAI (GPT-5)
    if (model_health_cache['openai']['last_check'] is None or 
        now - model_health_cache['openai']['last_check'] > cache_duration):
        try:
            adapter = LangChainAdapter()
            test_start = time.time()
            
            # Use asyncio timeout to prevent hanging
            response = await asyncio.wait_for(
                adapter.analyze_with_gpt4("Test", model_name="gpt-5"),
                timeout=5.0
            )
            
            response_time = int((time.time() - test_start) * 1000)
            model_health_cache['openai'] = {
                'last_check': now,
                'status': 'healthy' if response.get('content') else 'degraded',
                'response_time': response_time
            }
        except asyncio.TimeoutError:
            model_health_cache['openai'] = {
                'last_check': now,
                'status': 'degraded',
                'response_time': 5000,
                'message': 'Slow response'
            }
        except Exception:
            model_health_cache['openai'] = {
                'last_check': now,
                'status': 'offline',
                'response_time': None,
                'message': 'API error'
            }
    
    health_status['models']['openai'] = {
        'status': model_health_cache['openai']['status'],
        'avg_response_time_ms': model_health_cache['openai']['response_time'],
        'message': model_health_cache['openai'].get('message', 
                  f"~{model_health_cache['openai']['response_time']/1000:.1f}s avg" 
                  if model_health_cache['openai']['response_time'] else None)
    }
    
    # Check Gemini
    if (model_health_cache['gemini']['last_check'] is None or 
        now - model_health_cache['gemini']['last_check'] > cache_duration):
        try:
            adapter = LangChainAdapter()
            test_start = time.time()
            
            response = await asyncio.wait_for(
                adapter.analyze_with_gemini("Test", use_grounding=False),
                timeout=5.0
            )
            
            response_time = int((time.time() - test_start) * 1000)
            model_health_cache['gemini'] = {
                'last_check': now,
                'status': 'healthy' if response.get('content') else 'degraded',
                'response_time': response_time
            }
        except asyncio.TimeoutError:
            model_health_cache['gemini'] = {
                'last_check': now,
                'status': 'degraded',
                'response_time': 5000,
                'message': 'Slow response'
            }
        except Exception:
            model_health_cache['gemini'] = {
                'last_check': now,
                'status': 'offline',
                'response_time': None,
                'message': 'API error'
            }
    
    health_status['models']['gemini'] = {
        'status': model_health_cache['gemini']['status'],
        'avg_response_time_ms': model_health_cache['gemini']['response_time'],
        'message': model_health_cache['gemini'].get('message',
                  f"~{model_health_cache['gemini']['response_time']/1000:.1f}s avg" 
                  if model_health_cache['gemini']['response_time'] else None)
    }
    
    # Check background runner
    try:
        all_tasks = background_runner.get_all_tasks()
        active_count = sum(1 for t in all_tasks.values() if t['status'] == 'running')
        completed_count = sum(1 for t in all_tasks.values() if t['status'] == 'completed')
        
        health_status['background_runner'] = {
            'status': 'healthy',
            'active_tasks': active_count,
            'completed_tasks': completed_count,
            'total_tasks': len(all_tasks)
        }
    except Exception as e:
        health_status['background_runner'] = {
            'status': 'offline',
            'message': 'Not available'
        }
    
    # Check LangChain/LangSmith tracing
    global langchain_health_cache
    now = datetime.utcnow()
    cache_duration = timedelta(minutes=5)
    
    if (langchain_health_cache['last_check'] is None or 
        now - langchain_health_cache['last_check'] > cache_duration):
        try:
            # Check if LangChain API key is configured
            if settings.langchain_api_key:
                # Try to initialize LangSmith client
                from langsmith import Client
                client = Client(api_key=settings.langchain_api_key)
                
                # Check if we can connect to LangSmith
                try:
                    # List projects to verify connection
                    projects = list(client.list_projects(limit=1))
                    langchain_health_cache = {
                        'last_check': now,
                        'status': 'healthy',
                        'tracing_enabled': True,
                        'project': settings.langchain_project,
                        'message': f'Connected to project: {settings.langchain_project}'
                    }
                except Exception as e:
                    # API key is configured but can't connect
                    langchain_health_cache = {
                        'last_check': now,
                        'status': 'degraded',
                        'tracing_enabled': False,
                        'project': settings.langchain_project,
                        'message': 'API key configured but cannot connect'
                    }
            else:
                # No API key configured
                langchain_health_cache = {
                    'last_check': now,
                    'status': 'disabled',
                    'tracing_enabled': False,
                    'project': None,
                    'message': 'No API key configured (tracing disabled)'
                }
        except Exception as e:
            langchain_health_cache = {
                'last_check': now,
                'status': 'error',
                'tracing_enabled': False,
                'project': None,
                'message': f'Error checking LangChain: {str(e)}'
            }
    
    health_status['langchain'] = {
        'status': langchain_health_cache['status'],
        'tracing_enabled': langchain_health_cache['tracing_enabled'],
        'project': langchain_health_cache.get('project'),
        'message': langchain_health_cache.get('message')
    }
    
    # Determine overall status
    if health_status['database']['status'] == 'offline':
        health_status['status'] = 'offline'
    elif any(health_status['models'][m]['status'] == 'offline' for m in ['openai', 'gemini']):
        health_status['status'] = 'degraded'
    
    health_status['response_time_ms'] = int((time.time() - start_time) * 1000)
    
    return health_status

@router.get("/health/simple")
async def simple_health_check():
    """Simple health check for load balancers"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}