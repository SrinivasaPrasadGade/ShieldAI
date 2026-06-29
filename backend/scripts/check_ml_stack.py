#!/usr/bin/env python3
"""
ShieldAI ML Stack Health Check Script.

Run this to verify that all ML dependencies are correctly installed
and available in the current Python environment.

Usage:
    python scripts/check_ml_stack.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_import(module_name: str, package_hint: str = "") -> bool:
    """Try to import a module and report status."""
    try:
        mod = __import__(module_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"  ✅ {module_name} — version {version}")
        return True
    except ImportError as e:
        hint = f" (pip install {package_hint})" if package_hint else ""
        print(f"  ❌ {module_name} — NOT INSTALLED{hint}")
        return False


def main():
    print("\n" + "=" * 60)
    print("  ShieldAI ML Stack Health Check")
    print("=" * 60)

    all_ok = True

    # ── Core Python ──────────────────────────────────────────
    print(f"\n🐍 Python: {sys.version}")

    # ── AI / ML Packages ─────────────────────────────────────
    print("\n📦 AI / ML Packages:")
    all_ok &= check_import("torch", "torch")
    all_ok &= check_import("transformers", "transformers")
    all_ok &= check_import("cv2", "opencv-python-headless")
    all_ok &= check_import("numpy", "numpy")

    # ── Gemini SDK ───────────────────────────────────────────
    print("\n🤖 Gemini SDK:")
    genai_ok = check_import("google.genai", "google-genai")
    all_ok &= genai_ok

    # ── Config Check ─────────────────────────────────────────
    print("\n⚙️  Configuration:")
    try:
        from config import settings
        print(f"  ENABLE_ZERO_SHOT: {settings.ENABLE_ZERO_SHOT}")
        print(f"  ZERO_SHOT_MODEL:  {settings.ZERO_SHOT_MODEL}")
        print(f"  GEMINI_MODEL:     {settings.GEMINI_MODEL}")
        has_key = bool(settings.GEMINI_API_KEY) and "your-gemini" not in settings.GEMINI_API_KEY
        print(f"  GEMINI_API_KEY:   {'✅ configured' if has_key else '❌ not configured'}")
    except Exception as e:
        print(f"  ❌ Could not load config: {e}")
        all_ok = False

    # ── Zero-shot Model Load Test ────────────────────────────
    print("\n🧠 Zero-Shot Classifier:")
    try:
        from config import settings
        if not settings.ENABLE_ZERO_SHOT:
            print("  ⏭️  Disabled (ENABLE_ZERO_SHOT=false)")
        else:
            from transformers import pipeline as hf_pipeline
            print(f"  Loading {settings.ZERO_SHOT_MODEL}...")
            pipe = hf_pipeline(
                "zero-shot-classification",
                model=settings.ZERO_SHOT_MODEL,
                device=-1,
            )
            test_result = pipe(
                "Someone called claiming to be from CBI",
                candidate_labels=["scam", "legitimate"],
            )
            print(f"  ✅ Model loaded and inference works")
            print(f"     Test: '{test_result['labels'][0]}' ({test_result['scores'][0]:.2f})")
    except ImportError:
        print("  ❌ transformers not installed")
    except Exception as e:
        print(f"  ❌ Model load/inference failed: {e}")
        all_ok = False

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    if all_ok:
        print("  ✅ ML stack is healthy!")
    else:
        print("  ⚠️  Some components are missing or misconfigured.")
        print("     Run: pip install -r backend/requirements.dev.txt")
    print("=" * 60 + "\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
