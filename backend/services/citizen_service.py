"""
Citizen-facing service for ShieldAI.

Handles chatbot interactions via Gemini, fraud report creation
and tracking in Firestore.
"""

import uuid
import threading
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

    @property
    def db(self):
        if self._db is None:
            from models.database import get_firestore_client
            self._db = get_firestore_client()
        return self._db

    async def chat(self, message: str, session_id: str, language: str = "en", ip: str = "unknown") -> dict:
        """
        Process a citizen chatbot message.

        Args:
            message: User's message
            session_id: Session ID for conversation continuity
            language: Language preference
            ip: Client IP address for rate limiting

        Returns:
            dict matching CitizenChatResponse schema
        """
        import redis
        import json
        from config import settings
        
        try:
            r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            
            # Rate limiting: Max 10 messages per minute per IP
            rate_key = f"rate_limit:chat:{ip}"
            count = r.incr(rate_key)
            if count == 1:
                r.expire(rate_key, 60)
            if count > 10:
                logger.warning("chat_rate_limit_exceeded", ip=ip, session_id=session_id)
                return {
                    "response": "You are sending messages too quickly. Please wait a moment.",
                    "risk_assessment": None,
                    "report_link": None,
                    "session_id": session_id,
                    "error": "rate_limit"
                }

            # Retrieve chat history
            history_key = f"chat_history:{session_id}"
            history_items = r.lrange(history_key, 0, -1)
            
            context = ""
            if history_items:
                context = "Previous interaction in this session:\n"
                for item in history_items[-10:]:  # Keep last 10 messages
                    msg = json.loads(item)
                    context += f"{msg['role']}: {msg['text']}\n"
                context += "\n"
        except Exception as e:
            logger.error("redis_chat_history_failed", error=str(e))
            r = None
            context = ""

        # Build prompt
        full_message = f"{context}User: {message}"

        # 1. Get Gemini chat response
        gemini_result = await self.gemini.chat_response(full_message, session_id, language)

        response_text = gemini_result.get("response", "I'm here to help with fraud-related concerns.")
        risk_assessment = gemini_result.get("risk_assessment")

        # Save to history
        if r:
            try:
                r.rpush(history_key, json.dumps({"role": "User", "text": message}))
                r.rpush(history_key, json.dumps({"role": "Assistant", "text": response_text}))
                r.expire(history_key, 86400)  # 24 hours TTL
            except Exception as e:
                logger.error("redis_chat_history_save_failed", error=str(e))

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
        source: str = "web",
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
        current_year = now.year

        # Generate reference number: SAI-YYYY-XXXXXX using DB sequence
        from models.database import get_sqlite_connection
        with get_sqlite_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO reference_sequences (year, counter) VALUES (?, 0)", (current_year,))
            conn.execute("UPDATE reference_sequences SET counter = counter + 1 WHERE year = ?", (current_year,))
            cursor = conn.execute("SELECT counter FROM reference_sequences WHERE year = ?", (current_year,))
            row = cursor.fetchone()
            new_counter = row['counter']
            
        reference_number = f"SAI-{current_year}-{str(new_counter).zfill(6)}"

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
                from google.cloud import firestore
                batch = self.db.batch()
                report_ref = self.db.collection("fraud_reports").document(report_id)
                batch.set(report_ref, report_data)
                
                stats_ref = self.db.collection("system_stats").document("global_counts")
                stats_updates = {"total_reports": firestore.Increment(1)}
                if source == "chat":
                    stats_updates["chat_conversions"] = firestore.Increment(1)
                batch.set(stats_ref, stats_updates, merge=True)
                
                batch.commit()
                logger.info("citizen_report_created", report_id=report_id, reference=reference_number)
            else:
                logger.warning("firestore_offline_report_saved_locally", report_id=report_id)
                import json
                with get_sqlite_connection() as conn:
                    conn.execute(
                        "INSERT INTO offline_reports (id, payload) VALUES (?, ?)", 
                        (report_id, json.dumps(report_data, default=str))
                    )

            # Dispatch Celery task for async report analysis & geocoding
            try:
                from tasks.scam_tasks import process_citizen_report_task
                process_citizen_report_task.delay(report_id)
            except Exception as celery_err:
                logger.error("celery_dispatch_failed", error=str(celery_err), report_id=report_id)

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
                from models.database import get_sqlite_connection
                import json
                with get_sqlite_connection() as conn:
                    cursor = conn.execute("SELECT payload FROM offline_reports WHERE id = ?", (report_id,))
                    row = cursor.fetchone()
                    if row:
                        data = json.loads(row['payload'])
                        return {
                            "status": data.get("status", "pending"),
                            "updates": data.get("updates", ["Report submitted successfully (Offline Mode)"]),
                            "created_at": str(data.get("created_at", "")),
                        }
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
