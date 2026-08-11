# Phase 2 Feature Blueprint

> Scope: documentation and eligibility decisions only. No preprocessing, feature engineering, data splitting, statistical testing, or model training was performed.

## Eligibility method

A variable is eligible only when it is plausibly available as a profile characteristic before prediction, is not the target or a target component, is not screened by target ownership, has usable Eswatini coverage, and can be collected in a future assessment without asking for the outcome itself.

`CANDIDATE_CORE` variables are complete or nearly complete and straightforward to interpret. `CANDIDATE_CONDITIONAL` variables are defensible but require routing-aware preprocessing or a documented temporal limitation in Phase 3. Candidate status is not a guarantee of final inclusion; Phase 6 will finalize engineered modelling matrices.

## Model 1 - Financial inclusion (`account_fin`)

Variable | Category | Missing | Tier | Rationale
--- | --- | ---: | --- | ---
`female` | DEMOGRAPHIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`age` | DEMOGRAPHIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`educ` | SOCIOECONOMIC | 0.95% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`inc_q` | SOCIOECONOMIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`emp_in` | SOCIOECONOMIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`fin24c` | SOCIOECONOMIC | 0.00% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`internet_use` | DIGITAL | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`con1` | DIGITAL | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`con9` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con11` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con12` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con14` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con16` | DIGITAL | 22.36% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con18` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con20` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`fin46` | IDENTITY | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.

Model 1 deliberately excludes `account_mob`, the combined `account` indicator, all financial-account behaviours, target-screened questions, and constructed payment outcomes. Its blueprint emphasizes demographic, socioeconomic, identity, and interpretable digital-access characteristics.

## Model 2 - Mobile-money adoption (`account_mob`)

Variable | Category | Missing | Tier | Rationale
--- | --- | ---: | --- | ---
`female` | DEMOGRAPHIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`age` | DEMOGRAPHIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`educ` | SOCIOECONOMIC | 0.95% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`inc_q` | SOCIOECONOMIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`emp_in` | SOCIOECONOMIC | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`fin24c` | SOCIOECONOMIC | 0.00% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`internet_use` | DIGITAL | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`con1` | DIGITAL | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.
`con9` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con11` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con12` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con14` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con16` | DIGITAL | 22.36% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con18` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con20` | DIGITAL | 11.23% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con26` | DIGITAL | 40.25% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con27` | DIGITAL | 40.25% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con28` | DIGITAL | 47.67% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30a` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30b` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30c` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30d` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30e` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30g` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`con30h` | DIGITAL | 33.68% | CANDIDATE_CONDITIONAL | Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.
`fin46` | IDENTITY | 0.00% | CANDIDATE_CORE | Interpretable pre-outcome profile characteristic with usable coverage.

Model 2 deliberately excludes `account_fin`, mobile-money ownership questions, mobile-money transaction behaviours, and constructed digital-payment outcomes. It permits a broader conditional digital-capability set than Model 1 because mobile-money adoption depends directly on phone and internet capability, while still excluding the outcome itself.

## Missingness policy for the blueprint

- 100% missing and constant variables are excluded.
- Variables at or above 50% missingness are excluded from the initial blueprint.
- Routed digital variables below 50% missingness may be conditional candidates; Phase 3 must represent structural not-applicable states explicitly rather than treating them as ordinary random missingness.
- No value is imputed or recoded in Phase 2.
