from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)

MODELS = [
    ("openai", "gpt-5-pro", {"supports_geo": False, "supports_web_search": False, "returns_citations": False, "max_tokens": 8000}),
    ("anthropic", "claude-3.7-sonnet", {"supports_geo": False, "supports_web_search": False, "returns_citations": False, "max_tokens": 8000}),
    ("google", "gemini-2.5-pro", {"supports_geo": False, "supports_web_search": False, "returns_citations": False, "max_tokens": 8000}),
    ("perplexity", "pplx-70b-online", {"supports_geo": True, "supports_web_search": True, "returns_citations": True, "max_tokens": 8000}),
]

SQL = "INSERT INTO models (provider, model_key, capabilities, status) VALUES (:provider,:model_key,:capabilities::jsonb,'active') ON CONFLICT (provider, model_key) DO NOTHING;"

if __name__ == "__main__":
    with engine.begin() as conn:
        for provider, key, caps in MODELS:
            conn.execute(text(SQL), {"provider": provider, "model_key": key, "capabilities": caps})
        print(f"Seeded {len(MODELS)} model(s).")
