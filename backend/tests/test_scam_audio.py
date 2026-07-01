"""
Unit and integration tests for the /api/scam/analyze-audio endpoint.

Covers:
- Successful audio transcription and scam analysis (happy path)
- GeminiService-level transcription success and failure via mock
- Unsupported audio format rejection (422)
- File too large rejection (413)
- Empty audio file rejection (422)
- Gemini unavailable / transcription failure (503)
- WAV format acceptance
- Full response schema validation
"""

import io
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

# Extend the firebase_admin mock already set up in conftest.py to also cover
# firebase_admin.exceptions, which middleware.py imports directly.
# Without this, importing `main` inside the client fixture raises:
#   ModuleNotFoundError: No module named 'firebase_admin.exceptions'
if "firebase_admin.exceptions" not in sys.modules:
    sys.modules["firebase_admin.exceptions"] = MagicMock()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_audio_bytes(size_bytes: int = 512) -> bytes:
    """Generate fake audio bytes for testing."""
    return b"\x00" * size_bytes


def _make_upload_file(content: bytes, content_type: str = "audio/mpeg", filename: str = "test.mp3"):
    """Wrap bytes in a file-like tuple for multipart upload."""
    return ("audio_file", (filename, io.BytesIO(content), content_type))


# ── App Client Fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a FastAPI TestClient with Firebase already mocked at conftest level."""
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── GeminiService-Level Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gemini_transcribe_audio_success():
    """GeminiService.transcribe_audio returns stripped text when Gemini responds correctly."""
    from services.gemini_service import GeminiService

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "  Hello, I am calling from CBI.  "
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True

    result = await svc.transcribe_audio(b"\x00" * 512, mime_type="audio/mpeg")

    assert result == "Hello, I am calling from CBI."
    mock_client.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_transcribe_audio_unavailable():
    """GeminiService.transcribe_audio raises RuntimeError when API key is not configured."""
    from services.gemini_service import GeminiService

    svc = GeminiService(api_key="")
    assert not svc.is_available

    with pytest.raises(RuntimeError, match="Gemini API is not available"):
        await svc.transcribe_audio(b"\x00" * 512)


@pytest.mark.asyncio
async def test_gemini_transcribe_audio_api_error_raises():
    """GeminiService.transcribe_audio raises RuntimeError when all retries fail."""
    from services.gemini_service import GeminiService

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API down"))

    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True

    with pytest.raises(RuntimeError, match="Audio transcription failed"):
        await svc.transcribe_audio(b"\x00" * 512)


@pytest.mark.asyncio
async def test_gemini_transcribe_audio_prompt_contains_hindi_instruction():
    """The transcription prompt must include multilingual (Hindi) handling instructions."""
    from services.gemini_service import GeminiService

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Test transcript"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    svc = GeminiService(api_key="mock-key")
    svc.client = mock_client
    svc._available = True

    await svc.transcribe_audio(b"\x00" * 512, mime_type="audio/wav")

    call_args = mock_client.aio.models.generate_content.call_args
    contents = call_args.kwargs.get("contents") or (call_args.args[0] if call_args.args else "")
    prompt_text = contents[0] if isinstance(contents, list) else str(contents)
    assert "Hindi" in prompt_text or "indian language" in prompt_text.lower()


# ── ScamDetector-Level Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scam_detector_analyze_audio_full_pipeline():
    """
    ScamDetector.analyze_audio must:
    1. Call transcribe_audio on GeminiService
    2. Feed the transcript through analyze_text
    3. Return result dict that includes 'transcript' key
    """
    from services.scam_detector import ScamDetector

    mock_gemini = MagicMock()
    mock_gemini.is_available = True
    mock_gemini.transcribe_audio = AsyncMock(
        return_value="Please send 50,000 rupees immediately to avoid arrest."
    )
    mock_gemini.analyze_scam_text = AsyncMock(return_value={
        "risk_score": 0.92,
        "risk_label": "HIGH",
        "classification": "digital_arrest_scam",
        "scam_type": "Digital Arrest",
        "explanation": "CBI impersonation detected.",
        "recommended_action": "Hang up immediately.",
        "extracted_entities": {"phone_numbers": [], "account_numbers": []},
    })

    with patch("services.scam_detector.get_gemini_service", return_value=mock_gemini):
        detector = ScamDetector(enable_zero_shot=False)
        result = await detector.analyze_audio(b"\x00" * 512, mime_type="audio/mpeg")

    assert "transcript" in result
    assert result["transcript"] == "Please send 50,000 rupees immediately to avoid arrest."
    assert result["risk_score"] > 0.0
    assert result["risk_label"] == "HIGH"


@pytest.mark.asyncio
async def test_scam_detector_analyze_audio_low_risk():
    """ScamDetector.analyze_audio correctly handles benign audio content."""
    from services.scam_detector import ScamDetector

    mock_gemini = MagicMock()
    mock_gemini.is_available = True
    mock_gemini.transcribe_audio = AsyncMock(return_value="Hi, how are you doing today?")
    mock_gemini.analyze_scam_text = AsyncMock(return_value={
        "risk_score": 0.05,
        "risk_label": "LOW",
        "classification": "legitimate_conversation",
        "scam_type": None,
        "explanation": "No scam patterns detected.",
        "recommended_action": "No action needed.",
        "extracted_entities": {"phone_numbers": [], "account_numbers": []},
    })

    with patch("services.scam_detector.get_gemini_service", return_value=mock_gemini):
        detector = ScamDetector(enable_zero_shot=False)
        result = await detector.analyze_audio(b"\x00" * 512, mime_type="audio/wav")

    assert result["risk_label"] == "LOW"
    assert result["risk_score"] < 0.4
    assert result["transcript"] == "Hi, how are you doing today?"


