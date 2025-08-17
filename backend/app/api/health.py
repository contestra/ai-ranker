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
    'vertex': {'last_check': None, 'status': 'unknown', 'response_time': None},
    'gemini_direct': {'last_check': None, 'status': 'unknown', 'response_time': None}
}

# Cache for LangChain health check
langchain_health_cache = {
    'last_check': None,
    'status': 'unknown',
    'tracing_enabled': False,
    'project': None
}

@router.post("/health/refresh")
async def refresh_health_cache() -> Dict[str, str]:
    """Force refresh all health caches"""
    global model_health_cache, langchain_health_cache
    
    # Clear all caches
    model_health_cache = {
        'openai': {'last_check': None, 'status': 'checking', 'response_time': None},
        'vertex': {'last_check': None, 'status': 'checking', 'response_time': None},
        'gemini_direct': {'last_check': None, 'status': 'checking', 'response_time': None}
    }
    langchain_health_cache = {'last_check': None}
    
    return {"message": "Health cache cleared. Call /health to get fresh status."}

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
            'vertex': {'status': 'checking'},
            'gemini_direct': {'status': 'checking'}
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
    
    # Check Vertex AI (used for ALL Gemini requests)
    if (model_health_cache['vertex']['last_check'] is None or 
        now - model_health_cache['vertex']['last_check'] > cache_duration):
        try:
            # Remove old service account if present (use ADC instead)
            import os
            os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)
            
            # Try to import and use Vertex adapter
            from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
            vertex_adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
            test_start = time.time()
            
            # Test Vertex with grounding
            response = await asyncio.wait_for(
                vertex_adapter.analyze_with_gemini(
                    prompt="Test",
                    use_grounding=True,
                    model_name="gemini-2.0-flash"
                ),
                timeout=5.0
            )
            
            response_time = int((time.time() - test_start) * 1000)
            if response.get('error'):
                # Vertex is configured but failing
                model_health_cache['vertex'] = {
                    'last_check': now,
                    'status': 'offline',
                    'response_time': None,
                    'message': 'ADC not configured - run: gcloud auth application-default login'
                }
            else:
                model_health_cache['vertex'] = {
                    'last_check': now,
                    'status': 'healthy' if response.get('content') else 'degraded',
                    'response_time': response_time
                }
        except ImportError:
            model_health_cache['vertex'] = {
                'last_check': now,
                'status': 'offline',
                'response_time': None,
                'message': 'Vertex adapter not available'
            }
        except asyncio.TimeoutError:
            model_health_cache['vertex'] = {
                'last_check': now,
                'status': 'degraded',
                'response_time': 5000,
                'message': 'Slow response'
            }
        except Exception as e:
            # Check what type of error it is
            error_str = str(e).lower()
            if 'credentials' in error_str or 'authentication' in error_str or 'permission' in error_str:
                # This is an actual auth issue
                model_health_cache['vertex'] = {
                    'last_check': now,
                    'status': 'offline',
                    'response_time': None,
                    'message': 'Authentication error - check WEF or ADC configuration'
                }
            else:
                # Some other error - but Vertex might still be working
                # Try a simpler test without grounding
                try:
                    from app.llm.adapters.vertex_genai_adapter import VertexGenAIAdapter
                    vertex_adapter = VertexGenAIAdapter(project="contestra-ai", location="europe-west4")
                    test_start = time.time()
                    
                    # Simple test without grounding
                    response = await asyncio.wait_for(
                        vertex_adapter.analyze_with_gemini(
                            prompt="What is 1+1?",
                            use_grounding=False,
                            model_name="gemini-2.0-flash"
                        ),
                        timeout=5.0
                    )
                    
                    response_time = int((time.time() - test_start) * 1000)
                    if response and response.get('content'):
                        # It works! Update status to healthy
                        model_health_cache['vertex'] = {
                            'last_check': now,
                            'status': 'healthy',
                            'response_time': response_time,
                            'message': 'Using WEF authentication'
                        }
                    else:
                        model_health_cache['vertex'] = {
                            'last_check': now,
                            'status': 'degraded',
                            'response_time': response_time,
                            'message': f'Partial functionality: {str(e)[:50]}'
                        }
                except:
                    # Really offline
                    model_health_cache['vertex'] = {
                        'last_check': now,
                        'status': 'offline',
                        'response_time': None,
                        'message': f'Error: {str(e)[:100]}'
                    }
    
    health_status['models']['vertex'] = {
        'status': model_health_cache['vertex']['status'],
        'avg_response_time_ms': model_health_cache['vertex']['response_time'],
        'message': model_health_cache['vertex'].get('message',
                  f"~{model_health_cache['vertex']['response_time']/1000:.1f}s avg" 
                  if model_health_cache['vertex']['response_time'] else None)
    }
    
    # Check Gemini Direct API
    if (model_health_cache['gemini_direct']['last_check'] is None or 
        now - model_health_cache['gemini_direct']['last_check'] > cache_duration):
        try:
            # Test Direct API with grounding support
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=settings.google_api_key)
            test_start = time.time()
            
            # Test with grounding capability
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Test",
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=10,
                    tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]
                )
            )
            
            response_time = int((time.time() - test_start) * 1000)
            if response.text:
                model_health_cache['gemini_direct'] = {
                    'last_check': now,
                    'status': 'healthy',
                    'response_time': response_time,
                    'message': 'Direct API with grounding'
                }
            else:
                model_health_cache['gemini_direct'] = {
                    'last_check': now,
                    'status': 'degraded',
                    'response_time': response_time,
                    'message': 'Empty response'
                }
        except Exception as e:
            model_health_cache['gemini_direct'] = {
                'last_check': now,
                'status': 'offline',
                'response_time': None,
                'message': 'API key not configured or API error'
            }
    
    health_status['models']['gemini_direct'] = {
        'status': model_health_cache['gemini_direct']['status'],
        'avg_response_time_ms': model_health_cache['gemini_direct']['response_time'],
        'message': model_health_cache['gemini_direct'].get('message',
                  f"~{model_health_cache['gemini_direct']['response_time']/1000:.1f}s avg" 
                  if model_health_cache['gemini_direct']['response_time'] else None)
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
    elif any(health_status['models'][m]['status'] == 'offline' for m in ['openai', 'vertex']):
        health_status['status'] = 'degraded'
    
    health_status['response_time_ms'] = int((time.time() - start_time) * 1000)
    
    return health_status

@router.get("/health/simple")
async def simple_health_check():
    """Simple health check for load balancers"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}