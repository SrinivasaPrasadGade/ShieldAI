"""
Image quality assessment service for ShieldAI.

Pre-screens currency images before sending to Gemini Vision.
Rejects or warns about images that are too blurry, too dark,
too small, or otherwise unsuitable for AI analysis.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from logging_config import get_logger

logger = get_logger("shield_ai.image_quality")

# Try to import OpenCV and NumPy
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("opencv_not_available", message="Image quality checks disabled. pip install opencv-python-headless numpy")


# ── Thresholds ───────────────────────────────────────────────
MIN_BLUR_SCORE = 50.0        # Laplacian variance below this = too blurry
MIN_RESOLUTION = (200, 100)  # Minimum width x height in pixels
MIN_BRIGHTNESS = 30          # Mean brightness below this = too dark
MAX_BRIGHTNESS = 245         # Mean brightness above this = overexposed
MIN_ASPECT_RATIO = 0.3       # width/height below this = suspicious shape
MAX_ASPECT_RATIO = 5.0       # width/height above this = suspicious shape


@dataclass
class ImageQualityReport:
    """Structured quality assessment of an image."""
    is_usable: bool = True
    blur_score: float = 0.0
    brightness: str = "ok"        # "ok", "too_dark", "overexposed"
    brightness_mean: float = 0.0
    resolution: Tuple[int, int] = (0, 0)  # (width, height)
    aspect_ratio: float = 0.0
    warnings: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None


class ImageQualityService:
    """
    Assesses image quality using OpenCV.

    Checks:
    - Blur detection (Laplacian variance)
    - Brightness histogram (mean of grayscale)
    - Glare / overexposure detection
    - Minimum pixel size
    - Aspect ratio sanity check
    """

    def assess(self, image_bytes: bytes) -> ImageQualityReport:
        """
        Assess image quality from raw bytes.

        Args:
            image_bytes: Raw image file bytes.

        Returns:
            ImageQualityReport with is_usable flag and diagnostics.
        """
        report = ImageQualityReport()

        if not OPENCV_AVAILABLE:
            # Can't check quality without OpenCV — assume usable
            report.warnings.append("opencv_not_available: quality checks skipped")
            logger.debug("image_quality_skipped", reason="opencv not available")
            return report

        if not image_bytes or len(image_bytes) < 100:
            report.is_usable = False
            report.rejection_reason = "Image data too small or empty"
            return report

        try:
            img_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                report.is_usable = False
                report.rejection_reason = "Could not decode image (corrupt or unsupported format)"
                return report

            height, width = img.shape[:2]
            report.resolution = (width, height)

            # ── Resolution check ─────────────────────────────
            if width < MIN_RESOLUTION[0] or height < MIN_RESOLUTION[1]:
                report.warnings.append(
                    f"Resolution too low: {width}x{height} (minimum {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]})"
                )
                report.is_usable = False
                report.rejection_reason = f"Image too small ({width}x{height}px)"

            # ── Aspect ratio check ───────────────────────────
            report.aspect_ratio = round(width / height, 2) if height > 0 else 0.0
            if report.aspect_ratio < MIN_ASPECT_RATIO or report.aspect_ratio > MAX_ASPECT_RATIO:
                report.warnings.append(
                    f"Unusual aspect ratio: {report.aspect_ratio} (expected {MIN_ASPECT_RATIO}–{MAX_ASPECT_RATIO})"
                )

            # ── Blur detection (Laplacian variance) ──────────
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            report.blur_score = round(laplacian_var, 2)

            if laplacian_var < MIN_BLUR_SCORE:
                report.warnings.append(
                    f"Image is blurry (blur score {laplacian_var:.1f}, minimum {MIN_BLUR_SCORE})"
                )
                if not report.rejection_reason:
                    report.is_usable = False
                    report.rejection_reason = f"Image too blurry (score {laplacian_var:.1f})"

            # ── Brightness check ─────────────────────────────
            mean_brightness = float(gray.mean())
            report.brightness_mean = round(mean_brightness, 1)

            if mean_brightness < MIN_BRIGHTNESS:
                report.brightness = "too_dark"
                report.warnings.append(f"Image too dark (brightness {mean_brightness:.0f})")
                if not report.rejection_reason:
                    report.is_usable = False
                    report.rejection_reason = "Image too dark for reliable analysis"
            elif mean_brightness > MAX_BRIGHTNESS:
                report.brightness = "overexposed"
                report.warnings.append(f"Image overexposed (brightness {mean_brightness:.0f})")
                if not report.rejection_reason:
                    report.warnings.append("Overexposed image may reduce analysis accuracy")
            else:
                report.brightness = "ok"

            # ── Glare detection (high-brightness pixel ratio) ─
            white_pixel_ratio = float(np.sum(gray > 250)) / gray.size
            if white_pixel_ratio > 0.15:
                report.warnings.append(
                    f"Possible glare detected ({white_pixel_ratio:.0%} of pixels near-white)"
                )

            logger.debug(
                "image_quality_assessed",
                resolution=f"{width}x{height}",
                blur_score=report.blur_score,
                brightness=report.brightness_mean,
                is_usable=report.is_usable,
                warnings_count=len(report.warnings),
            )

            return report

        except Exception as e:
            logger.error("image_quality_assessment_failed", error=str(e))
            report.warnings.append(f"Quality assessment error: {str(e)}")
            # On error, default to usable (let Gemini try)
            return report


# ── Module-level singleton ──────────────────────────────────
_quality_service: Optional[ImageQualityService] = None


def get_image_quality_service() -> ImageQualityService:
    """Get the ImageQualityService singleton."""
    global _quality_service
    if _quality_service is None:
        _quality_service = ImageQualityService()
    return _quality_service
