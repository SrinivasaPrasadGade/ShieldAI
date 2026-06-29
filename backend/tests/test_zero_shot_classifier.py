"""
Tests for the ZeroShotScamClassifier service.

Covers:
- Classifier disabled → app works
- Classifier unavailable → clean fallback
- Mocked response → used correctly by ScamDetector
"""

import pytest
from unittest.mock import patch, MagicMock


class TestZeroShotClassifierDisabled:
    """Tests when zero-shot is disabled or unavailable."""

    def test_classifier_not_loaded_returns_none(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier
        clf = ZeroShotScamClassifier(model_name="facebook/bart-large-mnli")
        # Not loaded — classify should return None
        result = clf.classify("test text")
        assert result is None

    def test_classifier_is_not_available_when_not_loaded(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier
        clf = ZeroShotScamClassifier()
        assert clf.is_available is False

    def test_classifier_load_fails_gracefully(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier
        with patch("services.zero_shot_classifier.ZeroShotScamClassifier.load") as mock_load:
            mock_load.return_value = False
            clf = ZeroShotScamClassifier()
            clf.load()
            assert clf.is_available is False

    def test_scam_detector_works_without_zero_shot(self):
        """ScamDetector should work even when zero-shot is disabled."""
        from services.scam_detector import ScamDetector
        with patch("services.scam_detector.get_gemini_service") as mock_gemini:
            mock_svc = MagicMock()
            mock_svc.is_available = False
            mock_svc._fallback_scam_analysis.return_value = {
                "risk_score": 0.8,
                "risk_label": "HIGH",
                "classification": "digital_arrest_scam",
                "scam_type": "Digital Arrest Scam",
                "explanation": "Test",
                "recommended_action": "Test",
            }
            mock_svc.analyze_scam_text = mock_svc._fallback_scam_analysis
            mock_gemini.return_value = mock_svc

            detector = ScamDetector(enable_zero_shot=False)
            assert detector._zero_shot_enabled is False


class TestZeroShotClassifierMocked:
    """Tests with a mocked classifier pipeline."""

    def test_classify_returns_structured_result(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier

        clf = ZeroShotScamClassifier()
        clf._loaded = True

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = {
            "labels": ["digital arrest scam", "normal personal conversation"],
            "scores": [0.92, 0.08],
        }
        clf._pipeline = mock_pipeline

        result = clf.classify("CBI officer called threatening arrest")
        assert result is not None
        assert result.provider == "huggingface"
        assert result.top_label == "digital arrest scam"
        assert result.top_score == pytest.approx(0.92)
        assert "digital arrest scam" in result.all_scores

    def test_classify_handles_exception(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier

        clf = ZeroShotScamClassifier()
        clf._loaded = True
        clf._pipeline = MagicMock(side_effect=RuntimeError("Model OOM"))

        result = clf.classify("some text")
        assert result is None

    def test_truncate_text_fallback_without_tokenizer(self):
        from services.zero_shot_classifier import ZeroShotScamClassifier

        clf = ZeroShotScamClassifier()
        clf._tokenizer = None
        long_text = "a" * 2000
        truncated = clf._truncate_text(long_text)
        assert len(truncated) == 1024  # Fallback truncation
