"""
Risk fusion service for ShieldAI.

Combines Gemini AI results and zero-shot classifier results into
an explainable, rule-based final risk assessment.
Replaces the hard-coded 0.7/0.3 weighted average with transparent logic.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from logging_config import get_logger

logger = get_logger("shield_ai.risk_fusion")


@dataclass
class FusedRiskResult:
    """Explainable fused risk output."""
    risk_score: float = 0.0
    risk_label: str = "LOW"   # HIGH, MEDIUM, LOW, REVIEW
    explanation: str = ""
    fusion_method: str = ""   # e.g., "gemini_only", "both_agree", "gemini_primary"
    gemini: Optional[Dict[str, Any]] = None
    zero_shot: Optional[Dict[str, Any]] = None


class RiskFusionService:
    """
    Combines Gemini and zero-shot classifier outputs using rule-based logic.

    Rules (in priority order):
    1. If Gemini is high-confidence fraud (>=0.8) → trust Gemini
    2. If Gemini is unavailable → use zero-shot alone
    3. If both models agree on HIGH → HIGH
    4. If strong disagreement (>0.4 gap) → MEDIUM / REVIEW
    5. Otherwise → weighted blend (Gemini 0.7, zero-shot 0.3)
    """

    HIGH_THRESHOLD = 0.7
    MEDIUM_THRESHOLD = 0.4
    GEMINI_HIGH_CONFIDENCE = 0.8
    DISAGREEMENT_GAP = 0.4

    def fuse(
        self,
        gemini_result: Optional[dict],
        zero_shot_result: Optional[dict],
    ) -> FusedRiskResult:
        """
        Fuse scores from Gemini and zero-shot into a final risk assessment.

        Args:
            gemini_result: Output from GeminiService.analyze_scam_text()
                           Expected keys: risk_score, risk_label, classification, explanation, ...
            zero_shot_result: Output from ZeroShotScamClassifier.classify()
                              Expected keys: top_label, top_score, all_scores, latency_ms
                              May be None if classifier is disabled/unavailable.

        Returns:
            FusedRiskResult with explainable score, label, and method.
        """
        gemini_score = self._extract_gemini_score(gemini_result)
        zs_score = self._extract_zero_shot_risk_score(zero_shot_result)

        has_gemini = gemini_result is not None and gemini_score is not None
        has_zero_shot = zero_shot_result is not None and zs_score is not None

        # ── Rule 1: No models available ──────────────────────
        if not has_gemini and not has_zero_shot:
            return FusedRiskResult(
                risk_score=0.0,
                risk_label="LOW",
                explanation="No AI models available for analysis.",
                fusion_method="no_models",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # ── Rule 2: Gemini only (zero-shot unavailable) ──────
        if has_gemini and not has_zero_shot:
            score = gemini_score
            label = self._score_to_label(score)
            gemini_class = (gemini_result or {}).get("classification", "unknown")
            return FusedRiskResult(
                risk_score=round(score, 3),
                risk_label=label,
                explanation=f"Gemini classified as {gemini_class} ({score:.2f} confidence). Zero-shot classifier not available.",
                fusion_method="gemini_only",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # ── Rule 3: Zero-shot only (Gemini unavailable) ──────
        if not has_gemini and has_zero_shot:
            score = zs_score
            label = self._score_to_label(score)
            zs_label = (zero_shot_result or {}).get("top_label", "unknown")
            return FusedRiskResult(
                risk_score=round(score, 3),
                risk_label=label,
                explanation=f"Gemini unavailable. Zero-shot classified as '{zs_label}' (risk score {score:.2f}).",
                fusion_method="zero_shot_only",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # ── Both models available ────────────────────────────
        assert gemini_score is not None and zs_score is not None

        gemini_class = (gemini_result or {}).get("classification", "unknown")
        zs_label = (zero_shot_result or {}).get("top_label", "unknown")
        gap = abs(gemini_score - zs_score)

        # Rule 4: Gemini high-confidence fraud → trust Gemini
        if gemini_score >= self.GEMINI_HIGH_CONFIDENCE:
            score = gemini_score
            label = self._score_to_label(score)
            return FusedRiskResult(
                risk_score=round(score, 3),
                risk_label=label,
                explanation=(
                    f"Gemini high-confidence: {gemini_class} ({gemini_score:.2f}). "
                    f"Zero-shot: '{zs_label}' ({zs_score:.2f}). Trusting Gemini."
                ),
                fusion_method="gemini_high_confidence",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # Rule 5: Both agree high → HIGH
        if gemini_score >= self.HIGH_THRESHOLD and zs_score >= self.HIGH_THRESHOLD:
            score = max(gemini_score, zs_score)
            return FusedRiskResult(
                risk_score=round(score, 3),
                risk_label="HIGH",
                explanation=(
                    f"Both models agree: Gemini ({gemini_class}, {gemini_score:.2f}) "
                    f"and zero-shot ('{zs_label}', {zs_score:.2f}) both indicate HIGH risk."
                ),
                fusion_method="both_agree_high",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # Rule 6: Strong disagreement → label as MEDIUM / REVIEW
        if gap >= self.DISAGREEMENT_GAP:
            score = round((gemini_score * 0.7) + (zs_score * 0.3), 3)
            label = self._score_to_label(score)
            return FusedRiskResult(
                risk_score=score,
                risk_label=label,
                explanation=(
                    f"Models disagree significantly (gap {gap:.2f}): "
                    f"Gemini ({gemini_class}, {gemini_score:.2f}) vs "
                    f"zero-shot ('{zs_label}', {zs_score:.2f}). Final label follows the blended risk score."
                ),
                fusion_method="disagreement_review",
                gemini=gemini_result,
                zero_shot=zero_shot_result,
            )

        # Rule 7: Default weighted blend
        score = round((gemini_score * 0.7) + (zs_score * 0.3), 3)
        score = min(1.0, max(0.0, score))
        label = self._score_to_label(score)

        return FusedRiskResult(
            risk_score=score,
            risk_label=label,
            explanation=(
                f"Weighted fusion: Gemini ({gemini_class}, {gemini_score:.2f}) × 0.7 + "
                f"zero-shot ('{zs_label}', {zs_score:.2f}) × 0.3 = {score:.3f}."
            ),
            fusion_method="weighted_blend",
            gemini=gemini_result,
            zero_shot=zero_shot_result,
        )

    def _score_to_label(self, score: float) -> str:
        """Convert a 0-1 risk score to a label."""
        if score >= self.HIGH_THRESHOLD:
            return "HIGH"
        elif score >= self.MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _extract_gemini_score(result: Optional[dict]) -> Optional[float]:
        """Extract risk_score from Gemini result, tolerating missing data."""
        if result is None:
            return None
        score = result.get("risk_score")
        if score is None:
            # Try confidence as fallback
            score = result.get("confidence")
        if score is not None:
            return max(0.0, min(1.0, float(score)))
        return None

    @staticmethod
    def _extract_zero_shot_risk_score(result: Optional[dict]) -> Optional[float]:
        """
        Convert zero-shot result into a 0-1 risk score.
        High 'legitimate' score → low risk. Everything else → higher risk.
        """
        if result is None:
            return None
        all_scores = result.get("all_scores", {})
        if not all_scores:
            return None

        # Sum of legitimate labels
        legit_score = 0.0
        for label_key in ("legitimate customer support message", "normal personal conversation", "legitimate conversation"):
            legit_score += all_scores.get(label_key, 0.0)

        # Clamp legit_score to [0, 1]
        legit_score = min(1.0, legit_score)

        # Risk = inverse of legitimacy
        return round(1.0 - legit_score, 4)


# ── Module-level singleton ──────────────────────────────────
_fusion_service: Optional[RiskFusionService] = None


def get_risk_fusion_service() -> RiskFusionService:
    """Get the RiskFusionService singleton."""
    global _fusion_service
    if _fusion_service is None:
        _fusion_service = RiskFusionService()
    return _fusion_service
