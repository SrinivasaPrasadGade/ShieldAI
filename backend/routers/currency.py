"""
Currency detection API router for ShieldAI.

Endpoints:
  POST /api/currency/verify          — Start async currency verification
  GET  /api/currency/result/{task_id} — Poll verification result
  GET  /api/currency/ficn-map        — FICN incident map data
  GET  /api/currency/stats           — Currency check statistics
"""

from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from models.schemas import (
    CurrencyVerifyResponse,
    CurrencyResultResponse,
    FICNMapResponse,
    CurrencyStatsResponse,
)
from services.currency_analyzer import get_currency_analyzer
from logging_config import get_logger

logger = get_logger("shield_ai.router.currency")

router = APIRouter(prefix="/api/currency", tags=["Currency Detection"])


@router.post("/verify", response_model=CurrencyVerifyResponse, status_code=202)
async def verify_currency(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    denomination: Optional[int] = Form(None),
    location: Optional[str] = Form(None),
):
    """
    Start an async currency verification task.

    Upload a currency note image for AI-powered authenticity analysis.
    Returns a task_id — poll /result/{task_id} for the result.

    Supports JPEG, PNG, and WebP images up to 10MB.
    """
    from config import settings

    # Validate file type
    content_type = image.content_type or "image/jpeg"
    if content_type not in settings.allowed_image_type_list:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported image format: {content_type}. Supported: {settings.ALLOWED_IMAGE_TYPES}",
        )

    # Read and validate size
    image_bytes = await image.read()
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=422, detail="Empty image file")

    # Validate denomination if provided
    if denomination is not None and denomination not in (10, 20, 50, 100, 200, 500, 2000):
        raise HTTPException(
            status_code=422,
            detail="Invalid denomination. Must be one of: 10, 20, 50, 100, 200, 500, 2000",
        )

    analyzer = get_currency_analyzer()
    task_id = analyzer.start_verification(image_bytes, denomination, location)

    # Dispatch background processing
    background_tasks.add_task(analyzer.run_verification, task_id)

    return {"task_id": task_id}


@router.get("/result/{task_id}", response_model=CurrencyResultResponse)
async def get_verification_result(task_id: str):
    """
    Poll for the result of a currency verification task.

    Returns status: pending, processing, complete, or failed.
    When complete, includes verdict, confidence, failed features, and analysis.
    """
    analyzer = get_currency_analyzer()
    result = analyzer.get_result(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return result


@router.get("/ficn-map", response_model=FICNMapResponse)
async def get_ficn_map():
    """
    Get FICN (Fake Indian Currency Note) incident locations for map overlay.
    Returns incidents where currency was flagged as COUNTERFEIT or SUSPICIOUS.
    """
    analyzer = get_currency_analyzer()
    incidents = await analyzer.get_ficn_map()
    return {"incidents": incidents}


@router.get("/stats", response_model=CurrencyStatsResponse)
async def get_currency_stats():
    """
    Get currency verification statistics.
    Includes total checked, FICN detected, detection rate, and denomination breakdown.
    """
    analyzer = get_currency_analyzer()
    stats = await analyzer.get_stats()
    return stats
