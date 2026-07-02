import pytest
import unittest.mock as mock
import json
from services.gemini_service import (
    GeminiService,
    SCAM_DETECTION_SYSTEM_PROMPT,
    CURRENCY_ANALYSIS_SYSTEM_PROMPT,
    CITIZEN_SHIELD_SYSTEM_PROMPT,
    EVIDENCE_PACKAGE_PROMPT,
)

def test_prompt_constants():
    """Verify that all prompts are defined and contain relevant keywords."""
    assert "digital_arrest" in SCAM_DETECTION_SYSTEM_PROMPT.lower() or "digital arrest" in SCAM_DETECTION_SYSTEM_PROMPT.lower()
    assert "mahatma gandhi" in CURRENCY_ANALYSIS_SYSTEM_PROMPT.lower()
    assert "citizen fraud shield" in CITIZEN_SHIELD_SYSTEM_PROMPT.lower()
    assert "magistrate" in EVIDENCE_PACKAGE_PROMPT.lower() or "forensic" in EVIDENCE_PACKAGE_PROMPT.lower()


def test_fallback_scam_analysis_detects_common_ci_scam_patterns():
    """Verify offline fallback catches common utility and OTP scam wording."""
    svc = GeminiService(api_key="")

    utility = svc._fallback_scam_analysis(
        "Your electricity bill for the last month is pending. "
        "Your power will be cut off tonight by 9 PM. Call this number to pay."
    )
    assert utility["risk_label"] in {"MEDIUM", "HIGH"}
    assert utility["classification"] == "utility_scam"

    otp = svc._fallback_scam_analysis(
        "This is customer support. Your bank account is blocked due to suspicious activity. "
        "Share your OTP to unblock."
    )
    assert otp["risk_label"] in {"MEDIUM", "HIGH"}
    assert otp["classification"] == "phishing"

@pytest.mark.asyncio
async def test_evidence_synthesis_fallback():
    """Verify evidence package generation fallback behavior when Gemini is offline."""
    svc = GeminiService(api_key="")
    assert not svc.is_available
    
    mock_intel_data = {
        "cluster": {
            "id": 1,
            "name": "Operation Mamba",
            "cluster_name": "Operation Mamba",
            "risk_level": "HIGH",
            "operation_type": "digital_arrest",
            "geographic_span": "Cross-border"
        },
        "summary": {
            "total_entities": 5,
            "total_relationships": 10,
            "total_linked_reports": 2,
            "high_risk_entities": 3,
            "central_nodes": 1
        },
        "key_findings": [
            "Identified 1 central node(s)",
            "5 entities flagged as high risk"
        ]
    }
    
    report = await svc.generate_evidence_package(mock_intel_data)
    assert "FORENSIC INTELLIGENCE REPORT" in report
    assert "Operation Mamba" in report
    assert "Cross-border" in report
    assert "total_entities" not in report  # Ensures it's formatted rather than a raw dump

@pytest.mark.asyncio
async def test_gemini_evidence_synthesis_success():
    """Verify evidence package generation calls Gemini API successfully under mock settings."""
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.text = "Mocked forensic report output from Gemini AI."
    
    # Configure mock generate_content (async call)
    mock_client.aio.models.generate_content = mock.AsyncMock(return_value=mock_response)
    
    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True
    
    mock_intel_data = {
        "cluster": {"id": 1, "name": "Operation Mamba"}
    }
    
    report = await svc.generate_evidence_package(mock_intel_data)
    assert report == "Mocked forensic report output from Gemini AI."
    
    # Assert generate_content was called with the correct prompts
    mock_client.aio.models.generate_content.assert_called_once()
    args, kwargs = mock_client.aio.models.generate_content.call_args
    assert "Operation Mamba" in kwargs["contents"]
    assert kwargs["model"] == "gemini-2.0-flash"

@pytest.mark.asyncio
async def test_gemini_scam_analysis_success():
    """Verify scam analysis returns formatted results via mock Gemini call."""
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({
        "risk_score": 0.9,
        "risk_label": "HIGH",
        "classification": "digital_arrest_scam",
        "scam_type": "Digital Arrest",
        "explanation": "Test explanation",
        "recommended_action": "Test action"
    })
    
    mock_client.aio.models.generate_content = mock.AsyncMock(return_value=mock_response)
    
    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True
    
    result = await svc.analyze_scam_text("test scam text")
    assert result["risk_score"] == 0.9
    assert result["risk_label"] == "HIGH"
    assert result["classification"] == "digital_arrest_scam"

@pytest.mark.asyncio
async def test_gemini_currency_analysis_success():
    """Verify currency checking returns formatted results via mock Gemini call."""
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({
        "verdict": "GENUINE",
        "confidence": 0.95,
        "failed_features": [],
        "analysis": "Looks genuine note."
    })
    
    mock_client.aio.models.generate_content = mock.AsyncMock(return_value=mock_response)
    
    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True
    
    result = await svc.analyze_currency_image(b"dummy_bytes", 500)
    assert result["verdict"] == "GENUINE"
    assert result["confidence"] == 0.95

@pytest.mark.asyncio
async def test_gemini_chat_success():
    """Verify chatbot returns formatted responses via mock Gemini call."""
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.text = json.dumps({
        "response": "Hello citizen, do not worry.",
        "risk_assessment": {
            "detected_risk": False,
            "risk_level": "NONE",
            "risk_type": None
        }
    })
    
    mock_client.aio.models.generate_content = mock.AsyncMock(return_value=mock_response)
    
    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True
    
    result = await svc.chat_response("hello", "session-123")
    assert result["response"] == "Hello citizen, do not worry."
