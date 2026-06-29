"""
Citizen-facing service for ShieldAI.

Handles chatbot interactions via Gemini, fraud report creation
and tracking in Firestore.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from logging_config import get_logger
from services.gemini_service import get_gemini_service

logger = get_logger("shield_ai.citizen")


class CitizenService:
    """Citizen fraud shield — chatbot and reporting."""

    def __init__(self):
        self.gemini = get_gemini_service()
        self._db = None
        self._report_counter = 0

    @property
    def db(self):
        if self._db is None:
            from models.database import get_firestore_client
            self._db = get_firestore_client()
        return self._db

    async def chat(self, message: str, session_id: str, language: str = "en") -> dict:
        """
        Process a citizen chatbot message.

        Args:
            message: User's message
            session_id: Session ID for conversation continuity
            language: Language preference

        Returns:
            dict matching CitizenChatResponse schema
        """
        # 1. Get Gemini chat response
        gemini_result = await self.gemini.chat_response(message, session_id, language)

        response_text = gemini_result.get("response", "I'm here to help with fraud-related concerns.")
        risk_assessment = gemini_result.get("risk_assessment")

        # 2. Generate report link if risk detected
        report_link = None
        if risk_assessment and risk_assessment.get("detected_risk"):
            report_link = "/api/citizen/report"

        result = {
            "response": response_text,
            "risk_assessment": risk_assessment,
            "report_link": report_link,
            "session_id": session_id,
        }

        logger.info(
            "citizen_chat",
            session_id=session_id,
            risk_detected=bool(risk_assessment and risk_assessment.get("detected_risk")),
        )

        return result

    async def create_report(
        self,
        description: str,
        phone_number: Optional[str] = None,
        location: Optional[str] = None,
        contact_email: Optional[str] = None,
    ) -> dict:
        """
        Create a fraud report from a citizen submission.

        Args:
            description: Description of the incident
            phone_number: Optional suspicious phone number
            location: Optional location
            contact_email: Optional contact email

        Returns:
            dict matching CitizenReportResponse schema
        """
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Generate reference number: SAI-YYYY-XXXXXX
        self._report_counter += 1
        reference_number = f"SAI-{now.year}-{str(self._report_counter).zfill(6)}"

        report_data = {
            "id": report_id,
            "source": "web",
            "report_type": "other",  # Will be classified later
            "description": description,
            "phone_numbers": [phone_number] if phone_number else [],
            "account_numbers": [],
            "victim_location": {
                "city": location or "Unknown",
                "state": "Unknown",
                "pincode": "000000",
                "lat": 0.0,
                "lng": 0.0,
            },
            "risk_score": 0.0,
            "risk_label": "LOW",
            "gemini_classification": "pending",
            "detoxify_scores": {"toxicity": 0, "threat": 0, "insult": 0},
            "bert_confidence": 0.0,
            "scam_script_match": 0.0,
            "status": "pending",
            "contact_email": contact_email,
            "reference_number": reference_number,
            "created_at": now,
            "updated_at": now,
            "updates": [f"Report submitted on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"],
        }

        try:
            if self.db is not None:
                self.db.collection("fraud_reports").document(report_id).set(report_data)
                logger.info("citizen_report_created", report_id=report_id, reference=reference_number)
            else:
                logger.warning("firestore_offline_report_not_saved", report_id=report_id)

            # Dispatch Celery task for async report analysis & geocoding
            from tasks.scam_tasks import process_citizen_report_task
            process_citizen_report_task.delay(report_id)

            # Smart Upgrade: Add report to fraud network graph in SQLite
            try:
                from services.graph_service import get_graph_service
                graph_svc = get_graph_service()
                graph_svc.add_report_to_graph(
                    report_id=report_id,
                    phone_numbers=[phone_number] if phone_number else [],
                    account_numbers=[],
                    description=description
                )
                logger.info("citizen_report_added_to_graph", report_id=report_id)
            except Exception as graph_err:
                logger.error("citizen_report_graph_addition_failed", error=str(graph_err))

        except Exception as e:
            logger.error("citizen_report_creation_failed", error=str(e))
            if self.db is not None:
                raise

        next_steps = [
            f"Your report has been submitted with reference number {reference_number}.",
            "Our AI system will analyze the report and assign a risk level.",
            "You can track the status using the reference number.",
            "If this is an ongoing emergency, please call 112 or the cybercrime helpline at 1930 immediately.",
            "You may also file a formal complaint at cybercrime.gov.in.",
        ]

        return {
            "report_id": report_id,
            "reference_number": reference_number,
            "next_steps": next_steps,
        }

    async def get_report(self, report_id: str) -> Optional[dict]:
        """
        Get report status and updates.

        Args:
            report_id: Report ID to look up

        Returns:
            dict matching ReportStatusResponse, or None if not found
        """
        try:
            if self.db is None:
                return {
                    "status": "pending",
                    "updates": ["Report submitted successfully (Offline Mode)"],
                    "created_at": str(datetime.now(timezone.utc)),
                }

            doc = self.db.collection("fraud_reports").document(report_id).get()
            if not doc.exists:
                return None

            data = doc.to_dict()
            return {
                "status": data.get("status", "pending"),
                "updates": data.get("updates", []),
                "created_at": str(data.get("created_at", "")),
            }
        except Exception as e:
            logger.error("get_report_failed", report_id=report_id, error=str(e))
            return None


# Module-level singleton
_citizen_service: CitizenService | None = None


def get_citizen_service() -> CitizenService:
    """Get the CitizenService singleton."""
    global _citizen_service
    if _citizen_service is None:
        _citizen_service = CitizenService()
    return _citizen_service
