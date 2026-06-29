"""
ShieldAI Backend — FastAPI Application Entry Point

Production-grade API server for digital public safety intelligence.
Initializes databases, AI services, middleware, and all API routers.
"""

import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from logging_config import setup_logging, get_logger
from middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    global_exception_handler,
)

# Initialize logging first
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger("shield_ai.main")

# Track server start time for uptime reporting
_start_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Startup: initialize databases, AI services, task recovery.
    Shutdown: cleanup resources.
    """
    logger.info("server_starting", version=settings.APP_VERSION)

    # ── Startup ──────────────────────────────────────────────
    # 1. Initialize SQLite database
    from models.database import init_sqlite_db
    init_sqlite_db()
    logger.info("sqlite_initialized")

    # 2. Initialize async task store table
    from models.task_store import init_task_store, recover_stale, cleanup_expired
    init_task_store()

    # 3. Recover stale tasks from previous crashes
    recovered = recover_stale(timeout_minutes=settings.TASK_STALE_TIMEOUT_MINUTES)
    if recovered:
        logger.info("stale_tasks_recovered", count=recovered)

    # 4. Clean up expired tasks
    cleaned = cleanup_expired()
    if cleaned:
        logger.info("expired_tasks_cleaned", count=cleaned)

    # 5. Initialize Gemini service
    from services.gemini_service import init_gemini_service
    gemini_svc = init_gemini_service(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL,
    )
    logger.info("gemini_service_initialized", available=gemini_svc.is_available)

    # 6. Initialize BERT (may take 30-60s on first run for model download)
    if settings.ENABLE_BERT:
        logger.info("bert_init_starting", message="This may take a moment on first run...")
        from services.scam_detector import init_scam_detector
        # Pre-load the ScamDetector (and BERT if enabled) during startup so it doesn't block the first request
        init_scam_detector(enable_bert=settings.ENABLE_BERT, bert_model=settings.BERT_MODEL)

    logger.info(
        "server_ready",
        host=settings.HOST,
        port=settings.PORT,
        gemini=gemini_svc.is_available,
        cors_origins=settings.cors_origin_list,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("server_shutting_down")


# ── Create FastAPI Application ───────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered intelligence command centre for digital public safety. "
        "Detects digital fraud, counterfeit currency, and scam networks — "
        "shifting cybercrime response from reactive to proactive."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── Middleware Stack (order matters: last added = first executed) ───
# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)

# Request logging
app.add_middleware(RequestLoggingMiddleware)

# Request ID injection
app.add_middleware(RequestIDMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Global exception handler
app.add_exception_handler(Exception, global_exception_handler)


# ── Include Routers ──────────────────────────────────────────
from routers.scam import router as scam_router
from routers.currency import router as currency_router
from routers.graph import router as graph_router
from routers.geo import router as geo_router
from routers.citizen import router as citizen_router
from routers.webhook import router as webhook_router
from routers.risk import router as risk_router

app.include_router(scam_router)
app.include_router(currency_router)
app.include_router(graph_router)
app.include_router(geo_router)
app.include_router(citizen_router)
app.include_router(webhook_router)
app.include_router(risk_router)


# ── Health Check ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns service status, version, uptime, and dependency availability.
    """
    uptime_seconds = round(time.monotonic() - _start_time, 2)

    # Check Gemini availability
    from services.gemini_service import get_gemini_service
    gemini_available = get_gemini_service().is_available

    # Check SQLite
    sqlite_ok = False
    try:
        from models.database import get_sqlite_connection
        with get_sqlite_connection() as conn:
            conn.execute("SELECT 1")
            sqlite_ok = True
    except Exception:
        pass

    # Check Firestore
    firestore_ok = False
    try:
        from models.database import get_firestore_client
        get_firestore_client()
        firestore_ok = True
    except Exception:
        pass

    status = "healthy"
    status_code = 200
    if not sqlite_ok:
        status = "degraded"
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": settings.APP_VERSION,
            "uptime_seconds": uptime_seconds,
            "services": {
                "gemini": "available" if gemini_available else "unavailable (using fallback heuristics)",
                "sqlite": "connected" if sqlite_ok else "error",
                "firestore": "connected" if firestore_ok else "error",
            },
        }
    )
