import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from models.schemas import FraudReport, VictimLocation, DetoxifyScores

def test_fraud_report_schema():
    report = FraudReport(
        id="test_report_123",
        source="api",
        report_type="digital_arrest",
        description="Scammer pretending to be Customs officer demanded payment.",
        phone_numbers=["+919876543210"],
        account_numbers=["123456789012"],
        victim_location=VictimLocation(
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            lat=19.0760,
            lng=72.8777
        ),
        risk_score=0.92,
        risk_label="HIGH",
        gemini_classification="Matches Customs seizure scam.",
        detoxify_scores=DetoxifyScores(
            toxicity=0.85,
            threat=0.90,
            insult=0.10
        ),
        bert_confidence=0.89,
        scam_script_match=0.94,
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert report.id == "test_report_123"
    assert report.source == "api"
    assert report.risk_label == "HIGH"
    assert report.victim_location.city == "Mumbai"
