import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from config import settings

client = TestClient(app)

@pytest.fixture
def mock_twilio_auth_token(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "real_secret_token")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123456")

@pytest.fixture
def mock_twilio_auth_token_placeholder(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "your-twilio-auth-token")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123456")

@patch("twilio.request_validator.RequestValidator.validate")
def test_whatsapp_webhook_valid_signature(mock_validate, mock_twilio_auth_token):
    mock_validate.return_value = True
    
    response = client.post(
        "/webhook/whatsapp",
        headers={"x-twilio-signature": "valid-sig"},
        data={"From": "whatsapp:+1234567890", "Body": "help", "NumMedia": "0"}
    )
    
    assert response.status_code == 200
    assert "ShieldAI Commands" in response.text
    mock_validate.assert_called_once()

@patch("twilio.request_validator.RequestValidator.validate")
def test_whatsapp_webhook_invalid_signature(mock_validate, mock_twilio_auth_token, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    mock_validate.return_value = False
    
    response = client.post(
        "/webhook/whatsapp",
        headers={"x-twilio-signature": "invalid-sig"},
        data={"From": "whatsapp:+1234567890", "Body": "help", "NumMedia": "0"}
    )
    
    assert response.status_code == 403
    assert "Invalid Twilio signature" in response.json()["detail"]

@patch("twilio.request_validator.RequestValidator.validate")
def test_whatsapp_webhook_invalid_signature_debug_mode(mock_validate, mock_twilio_auth_token, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    mock_validate.return_value = False
    
    response = client.post(
        "/webhook/whatsapp",
        headers={"x-twilio-signature": "invalid-sig"},
        data={"From": "whatsapp:+1234567890", "Body": "help", "NumMedia": "0"}
    )
    
    # In DEBUG mode, invalid signature only logs a warning but proceeds
    assert response.status_code == 200
    assert "ShieldAI Commands" in response.text

@patch("twilio.request_validator.RequestValidator.validate")
def test_whatsapp_webhook_placeholder_token(mock_validate, mock_twilio_auth_token_placeholder):
    mock_validate.return_value = False
    
    response = client.post(
        "/webhook/whatsapp",
        headers={"x-twilio-signature": "invalid-sig"},
        data={"From": "whatsapp:+1234567890", "Body": "help", "NumMedia": "0"}
    )
    
    # Placeholder token logs a warning but proceeds
    assert response.status_code == 200
    assert "ShieldAI Commands" in response.text
