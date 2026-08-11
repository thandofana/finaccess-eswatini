# Phase 8 — Model 2: Mobile Money Adoption

## Scope

This phase develops only the mobile-money classifier (`account_mob`). It uses Model 2's distinct feature matrix and does not modify or retrain Model 1. SHAP, API, and frontend work remain outside this phase.

## Validation design

- Protected holdout: 210 respondents, never used for tuning or selection.
- Training set: 841 respondents.
- Identical Model 2 predictor profiles are grouped across the holdout and all five training folds.
- Profile overlap across holdout partitions: 0.
- Selection metric: training-fold ROC-AUC with the same pre-specified complexity-tier rule used for a fair protocol.
- Classification metrics use a provisional 0.50 threshold that was not tuned on the holdout.

## Candidate comparison

| Candidate | CV ROC-AUC | CV F1 | CV accuracy | Train–CV AUC gap | Selected |
|---|---:|---:|---:|---:|---|
| Random Forest | 0.716 ± 0.047 | 0.756 | 0.679 | 0.205 | No |
| Gradient Boosting | 0.712 ± 0.032 | 0.736 | 0.663 | 0.095 | No |
| Logistic Regression | 0.710 ± 0.043 | 0.700 | 0.658 | 0.050 | Yes |
| Decision Tree | 0.687 ± 0.026 | 0.723 | 0.643 | 0.039 | No |
| Dummy majority baseline | 0.500 ± 0.000 | 0.735 | 0.581 | 0.000 | No |

## Selected model

**Logistic Regression** was selected independently for mobile money.

Best parameters: `{"model__C": 0.05, "model__class_weight": "balanced"}`

## Protected-holdout results

| Metric | Value | 95% bootstrap interval where available |
|---|---:|---|
| Accuracy | 0.676 | 0.610–0.738 |
| Balanced Accuracy | 0.667 | — |
| Precision | 0.721 | 0.669–0.779 |
| Recall | 0.721 | 0.639–0.795 |
| F1 | 0.721 | 0.661–0.775 |
| Roc Auc | 0.726 | 0.657–0.791 |
| Brier Score | 0.205 | 0.186–0.226 |
| Log Loss | 0.596 | — |

Confusion counts at 0.50: TN=54, FP=34, FN=34, TP=88.

## Generalisation and calibration

- Train–CV ROC-AUC gap: 0.050 (low observed train–CV gap).
- Holdout minus mean CV ROC-AUC: 0.016.
- Expected calibration error: 0.079.
- Transformed one-hot feature count: 72.

## Limitations

- The protected holdout is small, so bootstrap intervals remain important.
- Thirty-two identical-profile groups contain both outcomes (77 respondents), limiting perfect separation.
- Recent internet and data-purchase characteristics overlap the mobile-money target observation period.
- Results describe prediction, not causation or nationwide production readiness.
- Survey weights were not used as predictors or loss weights.
- The 0.50 threshold remains provisional.
