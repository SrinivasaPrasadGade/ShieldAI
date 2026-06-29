"""
Alert management service for ShieldAI.

Manages alerts in Firestore — creation, retrieval, and status updates.
"""

import uuid
import json
import redis
from datetime import datetime, timezone
from typing import Optional

from logging_config import get_logger

logger = get_logger("shield_ai.alerts")

_redis_pool = None
def _get_redis():
    global _redis_pool
    from config import settings
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
    return redis.Redis(connection_pool=_redis_pool)


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
        Create a new alert in Firestore and publish to Redis.

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

        # 1. Store in Firestore (if available)
        try:
            if self.db is not None:
                self.db.collection("alerts").document(alert_id).set(alert_data)
                logger.info("alert_created", alert_id=alert_id, type=alert_type, severity=severity)
            else:
                logger.warning("firestore_offline_alert_not_saved", alert_id=alert_id)
        except Exception as e:
            logger.error("alert_creation_failed", error=str(e))
            # Don't raise in local dev if Firestore connection fails, but let's log it
            if self.db is not None:
                raise

        # 2. Publish to Redis pub/sub for real-time dashboard updates
        try:
            redis_alert = alert_data.copy()
            redis_alert["created_at"] = now.isoformat()
            
            r = _get_redis()
            r.publish("new_alerts", json.dumps(redis_alert))
            logger.info("alert_published_to_redis", alert_id=alert_id)
        except Exception as redis_err:
            logger.error("redis_publish_failed", error=str(redis_err))

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
            if self.db is None:
                # Return high-fidelity local mock alerts for offline dashboard demo
                now_str = datetime.now(timezone.utc).isoformat()
                mock_alerts = [
                    {
                        "id": "alert_mamba_critical",
                        "alert_type": "fraud_ring_identified",
                        "severity": "CRITICAL",
                        "title": "Critical Threat: Operation Mamba Coordinated digital arrest ring detected",
                        "description": "WhatsApp alert: suspect +917892019283 impersonating CBI officials. Skype video calls used to lock Aadhaar cards and demand clearance fees.",
                        "linked_report_id": "rep_mamba_01",
                        "linked_phone": "+917892019283",
                        "location": {"lat": 17.3850, "lng": 78.4867, "city": "Hyderabad"},
                        "is_read": False,
                        "created_at": now_str,
                    },
                    {
                        "id": "alert_kappa_high",
                        "alert_type": "fraud_ring_identified",
                        "severity": "HIGH",
                        "title": "Fraud Ring Detected: Ring Kappa Stock Investment Scam",
                        "description": "Correlated Stock Market WhatsApp/Telegram tip scam. Victim lured to download BullTrade app and send Rs 50,000 commission fee.",
                        "linked_report_id": "rep_kappa_01",
                        "linked_phone": "+919987123456",
                        "location": {"lat": 12.9716, "lng": 77.5946, "city": "Bengaluru"},
                        "is_read": False,
                        "created_at": now_str,
                    },
                    {
                        "id": "alert_ficn_malda",
                        "alert_type": "ficn_detected",
                        "severity": "HIGH",
                        "title": "Counterfeit Currency Alert: Malda Hotspot",
                        "description": "High volume of counterfeit Rs 500 notes intercepted in Malda, West Bengal. UV thread fluorescence failed.",
                        "linked_report_id": "rep_ficn_01",
                        "linked_phone": "",
                        "location": {"lat": 25.0108, "lng": 88.1406, "city": "Malda"},
                        "is_read": False,
                        "created_at": now_str,
                    },
                    {
                        "id": "alert_scam_delhi",
                        "alert_type": "scam_detected",
                        "severity": "MEDIUM",
                        "title": "Active Telecom SIM Block Scam in New Delhi",
                        "description": "TRAI impersonation warning in Delhi. Suspect calling from +919900112233 claiming sims will block in 2 hours.",
                        "linked_report_id": "rep_scam_01",
                        "linked_phone": "+919900112233",
                        "location": {"lat": 28.7041, "lng": 77.1025, "city": "Delhi"},
                        "is_read": False,
                        "created_at": now_str,
                    }
                ]
                if severity:
                    mock_alerts = [a for a in mock_alerts if a["severity"] == severity]
                return {"alerts": mock_alerts[:limit], "total": len(mock_alerts)}

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
            from services.firestore_utils import count_query
            total = count_query(alerts_ref)
            if total is None:
                total = len(alerts)

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
            if self.db is None:
                logger.warning("firestore_offline_cannot_mark_read", alert_id=alert_id)
                return False
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
_alert_service: AlertService | None = None


def get_alert_service() -> AlertService:
    """Get the AlertService singleton."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
