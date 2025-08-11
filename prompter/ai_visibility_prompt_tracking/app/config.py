from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOWED_COUNTRIES: set[str] = {"US","GB","AE","DE","CH","SG"}
    DEFAULT_LANGUAGE: str = "en-US"

    class Config:
        env_file = ".env"

settings = Settings()
