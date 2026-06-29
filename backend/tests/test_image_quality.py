"""
Tests for the ImageQualityService.
"""

import pytest
from services.image_quality_service import ImageQualityService


@pytest.fixture
def quality_svc():
    return ImageQualityService()


def test_empty_image_rejected(quality_svc):
    """Empty or very small bytes should be rejected immediately."""
    report = quality_svc.assess(b"")
    assert report.is_usable is False
    assert "too small" in report.rejection_reason.lower()


def test_corrupt_image_rejected(quality_svc):
    """Corrupt image bytes that cannot be decoded should be rejected."""
    # 200 random bytes
    corrupt_bytes = b"x" * 200
    report = quality_svc.assess(corrupt_bytes)
    assert report.is_usable is False
    assert "decode" in report.rejection_reason.lower()


def test_opencv_unavailable_fallback():
    """If OpenCV is unavailable, it should fail open (return usable)."""
    import services.image_quality_service as iqs
    
    # Mock OPENCV_AVAILABLE = False
    original_val = iqs.OPENCV_AVAILABLE
    try:
        iqs.OPENCV_AVAILABLE = False
        svc = ImageQualityService()
        
        # Valid-looking bytes (though it won't actually parse them)
        report = svc.assess(b"fake_image_data_that_is_long_enough_to_pass_size_check" * 10)
        
        assert report.is_usable is True
        assert any("opencv_not_available" in w for w in report.warnings)
    finally:
        # Restore
        iqs.OPENCV_AVAILABLE = original_val
