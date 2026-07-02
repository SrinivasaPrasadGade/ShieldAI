# ShieldAI Model Evaluation Report

**Generated:** 2026-07-02T14:38:20Z
**Dataset:** scam_eval_v1.jsonl (68 samples)

## Summary

| Model | Accuracy | Precision | Recall | F1 | FPR | FNR | p50 (ms) | p95 (ms) |
|-------|----------|-----------|--------|----|----|-----|----------|----------|
| Keyword Heuristic | 41.18% | 100.00% | 11.11% | 20.00% | 0.00% | 88.89% | 0 | 0 |
| Gemini AI (mock) | 41.18% | 100.00% | 11.11% | 20.00% | 0.00% | 88.89% | 0 | 0 |

## Per-Language: Keyword Heuristic

| Language | Total | Accuracy | Precision | Recall | F1 |
|----------|-------|----------|-----------|--------|-------|
| en | 43 | 46.51% | 100.00% | 14.81% | 25.81% |
| hi | 6 | 33.33% | 0.00% | 0.00% | 0.00% |
| hinglish | 13 | 30.77% | 100.00% | 10.00% | 18.18% |
| ta | 3 | 33.33% | 0.00% | 0.00% | 0.00% |
| te | 3 | 33.33% | 0.00% | 0.00% | 0.00% |

## Per-Language: Gemini AI (mock)

| Language | Total | Accuracy | Precision | Recall | F1 |
|----------|-------|----------|-----------|--------|-------|
| en | 43 | 46.51% | 100.00% | 14.81% | 25.81% |
| hi | 6 | 33.33% | 0.00% | 0.00% | 0.00% |
| hinglish | 13 | 30.77% | 100.00% | 10.00% | 18.18% |
| ta | 3 | 33.33% | 0.00% | 0.00% | 0.00% |
| te | 3 | 33.33% | 0.00% | 0.00% | 0.00% |

## Per-Type: Keyword Heuristic

| Type | Total | Accuracy | Precision | Recall | F1 |
|------|-------|----------|-----------|--------|-------|
| appointment_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| bank_communication | 4 | 100.00% | 0.00% | 0.00% | 0.00% |
| customs_parcel | 6 | 0.00% | 0.00% | 0.00% | 0.00% |
| delivery_update | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| digital_arrest | 15 | 26.67% | 100.00% | 26.67% | 42.11% |
| ecommerce_notification | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| entertainment | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| greeting | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| insurance_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| investment_fraud | 6 | 0.00% | 0.00% | 0.00% | 0.00% |
| kyc_otp | 9 | 11.11% | 100.00% | 11.11% | 20.00% |
| legitimate_police | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| loan_app_harassment | 3 | 0.00% | 0.00% | 0.00% | 0.00% |
| lottery_fraud | 2 | 0.00% | 0.00% | 0.00% | 0.00% |
| social_chat | 7 | 100.00% | 0.00% | 0.00% | 0.00% |
| subscription_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| trai_sim_block | 3 | 0.00% | 0.00% | 0.00% | 0.00% |
| travel_alert | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| utility_bill | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| utility_scam | 1 | 0.00% | 0.00% | 0.00% | 0.00% |
| work_communication | 2 | 100.00% | 0.00% | 0.00% | 0.00% |

## Per-Type: Gemini AI (mock)

| Type | Total | Accuracy | Precision | Recall | F1 |
|------|-------|----------|-----------|--------|-------|
| appointment_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| bank_communication | 4 | 100.00% | 0.00% | 0.00% | 0.00% |
| customs_parcel | 6 | 0.00% | 0.00% | 0.00% | 0.00% |
| delivery_update | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| digital_arrest | 15 | 26.67% | 100.00% | 26.67% | 42.11% |
| ecommerce_notification | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| entertainment | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| greeting | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| insurance_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| investment_fraud | 6 | 0.00% | 0.00% | 0.00% | 0.00% |
| kyc_otp | 9 | 11.11% | 100.00% | 11.11% | 20.00% |
| legitimate_police | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| loan_app_harassment | 3 | 0.00% | 0.00% | 0.00% | 0.00% |
| lottery_fraud | 2 | 0.00% | 0.00% | 0.00% | 0.00% |
| social_chat | 7 | 100.00% | 0.00% | 0.00% | 0.00% |
| subscription_reminder | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| trai_sim_block | 3 | 0.00% | 0.00% | 0.00% | 0.00% |
| travel_alert | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| utility_bill | 1 | 100.00% | 0.00% | 0.00% | 0.00% |
| utility_scam | 1 | 0.00% | 0.00% | 0.00% | 0.00% |
| work_communication | 2 | 100.00% | 0.00% | 0.00% | 0.00% |