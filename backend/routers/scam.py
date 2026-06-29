"""
Scam detection API router for ShieldAI.

Endpoints:
  POST /api/scam/analyze       — Text scam analysis
  POST /api/scam/analyze-audio — Audio file scam analysis
  GET  /api/scam/alerts        — List alerts
  GET  /api/scam/stats         — Scam statistics
"""

from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from models.schemas import (
    ScamAnalyzeRequest,
    ScamAnalyzeResponse,
    ScamAudioResponse,
    AlertListResponse,
    ScamStatsResponse,
)
from services.scam_detector import get_scam_detector
from logging_config import get_logger

logger = get_logger("shield_ai.router.scam")

router = APIRouter(prefix="/api/scam", tags=["Scam Detection"])


@router.post("/analyze", response_model=ScamAnalyzeResponse)
async def analyze_text(request: ScamAnalyzeRequest):
    """
    Analyze text for scam patterns using Gemini AI + Hugging Face zero-shot classification (BART-MNLI).

    Returns a composite risk score, classification, explanation, and recommended action.
    Automatically generates alerts for HIGH risk detections.
    """
    detector = get_scam_detector()
    result = await detector.analyze_text(
        text=request.text,
        source_phone=request.source_phone,
        language=request.language,
    )
    return result


@router.post("/analyze-audio", response_model=ScamAudioResponse)
async def analyze_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe an audio file and analyze the transcript for scam patterns.

    Supports MP3, WAV, OGG, FLAC, and WebM formats.
    Uses Gemini's native audio capabilities for transcription.
    """
    from config import settings

    # Validate file type
    content_type = audio_file.content_type or "audio/mpeg"
    if content_type not in settings.allowed_audio_type_list:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported audio format: {content_type}. Supported: {settings.ALLOWED_AUDIO_TYPES}",
        )

    # Validate file size
    audio_bytes = await audio_file.read()
    if len(audio_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=422, detail="Empty audio file")

    detector = get_scam_detector()

    try:
        result = await detector.analyze_audio(audio_bytes, mime_type=content_type)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    limit: int = Query(20, ge=1, le=100, description="Maximum alerts to return"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM"),
):
    """
    Retrieve scam detection alerts, optionally filtered by severity.
    Returns alerts ordered by creation time (newest first).
    """
    if severity and severity not in ("CRITICAL", "HIGH", "MEDIUM"):
        raise HTTPException(status_code=422, detail="Severity must be CRITICAL, HIGH, or MEDIUM")

    detector = get_scam_detector()
    result = await detector.get_alerts(limit=limit, severity=severity)
    return result


@router.get("/stats", response_model=ScamStatsResponse)
async def get_stats(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
):
    """
    Get scam analysis statistics for the specified time period.
    Includes total analyzed, risk breakdown, top scam types, and daily trend.
    """
    detector = get_scam_detector()
    result = await detector.get_stats(days=days)
    return result
