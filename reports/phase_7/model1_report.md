# Phase 7 — Model 1: Financial Inclusion

## Scope

This phase develops only the financial-inclusion classifier (`account_fin`). Mobile-money modelling, SHAP explainability, API work, and frontend work are outside this phase.

## Validation design

- Protected holdout: 211 respondents (20% target), never used for tuning or selection.
- Training set: 840 respondents.
- Identical predictor profiles are grouped in both the holdout split and five-fold cross-validation.
- Profile overlap across holdout partitions: 0.
- Selection metric: training-fold ROC-AUC. The one-standard-error rule chooses the simplest competitive model.
- Classification metrics use a provisional 0.50 threshold; it was not tuned on the holdout.
- Survey weights are not predictors or loss weights; evaluation describes respondent-level generalisation in this file.

## Candidate comparison

| Candidate | CV ROC-AUC | CV F1 | CV accuracy | Train–CV AUC gap | Selected |
|---|---:|---:|---:|---:|---|
| Gradient Boosting | 0.768 ± 0.024 | 0.705 | 0.698 | 0.045 | Yes |
| Random Forest | 0.759 ± 0.022 | 0.682 | 0.679 | 0.099 | No |
| Logistic Regression | 0.756 ± 0.023 | 0.689 | 0.688 | 0.031 | No |
| Decision Tree | 0.706 ± 0.032 | 0.637 | 0.631 | 0.055 | No |
| Dummy majority baseline | 0.500 ± 0.000 | 0.676 | 0.511 | 0.000 | No |

## Selected model

**Gradient Boosting** was selected using the pre-specified one-standard-error and complexity-tier rule.

Best parameters: `{"model__learning_rate": 0.03, "model__max_depth": 2, "model__min_samples_leaf": 5, "model__n_estimators": 200}`

## Protected-holdout results

| Metric | Value | 95% bootstrap interval where available |
|---|---:|---|
| Accuracy | 0.706 | 0.645–0.763 |
| Balanced Accuracy | 0.706 | — |
| Precision | 0.717 | 0.653–0.781 |
| Recall | 0.704 | 0.620–0.787 |
| F1 | 0.710 | 0.642–0.771 |
| Roc Auc | 0.745 | 0.674–0.805 |
| Brier Score | 0.204 | 0.182–0.229 |
| Log Loss | 0.594 | — |

Confusion counts at 0.50: TN=73, FP=30, FN=32, TP=76.

## Generalisation and calibration

- Selected-model train–CV ROC-AUC gap: 0.045 (low observed train–CV gap).
- Holdout versus mean CV ROC-AUC difference: -0.023.
- Expected calibration error across quantile bins: 0.048.
- Transformed one-hot feature count: 58.

## Limitations

- The holdout contains about one fifth of a 1,051-row dataset, so uncertainty intervals remain important.
- Forty-four identical-profile groups contain both outcomes (134 respondents), indicating that the available profile cannot perfectly separate inclusion.
- Fixed age bands lose within-band detail.
- Recent digital indicators are observational characteristics and do not establish causation.
- The 0.50 threshold is provisional; any later wording or threshold policy must be justified without using the protected holdout for repeated tuning.
- Model performance applies to this supplied survey file and is not evidence of nationwide production readiness.
