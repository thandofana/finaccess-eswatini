# Phase 3 — Data Cleaning & Preprocessing

## Scope

Phase 3 converts only the Phase 2-approved predictors into two model-specific, human-readable datasets. No data split, feature engineering, model fitting, evaluation, or explainability work is performed here.

## Generated datasets

| Dataset | Target | Rows | Predictors | Total columns | Unresolved missing cells |
|---|---|---:|---:|---:|---:|
| Model 1 | `account_fin` | 1051 | 16 | 17 | 0 |
| Model 2 | `account_mob` | 1051 | 26 | 27 | 0 |

The processed files remain Git-ignored because they contain respondent-level microdata.

## Cleaning decisions

- The source file is treated as immutable and its Phase 1 SHA-256 contract is checked before processing.
- Both binary targets remain integers coded `0` and `1`; target labels are not used as predictors.
- `age` is validated as whole years in the plausible project range 15–110 and retained as numeric.
- All other predictors are treated as categorical. Education and income quintile are not given artificial numeric distances.
- Explicit don't-know/refused codes become `Nonresponse` when the source distinguishes them.
- Constructed `No/DK/Ref` values remain the honest combined label `No / don't know / refused` because their components cannot be recovered.
- Routed blanks in conditional questions become `Not applicable / skipped`.
- The 10 blank education responses become `Missing or nonresponse` rather than being silently imputed.
- Unknown raw codes cause the cleaner to fail instead of being silently accepted.

## Duplicate policy

The reduced Model 1 dataset has 35 exact rows after the first occurrence; Model 2 has 9. These are retained because respondent IDs were unique in Phase 1, and identical profiles are plausible survey observations. The identifier itself is excluded from both modelling datasets.

## Leakage safeguards

- Model 1 contains exactly 16 approved predictors and excludes `account_mob`, all identifiers, metadata, weights, and post-outcome financial behaviour.
- Model 2 contains exactly 26 approved predictors and excludes `account_fin`, all identifiers, metadata, weights, and post-outcome financial behaviour.
- Feature lists are imported from the same central policy module used by the Phase 2 dictionary generator.
- The scikit-learn preprocessing objects are templates only and are not fitted or persisted in Phase 3.
- Later fitting must occur inside a complete model pipeline on training folds only.

## Numeric and categorical validation

- Age range after cleaning: 15–100 years.
- Non-integer age values: 0.
- Unexpected categorical codes: 0.
- Unresolved null cells across both outputs: 0.

## Important limitations carried forward

- Survey weights are intentionally excluded from individual predictors but may be used later for descriptive population estimates.
- Routed digital variables encode eligibility and access context; Phase 6 must reconsider each conditional field before final matrices are frozen.
- `internet_use=0` combines no, don't know, and refused in the supplied constructed variable; the cleaner cannot separate them.
- No inference about association, causation, or model performance is made in this phase.

## Validation outcome

All output schema, target, category, missingness, numeric-range, and leakage-boundary checks passed.
