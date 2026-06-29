"""
Dedicated Hugging Face zero-shot scam classifier for ShieldAI.

Uses facebook/bart-large-mnli for zero-shot text classification.
This service is isolated, testable, timed, and traceable.
It is optional — the app works fine without it (Gemini is the primary engine).
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from logging_config import get_logger

logger = get_logger("shield_ai.zero_shot")


# ── Scam-specific candidate labels ──────────────────────────
SCAM_LABELS: List[str] = [
    "digital arrest scam",
    "KYC OTP fraud",
    "fake investment scam",
    "customs parcel scam",
    "TRAI SIM block scam",
    "loan app harassment",
    "legitimate customer support message",
    "normal personal conversation",
]


@dataclass
class ZeroShotResult:
    """Structured result from zero-shot classification."""
    provider: str = "huggingface"
    model: str = ""
    top_label: str = ""
    top_score: float = 0.0
    all_scores: Dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0


class ZeroShotScamClassifier:
    """
    Hugging Face zero-shot scam classifier using BART-MNLI.

    Features:
    - Token-aware truncation via tokenizer (not naive text[:512])
    - Thread-based timeout for inference
    - Structured result with latency tracking
    - Proper logging of model events
    """

    def __init__(
        self,
        model_name: str = "facebook/bart-large-mnli",
        timeout_seconds: int = 30,
        labels: Optional[List[str]] = None,
    ):
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._labels = labels or SCAM_LABELS
        self._pipeline = None
        self._tokenizer = None
        self._loaded = False
        self._load_error: Optional[str] = None

    def load(self) -> bool:
        """
        Load the zero-shot classification pipeline.

        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            from transformers import pipeline as hf_pipeline, AutoTokenizer

            logger.info("zero_shot_loading", model=self._model_name)
            start = time.monotonic()

            self._pipeline = hf_pipeline(
                "zero-shot-classification",
                model=self._model_name,
                device=-1,  # CPU; use 0 for GPU
            )

            # Keep a reference to the tokenizer for token-aware truncation
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)

            elapsed_ms = round((time.monotonic() - start) * 1000)
            self._loaded = True
            self._load_error = None
            logger.info("zero_shot_loaded", model=self._model_name, load_time_ms=elapsed_ms)
            return True

        except ImportError as e:
            self._load_error = f"transformers not installed: {e}"
            logger.error("zero_shot_load_failed", error=self._load_error)
            return False

        except Exception as e:
            self._load_error = str(e)
            logger.error("zero_shot_load_failed", error=self._load_error)
            return False

    @property
    def is_available(self) -> bool:
        """Check if the classifier is loaded and ready."""
        return self._loaded and self._pipeline is not None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def _truncate_text(self, text: str, max_tokens: int = 512) -> str:
        """Token-aware truncation using the model's tokenizer."""
        if self._tokenizer is None:
            # Fallback: naive truncation
            return text[:1024]

        try:
            tokens = self._tokenizer.encode(
                text,
                truncation=True,
                max_length=max_tokens,
                add_special_tokens=False,
            )
            return self._tokenizer.decode(tokens, skip_special_tokens=True)
        except Exception:
            return text[:1024]

    def classify(self, text: str, language: str = "en") -> Optional[ZeroShotResult]:
        """
        Run zero-shot classification on text.

        Args:
            text: The text to classify.
            language: Language code (logged for observability, not used in classification).

        Returns:
            ZeroShotResult if successful, None on failure or timeout.
        """
        if not self.is_available:
            return None

        start = time.monotonic()
        result_holder: List[Optional[ZeroShotResult]] = [None]
        error_holder: List[Optional[str]] = [None]

        truncated_text = self._truncate_text(text)

        def _run_inference():
            try:
                raw = self._pipeline(
                    truncated_text,
                    candidate_labels=self._labels,
                    multi_label=False,
                )
                scores = dict(zip(raw["labels"], raw["scores"]))
                top_label = raw["labels"][0]
                top_score = raw["scores"][0]
                elapsed_ms = round((time.monotonic() - start) * 1000, 1)

                result_holder[0] = ZeroShotResult(
                    provider="huggingface",
                    model=self._model_name,
                    top_label=top_label,
                    top_score=top_score,
                    all_scores={k: round(v, 4) for k, v in scores.items()},
                    latency_ms=elapsed_ms,
                )
            except Exception as e:
                error_holder[0] = str(e)

        # Run inference in a thread with timeout
        thread = threading.Thread(target=_run_inference, daemon=True)
        thread.start()
        thread.join(timeout=self._timeout_seconds)

        if thread.is_alive():
            elapsed_ms = round((time.monotonic() - start) * 1000, 1)
            logger.error(
                "zero_shot_timeout",
                model=self._model_name,
                timeout_seconds=self._timeout_seconds,
                latency_ms=elapsed_ms,
                language=language,
            )
            return None

        if error_holder[0]:
            logger.error("zero_shot_classify_failed", error=error_holder[0], language=language)
            return None

        result = result_holder[0]
        if result:
            logger.debug(
                "zero_shot_classification",
                top_label=result.top_label,
                top_score=round(result.top_score, 3),
                latency_ms=result.latency_ms,
                language=language,
            )
        return result


# ── Module-level singleton ──────────────────────────────────
_classifier: Optional[ZeroShotScamClassifier] = None


def get_zero_shot_classifier() -> Optional[ZeroShotScamClassifier]:
    """Get the initialized ZeroShotScamClassifier singleton (may be None if disabled)."""
    return _classifier


def init_zero_shot_classifier(
    model_name: str = "facebook/bart-large-mnli",
    timeout_seconds: int = 30,
) -> ZeroShotScamClassifier:
    """Initialize and load the ZeroShotScamClassifier singleton."""
    global _classifier
    _classifier = ZeroShotScamClassifier(
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )
    _classifier.load()
    return _classifier
