from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import experiments, prompts, entities, metrics, dashboard, tracked_phrases, simple_analysis, real_analysis, embedding_analysis, comprehensive_analysis, pure_beeb, weekly_tracking, entity_extraction_beeb, contestra_v2_analysis, llm_crawlability, concordance_analysis, hybrid_analysis, brand_entity_strength, brand_entity_strength_v2, crawler_monitor, domains, crawler_monitor_v2, bot_analytics, prompt_tracking, prompt_tracking_celery, prompt_tracking_background, prompt_integrity, health, countries, prompter_v7, grounding_test
from app.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI Rank & Influence Tracker",
    version="2.0.0",  # Updated version for Contestra features
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(tracked_phrases.router, prefix="/api", tags=["tracked_phrases"])
app.include_router(simple_analysis.router, prefix="/api", tags=["analysis"])
app.include_router(real_analysis.router, prefix="/api", tags=["real_analysis"])
app.include_router(embedding_analysis.router, prefix="/api", tags=["embedding_analysis"])
app.include_router(comprehensive_analysis.router, prefix="/api", tags=["comprehensive_analysis"])
app.include_router(pure_beeb.router, prefix="/api", tags=["pure_beeb"])
app.include_router(weekly_tracking.router, prefix="/api", tags=["weekly_tracking"])
app.include_router(entity_extraction_beeb.router, prefix="/api", tags=["entity_beeb"])
app.include_router(contestra_v2_analysis.router, prefix="/api", tags=["contestra_v2"])
app.include_router(llm_crawlability.router, prefix="/api", tags=["crawlability"])
app.include_router(concordance_analysis.router, prefix="/api", tags=["concordance"])
app.include_router(hybrid_analysis.router, prefix="/api", tags=["hybrid"])
app.include_router(brand_entity_strength.router, prefix="/api", tags=["entity_strength"])
app.include_router(brand_entity_strength_v2.router, prefix="/api", tags=["entity_strength_v2"])
app.include_router(crawler_monitor.router, prefix="/api/crawler", tags=["crawler_monitor"])
app.include_router(domains.router, prefix="/api/domains", tags=["domains"])
app.include_router(crawler_monitor_v2.router, prefix="/api/crawler/v2", tags=["crawler_v2"])
app.include_router(bot_analytics.router, prefix="/api/bot-analytics", tags=["bot_analytics"])
app.include_router(prompt_tracking.router, tags=["prompt_tracking"])
app.include_router(prompt_tracking_celery.router, tags=["prompt_tracking_celery"])
app.include_router(prompt_tracking_background.router, tags=["prompt_tracking_background"])
app.include_router(prompt_integrity.router, tags=["prompt_integrity"])
app.include_router(health.router, tags=["health"])
app.include_router(countries.router, tags=["countries"])
app.include_router(prompter_v7.router, tags=["prompter_v7"])
app.include_router(grounding_test.router, prefix="/api/grounding-test", tags=["grounding_test"])

@app.get("/")
async def root():
    return {"message": "AI Rank & Influence Tracker API", "version": "2.1.0"}
