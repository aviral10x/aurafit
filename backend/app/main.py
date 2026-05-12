from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.routes import router
from app.services.analysis_jobs import start_analysis_worker, stop_analysis_worker
from app.services.rule_engine import rule_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB and load rules
    try:
        await init_db()
    except Exception as e:
        print(f"[WARNING] Database connection failed: {e}")
        print("[WARNING] Running without database — mock mode only")
    rule_engine.load()
    print(f"[INFO] Rule engine loaded {len(rule_engine.get_all_categories())} categories")
    await start_analysis_worker()
    try:
        yield
    finally:
        await stop_analysis_worker()


app = FastAPI(title="AuraFit API", version="2.0.0", lifespan=lifespan)

cors_origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
