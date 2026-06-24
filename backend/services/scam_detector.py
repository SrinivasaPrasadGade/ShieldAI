"""
Multi-model scam detection service for ShieldAI.

Orchestrates Gemini API + BERT zero-shot classification for
comprehensive scam text analysis. Handles audio transcription
via Gemini's native audio capabilities.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from logging_config import get_logger
from services.gemini_service import get_gemini_service

logger = get_logger("shield_ai.scam_detector")

# Try to import transformers for BERT zero-shot classification
try:
    from transformers import pipeline as hf_pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers_not_available", message="BERT scoring disabled. pip install transformers torch")


# Scam classification candidate labels for zero-shot
SCAM_LABELS = [
    "digital arrest scam",
    "financial fraud",
    "KYC fraud",
    "customs scam",
    "impersonation scam",
    "lottery or prize scam",
    "investment fraud",
    "legitimate conversation",
]


class ScamDetector:
    """
    Orchestrates multi-model scam analysis using Gemini + BERT.
    Merges scores from both models for a composite risk assessment.
    """

    def __init__(self, enable_bert: bool = True, bert_model: str = "facebook/bart-large-mnli"):
        self.gemini = get_gemini_service()
        self._bert_pipeline = None
        self._bert_enabled = enable_bert and TRANSFORMERS_AVAILABLE
        self._bert_model_name = bert_model

        if self._bert_enabled:
            self._init_bert()

    def _init_bert(self):
        """Lazy-load the BERT zero-shot classification pipeline."""
        try:
            logger.info("bert_loading", model=self._bert_model_name)
            self._bert_pipeline = hf_pipeline(
                "zero-shot-classification",
                model=self._bert_model_name,
                device=-1,  # CPU; use 0 for GPU
            )
            logger.info("bert_loaded", model=self._bert_model_name)
        except Exception as e:
            logger.error("bert_load_failed", error=str(e))
            self._bert_pipeline = None
            self._bert_enabled = False

    def bert_classify(self, text: str) -> Optional[dict]:
        """
        Run BERT zero-shot classification on text.

        Returns:
            dict with label scores, or None if BERT is unavailable.
        """
        if not self._bert_pipeline:
            return None

        try:
            result = self._bert_pipeline(
                text[:512],  # BERT max token limit consideration
                candidate_labels=SCAM_LABELS,
                multi_label=False,
            )
            # Build label → score mapping
            scores = dict(zip(result["labels"], result["scores"]))
            # Get the top label
            top_label = result["labels"][0]
            top_score = result["scores"][0]

            logger.debug("bert_classification", top_label=top_label, top_score=round(top_score, 3))

            return {
                "top_label": top_label,
                "top_score": top_score,
                "all_scores": {k: round(v, 4) for k, v in scores.items()},
            }
        except Exception as e:
            logger.error("bert_classify_failed", error=str(e))
            return None

    async def analyze_text(
        self,
        text: str,
        source_phone: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Full scam analysis pipeline: Gemini + BERT → fused score.

        Args:
            text: Text to analyze
            source_phone: Optional phone number
            language: Language code

        Returns:
            dict matching ScamAnalyzeResponse schema
        """
        # 1. Gemini analysis (primary signal)
        gemini_result = await self.gemini.analyze_scam_text(text, language)
        gemini_score = gemini_result.get("risk_score", 0.0)

        # 2. BERT zero-shot classification (secondary signal)
        bert_result = self.bert_classify(text)
        bert_score = 0.0

        if bert_result:
            # Convert BERT top score to risk score
            # "legitimate conversation" is the non-scam label
            legit_score = bert_result["all_scores"].get("legitimate conversation", 0.0)
            bert_score = 1.0 - legit_score  # Invert: high legit = low risk

        # 3. Score fusion: weighted average (Gemini 0.7, BERT 0.3)
        if bert_result:
            fused_score = (gemini_score * 0.7) + (bert_score * 0.3)
        else:
            fused_score = gemini_score

        fused_score = round(min(1.0, max(0.0, fused_score)), 3)

        # 4. Derive risk label from fused score
        if fused_score >= 0.7:
            risk_label = "HIGH"
        elif fused_score >= 0.4:
            risk_label = "MEDIUM"
        else:
            risk_label = "LOW"

        # 5. Generate alert if HIGH risk
        alert_id = None
        if risk_label == "HIGH":
            try:
                from services.alert_service import get_alert_service
                alert_svc = get_alert_service()
                alert_id = await alert_svc.create_alert(
                    alert_type="scam_detected",
                    severity="HIGH",
                    title=f"High-risk scam detected: {gemini_result.get('classification', 'unknown')}",
                    description=f"Text analysis risk score: {fused_score}. {gemini_result.get('explanation', '')}",
                    linked_phone=source_phone,
                )
            except Exception as e:
                logger.error("alert_creation_failed", error=str(e))

        result = {
            "risk_score": fused_score,
            "risk_label": risk_label,
            "classification": gemini_result.get("classification", "unknown"),
            "scam_type": gemini_result.get("scam_type"),
            "explanation": gemini_result.get("explanation", "Analysis complete."),
            "recommended_action": gemini_result.get("recommended_action", "Stay vigilant."),
            "alert_id": alert_id,
        }

        logger.info(
            "scam_analysis_complete",
            risk_score=fused_score,
            risk_label=risk_label,
            classification=result["classification"],
            gemini_available=self.gemini.is_available,
            bert_available=self._bert_enabled,
        )

        return result

    async def analyze_audio(self, audio_bytes: bytes, mime_type: str = "audio/mpeg") -> dict:
        """
        Transcribe audio and run scam analysis on the transcript.

        Args:
            audio_bytes: Raw audio file bytes
            mime_type: Audio MIME type

        Returns:
            dict matching ScamAudioResponse schema (includes transcript)
        """
        # 1. Transcribe audio via Gemini
        transcript = await self.gemini.transcribe_audio(audio_bytes, mime_type)

        # 2. Analyze the transcript
        analysis = await self.analyze_text(transcript)

        # 3. Merge transcript into result
        result = {**analysis, "transcript": transcript}

        logger.info(
            "audio_scam_analysis_complete",
            transcript_length=len(transcript),
            risk_score=result["risk_score"],
        )

        return result

    async def get_alerts(self, limit: int = 20, severity: Optional[str] = None) -> dict:
        """
        Retrieve scam alerts from Firestore.

        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity filter (HIGH, MEDIUM, CRITICAL)

        Returns:
            dict with alerts list and total count
        """
        try:
            from services.alert_service import get_alert_service
            alert_svc = get_alert_service()
            return await alert_svc.get_alerts(limit=limit, severity=severity)
        except Exception as e:
            logger.error("get_alerts_failed", error=str(e))
            return {"alerts": [], "total": 0}

    async def get_stats(self, days: int = 7) -> dict:
        """
        Get scam analysis statistics for the given time period.

        Args:
            days: Number of days to look back

        Returns:
            dict matching ScamStatsResponse schema
        """
        try:
            from models.database import get_firestore_client
            db = get_firestore_client()

            # Query fraud reports from Firestore
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            reports_ref = db.collection("fraud_reports")
            query = reports_ref.where("created_at", ">=", cutoff).stream()

            total = 0
            high_risk = 0
            medium_risk = 0
            scam_types: dict = {}
            daily_counts: dict = {}

            for doc in query:
                data = doc.to_dict()
                total += 1

                label = data.get("risk_label", "LOW")
                if label == "HIGH":
                    high_risk += 1
                elif label == "MEDIUM":
                    medium_risk += 1

                stype = data.get("gemini_classification", "unknown")
                scam_types[stype] = scam_types.get(stype, 0) + 1

                date_key = str(data.get("created_at", ""))[:10]
                if date_key:
                    daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

            trend = [{"date": k, "count": v} for k, v in sorted(daily_counts.items())]

            return {
                "total_analyzed": total,
                "high_risk": high_risk,
                "medium_risk": medium_risk,
                "top_scam_types": scam_types,
                "trend": trend,
            }

        except Exception as e:
            logger.error("get_scam_stats_failed", error=str(e))
            return {
                "total_analyzed": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "top_scam_types": {},
                "trend": [],
            }


# Module-level singleton
_scam_detector: Optional[ScamDetector] = None


def get_scam_detector() -> ScamDetector:
    """Get the initialized ScamDetector singleton."""
    global _scam_detector
    if _scam_detector is None:
        from config import settings
        _scam_detector = ScamDetector(
            enable_bert=settings.ENABLE_BERT,
            bert_model=settings.BERT_MODEL,
        )
    return _scam_detector


def init_scam_detector(enable_bert: bool = True, bert_model: str = "facebook/bart-large-mnli") -> ScamDetector:
    """Initialize the ScamDetector singleton."""
    global _scam_detector
    _scam_detector = ScamDetector(enable_bert=enable_bert, bert_model=bert_model)
    return _scam_detector
