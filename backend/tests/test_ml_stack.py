"""
Tests for ML Stack availability and imports.
"""

import sys
import pytest


def test_core_ml_imports():
    """Verify that core ML libraries can be imported."""
    # These should be installed in the dev environment
    import cv2
    import numpy as np

    assert cv2.__version__ is not None
    assert np.__version__ is not None


def test_huggingface_imports():
    """Verify that transformers and torch can be imported."""
    import torch
    import transformers

    assert torch.__version__ is not None
    assert transformers.__version__ is not None


def test_gemini_import():
    """Verify Google GenAI SDK can be imported."""
    from google import genai
    from google.genai import types

    assert genai is not None
    assert types is not None
