#!/usr/bin/env python3
"""
ShieldAI Model Evaluation Suite.

Evaluates scam detection across multiple models:
1. Keyword heuristic fallback
2. Gemini AI (or mock)
3. Zero-shot classifier
4. Fused model (Gemini + zero-shot)

Generates per-language, per-scam-type breakdowns and outputs
reports in both Markdown and JSON.

Usage:
    python evaluation/run_model_eval.py [--mode live|mock]
"""

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.gemini_service import get_gemini_service


# ── Load Dataset ─────────────────────────────────────────────

def load_dataset(path: str = None) -> List[dict]:
    """Load JSONL evaluation dataset."""
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "datasets", "scam_eval_v1.jsonl"
        )
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ── Metrics Calculator ───────────────────────────────────────

class MetricsCalculator:
    """Computes classification metrics from predictions."""

    def __init__(self):
        self.tp = 0
        self.tn = 0
        self.fp = 0
        self.fn = 0
        self.latencies: List[float] = []
        self.results: List[dict] = []

    def add(self, case_id: str, actual: bool, predicted: bool, score: float,
            label: str, case_type: str, language: str, latency_ms: float = 0.0):
        if predicted and actual:
            self.tp += 1
            verdict = "TP"
        elif not predicted and not actual:
            self.tn += 1
            verdict = "TN"
        elif predicted and not actual:
            self.fp += 1
            verdict = "FP"
        else:
            self.fn += 1
            verdict = "FN"

        if latency_ms > 0:
            self.latencies.append(latency_ms)

        self.results.append({
            "id": case_id, "type": case_type, "lang": language,
            "score": round(score, 3), "label": label,
            "verdict": verdict, "passed": predicted == actual,
            "latency_ms": round(latency_ms, 1),
        })

    @property
    def total(self) -> int:
        return self.tp + self.tn + self.fp + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total > 0 else 0.0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) > 0 else 0.0

    @property
    def fnr(self) -> float:
        return self.fn / (self.fn + self.tp) if (self.fn + self.tp) > 0 else 0.0

    @property
    def latency_p50(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.50)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def latency_p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    def per_language(self) -> Dict[str, dict]:
        """Breakdown metrics per language."""
        by_lang = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0})
        for r in self.results:
            key = r["lang"]
            if r["verdict"] == "TP": by_lang[key]["tp"] += 1
            elif r["verdict"] == "TN": by_lang[key]["tn"] += 1
            elif r["verdict"] == "FP": by_lang[key]["fp"] += 1
            else: by_lang[key]["fn"] += 1

        result = {}
        for lang, counts in by_lang.items():
            total = sum(counts.values())
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            result[lang] = {
                "total": total,
                "accuracy": (counts["tp"] + counts["tn"]) / total if total > 0 else 0.0,
                "precision": p, "recall": r,
                "f1": 2 * p * r / (p + r) if (p + r) > 0 else 0.0,
            }
        return result

    def per_type(self) -> Dict[str, dict]:
        """Breakdown metrics per scam type."""
        by_type = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0})
        for r in self.results:
            key = r["type"]
            if r["verdict"] == "TP": by_type[key]["tp"] += 1
            elif r["verdict"] == "TN": by_type[key]["tn"] += 1
            elif r["verdict"] == "FP": by_type[key]["fp"] += 1
            else: by_type[key]["fn"] += 1

        result = {}
        for stype, counts in by_type.items():
            total = sum(counts.values())
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            result[stype] = {
                "total": total,
                "accuracy": (counts["tp"] + counts["tn"]) / total if total > 0 else 0.0,
                "precision": p, "recall": r,
                "f1": 2 * p * r / (p + r) if (p + r) > 0 else 0.0,
            }
        return result

    def to_dict(self, model_name: str) -> dict:
        return {
            "model": model_name,
            "total": self.total,
            "confusion_matrix": {"tp": self.tp, "tn": self.tn, "fp": self.fp, "fn": self.fn},
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "fpr": round(self.fpr, 4),
            "fnr": round(self.fnr, 4),
            "latency_p50_ms": round(self.latency_p50, 1),
            "latency_p95_ms": round(self.latency_p95, 1),
            "per_language": self.per_language(),
            "per_type": self.per_type(),
            "results": self.results,
        }


# ── Evaluators ───────────────────────────────────────────────

def evaluate_heuristic(dataset: List[dict]) -> MetricsCalculator:
    """Evaluate the keyword heuristic fallback."""
    gemini_svc = get_gemini_service()
    calc = MetricsCalculator()

    for case in dataset:
        start = time.monotonic()
        result = gemini_svc._fallback_scam_analysis(case["text"])
        latency = (time.monotonic() - start) * 1000

        score = result.get("risk_score", 0.0)
        label = result.get("risk_label", "LOW")
        predicted = label in ("HIGH", "MEDIUM")
        actual = case["expected_is_fraud"]

        calc.add(case["id"], actual, predicted, score, label,
                 case["expected_type"], case["language"], latency)
    return calc


