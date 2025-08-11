from fastapi import FastAPI
from .routers import brands, prompts, schedules, runs

app = FastAPI(title="AI Visibility Prompt Tracking API (NONE|WEB grounding)")
app.include_router(brands.router)
app.include_router(prompts.router)
app.include_router(schedules.router)
app.include_router(runs.router)

@app.get("/healthz")
def health():
    return {"ok": True}
