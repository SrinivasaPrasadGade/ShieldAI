"""
Phone number risk score API router for ShieldAI.

Endpoint:
  POST /api/risk/phone — Phone number risk assessment
"""

from fastapi import APIRouter

from models.schemas import PhoneRiskRequest, PhoneRiskResponse
from services.phone_risk_service import get_phone_risk_service
from logging_config import get_logger

logger = get_logger("shield_ai.router.risk")

router = APIRouter(prefix="/api/risk", tags=["Risk Assessment"])


@router.post("/phone", response_model=PhoneRiskResponse)
async def assess_phone_risk(request: PhoneRiskRequest):
    """
    Assess the fraud risk of a phone number.

    Cross-references the number against the fraud network graph (SQLite)
    and historical fraud reports (Firestore) to compute a composite risk score.

    Returns risk score, label, report count, fraud types, and network membership.
    """
    service = get_phone_risk_service()
    result = await service.assess_risk(phone_number=request.phone_number)
    return result
