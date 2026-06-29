"""
Tests for the RiskFusionService.

Covers:
- Gemini high-confidence
- Both agree HIGH
- Disagreement handling
- Fallbacks (zero-shot only, gemini only)
"""

from services.risk_fusion_service import RiskFusionService


def test_fusion_gemini_only():
    fusion = RiskFusionService()
    gemini = {"risk_score": 0.85, "risk_label": "HIGH", "classification": "digital_arrest"}

    result = fusion.fuse(gemini_result=gemini, zero_shot_result=None)
    assert result.fusion_method == "gemini_only"
    assert result.risk_score == 0.85
    assert result.risk_label == "HIGH"


def test_fusion_zero_shot_only():
    fusion = RiskFusionService()
    zs = {
        "top_label": "investment fraud",
        "top_score": 0.9,
        "all_scores": {"investment fraud": 0.9, "legitimate conversation": 0.05},
        "latency_ms": 100,
    }

    result = fusion.fuse(gemini_result=None, zero_shot_result=zs)
    assert result.fusion_method == "zero_shot_only"
    # Inverse of legit score 0.05 -> risk 0.95
    assert result.risk_score == 0.95
    assert result.risk_label == "HIGH"


def test_fusion_both_agree_high():
    fusion = RiskFusionService()
    gemini = {"risk_score": 0.75, "risk_label": "HIGH"}
    zs = {
        "top_label": "fraud",
        "all_scores": {"legitimate conversation": 0.1},
    }

    result = fusion.fuse(gemini_result=gemini, zero_shot_result=zs)
    assert result.fusion_method == "both_agree_high"
    # Max of Gemini (0.75) and ZS (0.90)
    assert result.risk_score == 0.90
    assert result.risk_label == "HIGH"


def test_fusion_gemini_high_confidence():
    fusion = RiskFusionService()
    gemini = {"risk_score": 0.95, "risk_label": "HIGH"}
    zs = {
        "top_label": "legit",
        "all_scores": {"legitimate conversation": 0.7},  # ZS risk: 0.3
    }

    result = fusion.fuse(gemini_result=gemini, zero_shot_result=zs)
    assert result.fusion_method == "gemini_high_confidence"
    assert result.risk_score == 0.95
    assert result.risk_label == "HIGH"


def test_fusion_disagreement():
    fusion = RiskFusionService()
    gemini = {"risk_score": 0.20, "risk_label": "LOW"}
    zs = {
        "top_label": "fraud",
        "all_scores": {"legitimate conversation": 0.1},  # ZS risk: 0.9
    }

    result = fusion.fuse(gemini_result=gemini, zero_shot_result=zs)
    assert result.fusion_method == "disagreement_review"
    assert result.risk_label == "MEDIUM"


def test_fusion_no_models_available():
    fusion = RiskFusionService()
    result = fusion.fuse(gemini_result=None, zero_shot_result=None)
    assert result.fusion_method == "no_models"
    assert result.risk_score == 0.0
    assert result.risk_label == "LOW"
