# Phase 6 — Feature Engineering

## Scope

Phase 6 applies deterministic, interpretable transformations to Phase 3 predictors and freezes one model-specific matrix per outcome. No train/test split, model fitting, tuning, evaluation, or SHAP analysis is performed.

## Final matrices

| Model | Target | Rows | Final predictors | Total columns | Null cells |
|---|---|---:|---:|---:|---:|
| Financial inclusion | `account_fin` | 1051 | 15 | 16 | 0 |
| Mobile money | `account_mob` | 1051 | 16 | 17 | 0 |

Respondent-level outputs remain Git-ignored. All 1,051 rows and both target distributions are preserved.

## Retained transformations

- `age_group`: fixed 15–24, 25–34, 35–44, 45–54, 55–64, and 65+ bands replace raw age. Fixed rules avoid learning cut points from either outcome, provide non-linearity, and keep explanations readable.
- `phone_access_tier`: phone ownership and routed phone type become one consistent state: smartphone, basic phone, no personal phone, or explicit nonresponse.
- `internet_engagement_level` (Model 2 only): recent internet use and use frequency are consolidated without treating routed non-use as random missingness.
- `data_purchase_pattern` (Model 2 only): internet eligibility, data purchasing, and purchase frequency are combined into explicit routed states.

## Excluded proposals

- `online_activity_breadth` was rejected. Its seven recent mobile activities overlap the mobile-money outcome period, increase assessment burden, and risk encoding unstable behavior rather than durable access characteristics.
- A generic `digital_access_score` was rejected because arbitrary equal weighting would double-count related inputs and obscure truthful SHAP explanations.
- Raw age, `con1`, and `con9` are removed after their approved replacements are created. Model 2 also removes component fields `internet_use`, `con26`, `con27`, and `con28` after consolidation.

## Leakage safeguards

- No feature function reads, aggregates, or conditions on either target.
- Transformations learn no sample statistics and therefore can be reproduced identically at inference time.
- Parallel targets, identifiers, metadata, weights, account behaviors, and constructed payment outcomes remain absent.
- Automated tests verify that changing the target leaves every engineered predictor unchanged.

## Final preprocessing contract

All final predictors are categorical. Later model phases must one-hot encode them inside a complete training-fold pipeline with unknown-category tolerance. No encoder is fitted in Phase 6.

## Notes carried forward

- Fixed age bands trade some within-band detail for interpretability and non-linearity; Phase 7/8 evaluation must reveal whether that tradeoff generalizes.
- Model 2 internet and data-purchase fields are non-financial digital behaviors, but they overlap the mobile-money target observation window; this limitation remains explicit.
- `internet_use=0` combines no, don't know, and refused, so the derived no-recent-use state preserves that ambiguity in its label.
- Feature decisions are semantic and data-quality based; no full-sample target association or model score was used to select them.
