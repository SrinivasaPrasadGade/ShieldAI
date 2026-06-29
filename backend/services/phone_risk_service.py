"""
Phone number risk assessment service for ShieldAI.

Cross-references a phone number across the SQLite fraud graph
and Firestore fraud reports to build a composite risk profile.
"""

from typing import Optional

from logging_config import get_logger
from models.database import get_sqlite_connection

logger = get_logger("shield_ai.phone_risk")


class PhoneRiskService:
    """Cross-references phone numbers across all data stores."""

    async def assess_risk(self, phone_number: str) -> dict:
        """
        Assess the risk of a phone number.

        Queries:
        1. SQLite entities table (fraud graph)
        2. Firestore fraud_reports (historical reports)

        Args:
            phone_number: Phone number to assess

        Returns:
            dict matching PhoneRiskResponse schema
        """
        # Normalize phone number for matching
        cleaned = phone_number.strip().replace(" ", "").replace("-", "")

        # 1. Check SQLite graph
        entity = None
        with get_sqlite_connection() as conn:
            # Exact match first
            row = conn.execute(
                "SELECT * FROM entities WHERE value = ? AND entity_type = 'phone'",
                (cleaned,),
            ).fetchone()

            if not row:
                # Try partial match (last 10 digits)
                last_10 = cleaned[-10:] if len(cleaned) >= 10 else cleaned
                row = conn.execute(
                    "SELECT * FROM entities WHERE value LIKE ? AND entity_type = 'phone'",
                    (f"%{last_10}",),
                ).fetchone()

            if row:
                entity = dict(row)

        # 2. Check Firestore fraud reports
        fraud_types = []
        last_reported = None
        report_count_firestore = 0

        try:
            from models.database import get_firestore_client
            db = get_firestore_client()

            # Query reports containing this phone number
            reports_ref = db.collection("fraud_reports")
            # Firestore array-contains query
            query = reports_ref.where("phone_numbers", "array_contains", cleaned).stream()

            for doc in query:
                data = doc.to_dict()
                report_count_firestore += 1

                rtype = data.get("report_type", "unknown")
                if rtype not in fraud_types:
                    fraud_types.append(rtype)

                reported_at = str(data.get("created_at", ""))
                if reported_at and (not last_reported or reported_at > last_reported):
                    last_reported = reported_at

        except Exception as e:
            logger.error("firestore_phone_check_failed", error=str(e))

        # 3. Compute composite risk
        if entity:
            risk_score = entity.get("risk_score", 0.0)
            report_count = entity.get("report_count", 0) + report_count_firestore
            in_network = entity.get("cluster_id") is not None
        else:
            # Not in graph — compute from Firestore reports alone
            risk_score = min(1.0, report_count_firestore * 0.2)  # Each report adds 0.2
            report_count = report_count_firestore
            in_network = False

        # Risk label
        if risk_score >= 0.7:
            risk_label = "HIGH"
        elif risk_score >= 0.4:
            risk_label = "MEDIUM"
        else:
            risk_label = "LOW"

        result = {
            "risk_score": round(risk_score, 3),
            "risk_label": risk_label,
            "report_count": report_count,
            "last_reported": last_reported,
            "fraud_types": fraud_types,
            "in_network": in_network,
        }

        logger.info(
            "phone_risk_assessed",
            phone=cleaned[-4:],  # Only log last 4 digits for privacy
            risk_score=result["risk_score"],
            in_network=in_network,
        )

        return result


# Module-level singleton
_phone_risk_service: PhoneRiskService | None = None


def get_phone_risk_service() -> PhoneRiskService:
    """Get the PhoneRiskService singleton."""
    global _phone_risk_service
    if _phone_risk_service is None:
        _phone_risk_service = PhoneRiskService()
    return _phone_risk_service
