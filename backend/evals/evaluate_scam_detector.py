import json
import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scam_detector import ScamDetector
from services.gemini_service import init_gemini_service
from services.zero_shot_classifier import init_zero_shot_classifier
from config import settings

async def evaluate():
    print("Initializing services...")
    # Initialize singletons
    init_gemini_service(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)
    init_zero_shot_classifier()
    
    detector = ScamDetector()
    
    data_path = Path(__file__).parent / "data" / "dataset.json"
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    y_true = []
    y_pred = []
    results = []
    
    print(f"Evaluating {len(dataset)} examples...")
    for item in dataset:
        print(f"Processing ID {item['id']}...")
        text = item["text"]
        true_label = item["true_label"] # "SCAM" or "LEGITIMATE"
        
        try:
            res = await detector.analyze_text(text)
            # If risk_label is HIGH or MEDIUM, predict SCAM. If LOW, predict LEGITIMATE.
            pred = "SCAM" if res["risk_label"] in ["HIGH", "MEDIUM"] else "LEGITIMATE"
        except Exception as e:
            print(f"Error processing ID {item['id']}: {e}")
            res = {}
            pred = "ERROR"
            
        y_true.append(true_label)
        y_pred.append(pred)
        
        results.append({
            "id": item["id"],
            "text": text,
            "true_label": true_label,
            "predicted_label": pred,
            "risk_score": res.get("risk_score") if pred != "ERROR" else None,
            "risk_label": res.get("risk_label") if pred != "ERROR" else None
        })
        
    # Compute metrics
    correct = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    for t, p in zip(y_true, y_pred):
        if p == "ERROR":
            continue
        if t == p:
            correct += 1
        if p == "SCAM" and t == "SCAM":
            true_positives += 1
        elif p == "SCAM" and t == "LEGITIMATE":
            false_positives += 1
        elif p == "LEGITIMATE" and t == "SCAM":
            false_negatives += 1
            
    total = len([p for p in y_pred if p != "ERROR"])
    accuracy = correct / total if total > 0 else 0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    report_content = f"""# ScamDetector Evaluation Report

## Metrics
- **Total Examples**: {total}
- **Accuracy**: {accuracy:.2%}
- **Precision**: {precision:.2%}
- **Recall**: {recall:.2%}
- **F1 Score**: {f1:.2%}

## Detailed Results
| ID | True Label | Predicted Label | Risk Score | Risk Label | Status |
|----|------------|-----------------|------------|------------|--------|
"""
    for r in results:
        status = "✅" if r["true_label"] == r["predicted_label"] else "❌"
        score = f"{r['risk_score']:.2f}" if r["risk_score"] is not None else "N/A"
        report_content += f"| {r['id']} | {r['true_label']} | {r['predicted_label']} | {score} | {r['risk_label']} | {status} |\n"
        
    report_path = Path(__file__).parent / "report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Evaluation complete. Report saved to {report_path}")
    
    # Check baseline thresholds
    if accuracy < 0.85 or f1 < 0.80:
        print(f"[FAIL] Quality below baseline! Accuracy: {accuracy:.2%}, F1: {f1:.2%}")
        sys.exit(1)
    else:
        print(f"[PASS] Quality meets baseline! Accuracy: {accuracy:.2%}, F1: {f1:.2%}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    # Load .env file from root
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    asyncio.run(evaluate())
