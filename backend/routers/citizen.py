"""
Citizen Shield API router for ShieldAI.

Endpoints:
  POST /api/citizen/chat              — Chatbot interaction
  POST /api/citizen/report            — Submit fraud report
  GET  /api/citizen/report/{report_id} — Check report status
"""

from fastapi import APIRouter, HTTPException, Request

from models.schemas import (
    CitizenChatRequest,
    CitizenChatResponse,
    CitizenReportRequest,
    CitizenReportResponse,
    ReportStatusResponse,
)
from services.citizen_service import get_citizen_service
from logging_config import get_logger

logger = get_logger("shield_ai.router.citizen")

router = APIRouter(prefix="/api/citizen", tags=["Citizen Shield"])


@router.post("/chat", response_model=CitizenChatResponse)
async def chat(request: CitizenChatRequest, http_request: Request):
    """
    Interact with the Citizen Fraud Shield chatbot.

    Send a message and receive an AI-powered response with optional
    risk assessment. Supports session continuity via session_id.
    """
    ip = http_request.client.host if http_request.client else "unknown"
    service = get_citizen_service()
    result = await service.chat(
        message=request.message,
        session_id=request.session_id,
        language=request.language,
        ip=ip,
    )
    return result


@router.post("/report", response_model=CitizenReportResponse, status_code=201)
async def create_report(request: CitizenReportRequest):
    """
    Submit a fraud report as a citizen.

    Returns a report_id, reference number (SAI-YYYY-XXXXXX),
    and next steps including official reporting channels.
    """
    service = get_citizen_service()
    try:
        result = await service.create_report(
            description=request.description,
            phone_number=request.phone_number,
            location=request.location,
            contact_email=request.contact_email,
            source=request.source,
        )
        return result
    except Exception as e:
        logger.error("report_creation_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create report. Please try again.")


@router.get("/report/{report_id}", response_model=ReportStatusResponse)
async def get_report_status(report_id: str):
    """
    Check the status of a previously submitted fraud report.
    Returns current status, updates history, and creation timestamp.
    """
    service = get_citizen_service()
    result = await service.get_report(report_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    return result
