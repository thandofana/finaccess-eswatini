# Phase 9 Explainability Report

SHAP explanations were generated separately for both validated pipelines on their protected holdouts. Contributions are additive in log-odds and are summed from one-hot columns back to original input fields.

## Leading global factors

### Financial Inclusion

- age group: mean absolute SHAP 0.3348 log-odds
- workforce status: mean absolute SHAP 0.3202 log-odds
- income quintile: mean absolute SHAP 0.2666 log-odds
- education level: mean absolute SHAP 0.2230 log-odds
- recent internet use: mean absolute SHAP 0.2027 log-odds

### Mobile Money Adoption

- SIM registration in own name: mean absolute SHAP 0.2692 log-odds
- age group: mean absolute SHAP 0.1991 log-odds
- internet engagement: mean absolute SHAP 0.1722 log-odds
- data-purchase pattern: mean absolute SHAP 0.1699 log-odds
- income quintile: mean absolute SHAP 0.1691 log-odds

## Faithfulness checks

- Maximum raw-score reconstruction error: 2.665e-15
- Maximum probability reconstruction error: 3.331e-16
- Persisted explainers were reloaded and matched to immutable pipeline hashes.
- Aggregation to source features preserves the exact sum of encoded SHAP values.

## Interpretation boundaries

- A positive SHAP value supports a higher model prediction relative to its explainer baseline; a negative value supports a lower prediction.
- SHAP explains model behaviour, not causation or an official World Bank classification.
- Correlated or conceptually overlapping inputs can share or redistribute attribution.
- The 0.50 classification threshold remains provisional from the modelling phases.
- Global rankings describe the protected holdout samples and should not be treated as population causal effects.