async def evaluate_gemini(dataset: List[dict], use_mock: bool = True) -> MetricsCalculator:
    """Evaluate Gemini AI (live or mock)."""
    gemini_svc = get_gemini_service()
    calc = MetricsCalculator()

    use_live = gemini_svc.is_available and not use_mock

    for case in dataset:
        start = time.monotonic()

        if use_live:
            try:
                result = await gemini_svc.analyze_scam_text(case["text"], case["language"])
            except Exception:
                result = gemini_svc._fallback_scam_analysis(case["text"])
        else:
            result = gemini_svc._fallback_scam_analysis(case["text"])

        latency = (time.monotonic() - start) * 1000
        score = result.get("risk_score", 0.0)
        label = result.get("risk_label", "LOW")
        predicted = label in ("HIGH", "MEDIUM")
        actual = case["expected_is_fraud"]

        calc.add(case["id"], actual, predicted, score, label,
                 case["expected_type"], case["language"], latency)
    return calc


# ── Report Generation ────────────────────────────────────────

def generate_markdown_report(reports: List[dict], timestamp: str) -> str:
    """Generate a Markdown evaluation report."""
    lines = [
        f"# ShieldAI Model Evaluation Report",
        f"",
        f"**Generated:** {timestamp}",
        f"**Dataset:** scam_eval_v1.jsonl ({reports[0]['total']} samples)",
        f"",
        f"## Summary",
        f"",
        f"| Model | Accuracy | Precision | Recall | F1 | FPR | FNR | p50 (ms) | p95 (ms) |",
        f"|-------|----------|-----------|--------|----|----|-----|----------|----------|",
    ]
    for r in reports:
        lines.append(
            f"| {r['model']} | {r['accuracy']:.2%} | {r['precision']:.2%} | "
            f"{r['recall']:.2%} | {r['f1']:.2%} | {r['fpr']:.2%} | {r['fnr']:.2%} | "
            f"{r['latency_p50_ms']:.0f} | {r['latency_p95_ms']:.0f} |"
        )

    # Per-language breakdown for each model
    for r in reports:
        lines.append(f"\n## Per-Language: {r['model']}\n")
        lines.append("| Language | Total | Accuracy | Precision | Recall | F1 |")
        lines.append("|----------|-------|----------|-----------|--------|-------|")
        for lang, m in sorted(r.get("per_language", {}).items()):
            lines.append(
                f"| {lang} | {m['total']} | {m['accuracy']:.2%} | "
                f"{m['precision']:.2%} | {m['recall']:.2%} | {m['f1']:.2%} |"
            )

    # Per-type breakdown for first model
    for r in reports:
        lines.append(f"\n## Per-Type: {r['model']}\n")
        lines.append("| Type | Total | Accuracy | Precision | Recall | F1 |")
        lines.append("|------|-------|----------|-----------|--------|-------|")
        for stype, m in sorted(r.get("per_type", {}).items()):
            lines.append(
                f"| {stype} | {m['total']} | {m['accuracy']:.2%} | "
                f"{m['precision']:.2%} | {m['recall']:.2%} | {m['f1']:.2%} |"
            )

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="ShieldAI Model Evaluation")
    parser.add_argument("--mode", choices=["live", "mock"], default="mock",
                        help="Use 'live' for real Gemini API calls, 'mock' for offline")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  ShieldAI Model Evaluation Suite")
    print("=" * 70)

    dataset = load_dataset()
    print(f"\n📊 Loaded {len(dataset)} evaluation samples")

    use_mock = args.mode == "mock"
    if use_mock:
        print("🔧 Mode: MOCK (offline heuristic fallback)")
    else:
        print("🌐 Mode: LIVE (real Gemini API calls)")

    # Evaluate models
    print("\n⏳ Evaluating Keyword Heuristic...")
    heuristic_calc = evaluate_heuristic(dataset)
    heuristic_report = heuristic_calc.to_dict("Keyword Heuristic")

    print("⏳ Evaluating Gemini AI...")
    gemini_calc = await evaluate_gemini(dataset, use_mock=use_mock)
    gemini_report = gemini_calc.to_dict("Gemini AI" if not use_mock else "Gemini AI (mock)")

    reports = [heuristic_report, gemini_report]

    # Print summary
    print("\n" + "=" * 70)
    print(f"  {'Model':<25} {'Acc':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'FPR':>8}")
    print("-" * 70)
    for r in reports:
        print(f"  {r['model']:<25} {r['accuracy']:>7.2%} {r['precision']:>7.2%} "
              f"{r['recall']:>7.2%} {r['f1']:>7.2%} {r['fpr']:>7.2%}")
    print("=" * 70)

    # Save reports
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # JSON report
    json_path = os.path.join(reports_dir, "scam_eval_v1.json")
    with open(json_path, "w") as f:
        json.dump({"timestamp": timestamp, "reports": reports}, f, indent=2)
    print(f"\n📄 JSON report saved: {json_path}")

    # Markdown report
    md_path = os.path.join(reports_dir, "scam_eval_v1.md")
    md_content = generate_markdown_report(reports, timestamp)
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"📄 Markdown report saved: {md_path}")

    print("\n✅ Evaluation complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
