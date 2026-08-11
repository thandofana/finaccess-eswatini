# Phase 2 Leakage Review

## Decision hierarchy

1. Remove the target itself, the parallel outcome, identifiers, metadata, constants, and all-missing fields.
2. Exclude variables used to construct or screen the target (`DIRECT`).
3. Exclude contemporaneous financial behaviours and transactions (`HIGH`).
4. Review recent digital behaviours for temporal overlap (`MODERATE`).
5. Retain only interpretable pre-outcome profile characteristics as core or conditional candidates.

## Model-specific status counts

- Model 1: `{"CANDIDATE_CONDITIONAL": 8, "CANDIDATE_CORE": 8, "EXCLUDE_ALL_MISSING": 14, "EXCLUDE_CONCEPTUAL": 2, "EXCLUDE_DIRECT_LEAKAGE": 8, "EXCLUDE_HIGH_MISSING": 92, "EXCLUDE_IDENTIFIER": 1, "EXCLUDE_METADATA": 6, "EXCLUDE_MODEL_SCOPE": 10, "EXCLUDE_NO_VARIANCE": 1, "EXCLUDE_PARALLEL_OUTCOME": 1, "EXCLUDE_POST_OUTCOME": 45, "EXCLUDE_REDUNDANT": 2, "TARGET": 1}`
- Model 2: `{"CANDIDATE_CONDITIONAL": 18, "CANDIDATE_CORE": 8, "EXCLUDE_ALL_MISSING": 14, "EXCLUDE_CONCEPTUAL": 2, "EXCLUDE_DIRECT_LEAKAGE": 16, "EXCLUDE_HIGH_MISSING": 92, "EXCLUDE_IDENTIFIER": 1, "EXCLUDE_METADATA": 6, "EXCLUDE_NO_VARIANCE": 1, "EXCLUDE_PARALLEL_OUTCOME": 1, "EXCLUDE_POST_OUTCOME": 37, "EXCLUDE_REDUNDANT": 2, "TARGET": 1}`

## High-impact exclusions

- Model 1 excludes `account_mob` as a parallel financial-access outcome and excludes formal-account ownership, debit-card, account-use, and account-barrier branches as leakage.
- Model 2 excludes `account_fin` as a parallel outcome and excludes all mobile-money ownership, barrier, frequency, transaction, and mobile-payment variables as leakage.
- Both models exclude `account`, `dig_account`, payment receipt modes, and constructed digital-payment measures.
- `internet_use` is retained, while nested source questions `con24` and `con25` are excluded as redundant components.
- `fin24c` is the only `fin*` questionnaire field admitted as a conditional candidate because it measures an exogenous disaster exposure rather than financial adoption or behaviour.
- `fin46` is retained as identity-document access; other ID fields are excluded because they are post-event, highly routed, or entirely missing.
