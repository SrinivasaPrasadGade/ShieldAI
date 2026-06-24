"""
Alert management service for ShieldAI.

Manages alerts in Firestore — creation, retrieval, and status updates.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from logging_config import get_logger

logger = get_logger("shield_ai.alerts")


class AlertService:
    """Firestore alerts collection management."""

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            from models.database import get_firestore_client
            self._db = get_firestore_client()
        return self._db

    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        linked_report_id: Optional[str] = None,
        linked_phone: Optional[str] = None,
        location: Optional[dict] = None,
    ) -> str:
        """
        Create a new alert in Firestore.

        Args:
            alert_type: scam_detected, ficn_detected, fraud_ring_identified, new_hotspot
            severity: CRITICAL, HIGH, MEDIUM
            title: Alert title
            description: Alert description
            linked_report_id: Optional linked report ID
            linked_phone: Optional linked phone number
            location: Optional {lat, lng, city} dict

        Returns:
            Generated alert ID
        """
        alert_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        alert_data = {
            "id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description,
            "linked_report_id": linked_report_id,
            "linked_phone": linked_phone,
            "location": location or {"lat": 0, "lng": 0, "city": "Unknown"},
            "is_read": False,
            "created_at": now,
        }

        try:
            self.db.collection("alerts").document(alert_id).set(alert_data)
            logger.info("alert_created", alert_id=alert_id, type=alert_type, severity=severity)
        except Exception as e:
            logger.error("alert_creation_failed", error=str(e))
            raise

        return alert_id

    async def get_alerts(self, limit: int = 20, severity: Optional[str] = None) -> dict:
        """
        Retrieve alerts from Firestore.

        Args:
            limit: Maximum alerts to return
            severity: Optional severity filter

        Returns:
            dict with alerts list and total count
        """
        try:
            alerts_ref = self.db.collection("alerts")

            if severity:
                query = alerts_ref.where("severity", "==", severity)
            else:
                query = alerts_ref

            query = query.order_by("created_at", direction="DESCENDING").limit(limit)
            docs = list(query.stream())

            alerts = []
            for doc in docs:
                data = doc.to_dict()
                alerts.append({
                    "id": data.get("id", doc.id),
                    "alert_type": data.get("alert_type", ""),
                    "severity": data.get("severity", ""),
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "linked_report_id": data.get("linked_report_id"),
                    "linked_phone": data.get("linked_phone"),
                    "location": data.get("location"),
                    "is_read": data.get("is_read", False),
                    "created_at": str(data.get("created_at", "")),
                })

            # Get total count
            total_docs = list(alerts_ref.stream())
            total = len(total_docs)

            return {"alerts": alerts, "total": total}

        except Exception as e:
            logger.error("get_alerts_failed", error=str(e))
            return {"alerts": [], "total": 0}

    async def mark_read(self, alert_id: str) -> bool:
        """
        Mark an alert as read.

        Args:
            alert_id: Alert ID to update

        Returns:
            True if updated, False if not found
        """
        try:
            doc_ref = self.db.collection("alerts").document(alert_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({"is_read": True})
                logger.info("alert_marked_read", alert_id=alert_id)
                return True
            return False
        except Exception as e:
            logger.error("mark_alert_read_failed", alert_id=alert_id, error=str(e))
            return False


# Module-level singleton
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """Get the AlertService singleton."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