@pytest.mark.asyncio
async def test_scam_detector_analyze_audio_propagates_error():
    """ScamDetector.analyze_audio re-raises RuntimeError from GeminiService on failure."""
    from services.scam_detector import ScamDetector

    mock_gemini = MagicMock()
    mock_gemini.is_available = True
    mock_gemini.transcribe_audio = AsyncMock(
        side_effect=RuntimeError("Audio transcription failed: API error")
    )

    with patch("services.scam_detector.get_gemini_service", return_value=mock_gemini):
        detector = ScamDetector(enable_zero_shot=False)
        with pytest.raises(RuntimeError, match="Audio transcription failed"):
            await detector.analyze_audio(b"\x00" * 512)


# ── API Endpoint Tests (POST /api/scam/analyze-audio) ────────────────────────

@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_success(mock_get_detector, client):
    """Valid audio upload returns 200 with all expected fields."""
    mock_detector = MagicMock()
    mock_detector.analyze_audio = AsyncMock(return_value={
        "risk_score": 0.88,
        "risk_label": "HIGH",
        "classification": "digital_arrest_scam",
        "scam_type": "Digital Arrest",
        "explanation": "CBI impersonation with arrest threat detected.",
        "recommended_action": "Hang up and report.",
        "alert_id": "alert-abc-123",
        "transcript": "I am calling from CBI. You will be arrested.",
    })
    mock_get_detector.return_value = mock_detector

    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(_make_audio_bytes(1024), "audio/mpeg")],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_label"] == "HIGH"
    assert data["transcript"] == "I am calling from CBI. You will be arrested."
    assert "risk_score" in data
    assert "classification" in data


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_unsupported_format(mock_get_detector, client):
    """Unsupported MIME type (video/mp4) must return 422 without calling the detector."""
    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(_make_audio_bytes(512), "video/mp4", "test.mp4")],
    )

    assert response.status_code == 422
    assert "Unsupported audio format" in response.json().get("detail", "")
    mock_get_detector.return_value.analyze_audio.assert_not_called()


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_file_too_large(mock_get_detector, client):
    """File exceeding MAX_UPLOAD_SIZE_MB must return 413."""
    from config import settings
    oversized_bytes = _make_audio_bytes(settings.max_upload_bytes + 1)

    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(oversized_bytes, "audio/mpeg")],
    )

    assert response.status_code == 413
    assert "too large" in response.json().get("detail", "").lower()
    mock_get_detector.return_value.analyze_audio.assert_not_called()


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_empty_file(mock_get_detector, client):
    """Zero-byte file must return 422 Unprocessable Entity."""
    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(b"", "audio/mpeg")],
    )

    assert response.status_code == 422
    assert "empty" in response.json().get("detail", "").lower()
    mock_get_detector.return_value.analyze_audio.assert_not_called()


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_gemini_down_returns_503(mock_get_detector, client):
    """RuntimeError from the detector (Gemini down) must surface as 503."""
    mock_detector = MagicMock()
    mock_detector.analyze_audio = AsyncMock(
        side_effect=RuntimeError("Audio transcription failed: Gemini API is not available.")
    )
    mock_get_detector.return_value = mock_detector

    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(_make_audio_bytes(1024), "audio/mpeg")],
    )

    assert response.status_code == 503
    assert "transcription failed" in response.json().get("detail", "").lower()


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_wav_format_accepted(mock_get_detector, client):
    """audio/wav format must be accepted and return 200."""
    mock_detector = MagicMock()
    mock_detector.analyze_audio = AsyncMock(return_value={
        "risk_score": 0.1,
        "risk_label": "LOW",
        "classification": "legitimate_conversation",
        "scam_type": None,
        "explanation": "No scam detected.",
        "recommended_action": "No action needed.",
        "alert_id": None,
        "transcript": "Hello, this is a normal call.",
    })
    mock_get_detector.return_value = mock_detector

    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(_make_audio_bytes(512), "audio/wav", "test.wav")],
    )

    assert response.status_code == 200
    assert response.json()["risk_label"] == "LOW"


@patch("routers.scam.get_scam_detector")
def test_api_analyze_audio_response_schema(mock_get_detector, client):
    """Response must contain ALL fields defined in the ScamAudioResponse schema."""
    required_fields = {
        "risk_score", "risk_label", "classification",
        "scam_type", "explanation", "recommended_action",
        "alert_id", "transcript",
    }

    mock_detector = MagicMock()
    mock_detector.analyze_audio = AsyncMock(return_value={
        "risk_score": 0.55,
        "risk_label": "MEDIUM",
        "classification": "financial_fraud",
        "scam_type": "KYC Fraud",
        "explanation": "KYC fraud patterns found.",
        "recommended_action": "Do not share OTP.",
        "alert_id": None,
        "transcript": "Please provide your OTP to update your KYC.",
    })
    mock_get_detector.return_value = mock_detector

    response = client.post(
        "/api/scam/analyze-audio",
        files=[_make_upload_file(_make_audio_bytes(512), "audio/mpeg")],
    )

    assert response.status_code == 200
    data = response.json()
    for field in required_fields:
        assert field in data, f"Missing field in response: {field}"
