from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    
    upstash_redis_rest_url: Optional[str] = None
    upstash_redis_rest_token: Optional[str] = None
    
    openai_api_key: str
    google_api_key: str
    anthropic_api_key: str
    scraperapi_key: Optional[str] = None  # For geo-located API requests
    proxy_enabled: bool = False  # Enable proxy for country-specific requests
    exa_api_key: Optional[str] = None  # Exa.ai for semantic search
    langchain_api_key: Optional[str] = None
    langchain_tracing_v2: bool = True
    langchain_project: str = "ai-ranker"
    
    fly_api_token: Optional[str] = None  # Added for Fly.io deployment
    
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    
    class Config:
        env_file = ".env"

settings = Settings()