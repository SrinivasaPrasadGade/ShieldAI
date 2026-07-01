"""
Currency analysis service for ShieldAI.

Handles image preprocessing (OpenCV), async verification via Gemini Vision,
result polling, FICN mapping, statistics, and Firestore persistence of
completed checks (so /stats and /ficn-map reflect real uploads).
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from logging_config import get_logger
from config import settings
from models import task_store
from services.gemini_service import get_gemini_service
from services.storage_service import get_storage_service

logger = get_logger("shield_ai.currency")

# Try to import OpenCV
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("opencv_not_available", message="Image preprocessing disabled. pip install opencv-python-headless numpy")


# ── Location helper ─────────────────────────────────────────────────────────

# Known city coordinates (lat, lng) for quick string → geo lookup
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "mumbai":    (19.0760,  72.8777),
    "delhi":     (28.7041,  77.1025),
    "bengaluru": (12.9716,  77.5946),
    "bangalore": (12.9716,  77.5946),
    "kolkata":   (22.5726,  88.3639),
    "hyderabad": (17.3850,  78.4867),
    "chennai":   (13.0827,  80.2707),
    "pune":      (18.5204,  73.8567),
    "ahmedabad": (23.0225,  72.5714),
    "amritsar":  (31.6340,  74.8723),
    "malda":     (25.0108,  88.1440),
}


def _parse_location(location: Optional[str]) -> dict:
    """
    Convert the optional ``location`` string into a Firestore-compatible
    ``{lat, lng, city}`` dict.

    Accepted formats
    ----------------
    - ``None``                   → ``{lat: 0, lng: 0, city: "Unknown"}``
    - ``"Mumbai"``               → looked up in _CITY_COORDS
    - ``"19.0760,72.8777"``      → parsed as lat,lng (city="Unknown")
    - ``"Mumbai,19.0760,72.8777"``→ city + explicit coords
    """
    if not location:
        return {"lat": 0.0, "lng": 0.0, "city": "Unknown"}

    parts = [p.strip() for p in location.split(",")]

    # Try fully-numeric two-part "lat,lng"
    if len(parts) == 2:
        try:
            return {"lat": float(parts[0]), "lng": float(parts[1]), "city": "Unknown"}
        except ValueError:
            pass

    # Three-part "city,lat,lng"
    if len(parts) == 3:
        try:
            return {"lat": float(parts[1]), "lng": float(parts[2]), "city": parts[0]}
        except ValueError:
            pass

    # Plain city name
    city_key = parts[0].lower()
    if city_key in _CITY_COORDS:
        lat, lng = _CITY_COORDS[city_key]
        return {"lat": lat, "lng": lng, "city": parts[0]}

    # Unrecognised string — store as city name with zero coords
    return {"lat": 0.0, "lng": 0.0, "city": parts[0]}


class CurrencyAnalyzer:
    """
    Handles the full currency verification workflow:
    OpenCV preprocessing → Gemini Vision analysis → result storage.
    """

    def __init__(self):
        self.gemini = get_gemini_service()

    def preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        Preprocess currency image using OpenCV for better analysis accuracy.

        Pipeline: Denoise → CLAHE contrast enhancement → perspective correction.
        Falls back to raw bytes if OpenCV is unavailable.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Preprocessed image bytes (JPEG encoded)
        """
        if not OPENCV_AVAILABLE:
            logger.debug("opencv_fallback", message="Passing raw image bytes")
            return image_bytes

        try:
            # Decode image
            img_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None:
                logger.warning("image_decode_failed", message="Could not decode image, using raw bytes")
                return image_bytes

            # 1. Noise reduction
            denoised = cv2.fastNlMeansDenoisingColored(img, h=10, hForColorComponents=10)

            # 2. Contrast enhancement using CLAHE on L channel of LAB color space
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l_channel)
            enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

            # 3. Perspective correction via contour detection
            enhanced = self._perspective_correct(enhanced, img)

            # Encode back to JPEG
            success, buffer = cv2.imencode('.jpg', enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if success:
                logger.info("image_preprocessed", original_size=len(image_bytes), processed_size=len(buffer))
                return buffer.tobytes()
            else:
                return image_bytes

        except Exception as e:
            logger.error("image_preprocessing_failed", error=str(e))
            return image_bytes

    def _perspective_correct(self, enhanced: 'np.ndarray', original: 'np.ndarray') -> 'np.ndarray':
        """
        Attempt perspective correction by finding the largest quadrilateral contour.
        Falls back to enhanced image if correction fails.
        """
        try:
            gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)

            # Dilate to connect edge gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(edges, kernel, iterations=2)

            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return enhanced

            # Find the largest contour by area
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            img_area = enhanced.shape[0] * enhanced.shape[1]

            # Only correct if the contour covers at least 20% of the image
            if area < img_area * 0.2:
                return enhanced

            # Approximate to quadrilateral
            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

            if len(approx) == 4:
                # Order points: top-left, top-right, bottom-right, bottom-left
                pts = approx.reshape(4, 2).astype(np.float32)
                rect = self._order_points(pts)

                # Compute target dimensions
                width = max(
                    np.linalg.norm(rect[0] - rect[1]),
                    np.linalg.norm(rect[2] - rect[3]),
                )
                height = max(
                    np.linalg.norm(rect[0] - rect[3]),
                    np.linalg.norm(rect[1] - rect[2]),
                )

                dst = np.array([
                    [0, 0],
                    [width - 1, 0],
                    [width - 1, height - 1],
                    [0, height - 1],
                ], dtype=np.float32)

                matrix = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(enhanced, matrix, (int(width), int(height)))

                logger.debug("perspective_corrected")
                return warped

            return enhanced

        except Exception as e:
            logger.debug("perspective_correction_skipped", reason=str(e))
            return enhanced

    @staticmethod
    def _order_points(pts: 'np.ndarray') -> 'np.ndarray':
        """Order points as: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        return rect

    async def start_verification(self, image_bytes: bytes, content_type: str, denomination: Optional[int] = None, location: Optional[str] = None) -> str:
        """
        Create a task for async currency verification via Celery.

        Args:
            image_bytes: Raw image bytes
            content_type: MIME type of the image
            denomination: Optional currency denomination
            location: Optional location string

        Returns:
            task_id for polling
        """
        task_id = task_store.create_task(task_type="currency_verify")

        # Upload image to Firebase Storage
        storage = get_storage_service()
        file_url = storage.upload_file(image_bytes, content_type, folder="currency_scans")

        # Dispatch Celery task
        from tasks.currency_tasks import verify_currency_task
        verify_currency_task.delay(task_id, file_url, denomination, location)

        logger.info("verification_queued_to_celery", task_id=task_id, denomination=denomination)
        return task_id

    async def run_verification(self, task_id: str, file_url: str = None, denomination: Optional[int] = None, location: Optional[str] = None) -> None:
        """
        Execute the actual currency verification (called by Kafka worker).

        Args:
            task_id: The task ID to update
            file_url: Firebase storage URL of the image
            denomination: Optional denomination
            location: Optional location
        """
        try:
            task_store.update_task(task_id, status="processing")

            if not file_url:
                task_store.update_task(task_id, status="failed", error="Missing file_url in task data")
                return

            storage = get_storage_service()
            image_bytes = storage.download_file(file_url)

            # 0. Assess image quality before any processing
            from services.image_quality_service import get_image_quality_service
            quality_svc = get_image_quality_service()
            quality_report = quality_svc.assess(image_bytes)

            if not quality_report.is_usable:
                # Image too poor for reliable analysis
                task_result = {
                    "verdict": "UNCLEAR_IMAGE",
                    "confidence": 0.0,
                    "failed_features": ["image_quality_insufficient"],
                    "analysis": (
                        f"Image quality check failed: {quality_report.rejection_reason}. "
                        f"Please retake the photo with better lighting and focus."
                    ),
                    "alert_generated": False,
                    "image_quality": {
                        "is_usable": quality_report.is_usable,
                        "blur_score": quality_report.blur_score,
                        "brightness": quality_report.brightness,
                        "resolution": list(quality_report.resolution),
                        "warnings": quality_report.warnings,
                        "rejection_reason": quality_report.rejection_reason,
                    },
                }
                task_store.update_task(task_id, status="complete", result=task_result)
                logger.info("verification_rejected_quality", task_id=task_id, reason=quality_report.rejection_reason)
                return

            # 1. Preprocess Image
            processed_bytes = self.preprocess_image(image_bytes)

            # 2. Analyze with Gemini Vision
            result = await self.gemini.analyze_currency_image(processed_bytes, denomination)

            # 3. Determine if alert should be generated
            alert_generated = False
            verdict = result.get("verdict", "SUSPICIOUS")
            failed_features = result.get("failed_features", [])

            if failed_features:
                try:
                    from models.database import get_sqlite_connection
                    with get_sqlite_connection() as conn:
                        for feature in failed_features:
                            conn.execute(
                                "INSERT INTO currency_failures (task_id, feature_name) VALUES (?, ?)",
                                (task_id, str(feature))
                            )
                except Exception as db_err:
                    logger.error("currency_failure_db_insert_error", error=str(db_err))

            if verdict in ("COUNTERFEIT", "SUSPICIOUS"):
                try:
                    from services.alert_service import get_alert_service
                    alert_svc = get_alert_service()
                    await alert_svc.create_alert(
                        alert_type="ficn_detected",
                        severity="CRITICAL" if verdict == "COUNTERFEIT" else "HIGH",
                        title=f"{'Counterfeit' if verdict == 'COUNTERFEIT' else 'Suspicious'} currency detected",
                        description=f"Rs {denomination or 'unknown'} note flagged. {result.get('analysis', '')}",
                    )
                    alert_generated = True
                except Exception as e:
                    logger.error("currency_alert_failed", error=str(e))

            # 4. Store complete result (including quality report)
            task_result = {
                "verdict": verdict,
                "confidence": result.get("confidence", 0.5),
                "failed_features": result.get("failed_features", []),
                "analysis": result.get("analysis", ""),
                "alert_generated": alert_generated,
                "image_quality": {
                    "is_usable": quality_report.is_usable,
                    "blur_score": quality_report.blur_score,
                    "brightness": quality_report.brightness,
                    "resolution": list(quality_report.resolution),
                    "warnings": quality_report.warnings,
                },
            }

            task_store.update_task(task_id, status="complete", result=task_result)

            logger.info(
                "verification_complete",
                task_id=task_id,
                verdict=verdict,
                confidence=result.get("confidence"),
            )

            # 5. Persist to Firestore so /stats and /ficn-map reflect real uploads
            await self._persist_to_firestore(
                task_id=task_id,
                denomination=denomination,
                file_url=file_url,
                location=location,
                task_result=task_result,
            )

        except Exception as e:
            logger.error("verification_failed", task_id=task_id, error=str(e))
            task_store.update_task(task_id, status="failed", error=str(e))

    async def _persist_to_firestore(
        self,
        task_id: str,
        denomination: Optional[int],
        file_url: Optional[str],
        location: Optional[str],
        task_result: dict,
    ) -> None:
        """
        Best-effort write of the completed verification result into the
        Firestore ``currency_checks`` collection.

        This makes ``/api/currency/stats`` and ``/api/currency/ficn-map``
        reflect real uploads rather than only seeded demo data.
        A failure here is logged but does NOT fail the overall task.
        """
        try:
            from models.database import get_firestore_client
            db = get_firestore_client()
            if db is None:
                logger.warning("firestore_unavailable_skipping_currency_persist", task_id=task_id)
                return

            doc = {
                "id": task_id,
                "denomination": denomination,
                "verdict": task_result.get("verdict"),
                "confidence": task_result.get("confidence"),
                "failed_features": task_result.get("failed_features", []),
                "gemini_analysis": task_result.get("analysis", ""),
                "image_url": file_url or "",
                "location": _parse_location(location),
                "submitted_by": "field_upload",
                "created_at": datetime.now(timezone.utc),
            }
            db.collection("currency_checks").document(task_id).set(doc)
            logger.info("currency_check_persisted_to_firestore", task_id=task_id, verdict=doc["verdict"])
        except Exception as persist_err:
            logger.error("currency_firestore_persist_failed", task_id=task_id, error=str(persist_err))

    def get_result(self, task_id: str) -> Optional[dict]:
        """
        Get the result of a currency verification task.

        Returns:
            dict matching CurrencyResultResponse, or None if not found
        """
        task = task_store.get_task(task_id)
        if not task:
            return None

        result = {
            "status": task["status"],
            "verdict": None,
            "confidence": None,
            "failed_features": None,
            "analysis": None,
            "alert_generated": None,
        }

        if task["status"] == "complete" and task.get("result"):
            result.update(task["result"])
        elif task["status"] == "failed":
            result["analysis"] = task.get("error", "Verification failed")

        return result

    async def get_ficn_map(self) -> list:
        """
        Get FICN incident locations for the map overlay.

        Returns:
            List of FICN incident dicts
        """
        try:
            from models.database import get_firestore_client
            db = get_firestore_client()

            checks_ref = db.collection("currency_checks")
            query = checks_ref.where("verdict", "in", ["COUNTERFEIT", "SUSPICIOUS"]).stream()

            incidents = []
            for doc in query:
                data = doc.to_dict()
                loc = data.get("location", {})
                incidents.append({
                    "lat": loc.get("lat", 0),
                    "lng": loc.get("lng", 0),
                    "city": loc.get("city", "Unknown"),
                    "denomination": data.get("denomination", 0),
                    "date": str(data.get("created_at", "")),
                })

            return incidents

        except Exception as e:
            logger.error("get_ficn_map_failed", error=str(e))
            return []

    async def get_stats(self) -> dict:
        """
        Get currency check statistics.

        Returns:
            dict matching CurrencyStatsResponse schema
        """
        try:
            from models.database import get_firestore_client
            from services.firestore_utils import count_query
            db = get_firestore_client()

            checks_ref = db.collection("currency_checks")
            all_checks = list(checks_ref.limit(1000).stream())

            total = count_query(checks_ref) or len(all_checks)
            ficn_query = checks_ref.where("verdict", "in", ["COUNTERFEIT", "SUSPICIOUS"])
            ficn_count = count_query(ficn_query)
            ficn = ficn_count or 0
            denominations: dict = {}

            for doc in all_checks:
                data = doc.to_dict()
                if ficn_count is None and data.get("verdict") in ("COUNTERFEIT", "SUSPICIOUS"):
                    ficn += 1
                denom = str(data.get("denomination", "unknown"))
                denominations[denom] = denominations.get(denom, 0) + 1

            return {
                "total_checked": total,
                "ficn_detected": ficn,
                "detection_rate": round(ficn / total, 4) if total > 0 else 0.0,
                "top_denominations": denominations,
            }

        except Exception as e:
            logger.error("get_currency_stats_failed", error=str(e))
            return {
                "total_checked": 0,
                "ficn_detected": 0,
                "detection_rate": 0.0,
                "top_denominations": {},
            }


# Module-level singleton
_currency_analyzer: CurrencyAnalyzer | None = None


def get_currency_analyzer() -> CurrencyAnalyzer:
    """Get the CurrencyAnalyzer singleton."""
    global _currency_analyzer
    if _currency_analyzer is None:
        _currency_analyzer = CurrencyAnalyzer()
    return _currency_analyzer
