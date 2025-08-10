from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import experiments, prompts, entities, metrics, dashboard, tracked_phrases, simple_analysis, real_analysis, embedding_analysis, comprehensive_analysis, pure_beeb, weekly_tracking, entity_extraction_beeb
from app.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI Rank & Influence Tracker",
    version="2.0.0",  # Updated version for Dejan.ai features
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

@app.get("/")
async def root():
    return {"message": "AI Rank & Influence Tracker API", "version": "1.0.0"}