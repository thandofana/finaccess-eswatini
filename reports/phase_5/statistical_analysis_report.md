# Phase 5 — Statistical Analysis

## Scope

This phase formally evaluates a limited set of associations identified before testing from Phase 4. It does not establish causation and does not train or select predictive models.

## Methods

- Categorical variables: Pearson chi-square test of independence with bias-corrected Cramér's V.
- Numeric age: two-sided Mann–Whitney U test with rank-biserial correlation.
- Multiplicity: Benjamini–Hochberg false-discovery-rate adjustment across eight tests separately for each outcome.
- Significance rule: adjusted p-value below 0.05.
- Inference uses unweighted respondent counts because no strata/cluster design variables are used; survey-weighted rates provide descriptive context only.
- Explicit nonresponse categories are excluded test-by-test. Structurally meaningful `Not applicable / skipped` phone-type responses are retained.

## Results

| Outcome | Variable | Test | Effect | Magnitude | Raw p | FDR-adjusted p | Significant |
|---|---|---|---:|---|---:|---:|---|
| Financial inclusion | Household income quintile | Pearson chi-square test of independence | 0.270 | small | 1.2e-16 | 4.81e-16 | Yes |
| Financial inclusion | Workforce status | Pearson chi-square test of independence | 0.265 | small | 5.52e-18 | 4.41e-17 | Yes |
| Financial inclusion | Education | Pearson chi-square test of independence | 0.225 | small | 1.28e-12 | 3.42e-12 | Yes |
| Financial inclusion | Respondent age | Two-sided Mann-Whitney U | 0.203 | small | 1.22e-08 | 1.96e-08 | Yes |
| Financial inclusion | Recent internet use | Pearson chi-square test of independence | 0.200 | small | 5.4e-11 | 1.08e-10 | Yes |
| Financial inclusion | Phone type | Pearson chi-square test of independence | 0.147 | small | 5.05e-06 | 6.73e-06 | Yes |
| Financial inclusion | Mobile phone ownership | Pearson chi-square test of independence | 0.084 | negligible | 0.00386 | 0.00442 | Yes |
| Financial inclusion | Gender | Pearson chi-square test of independence | 0.000 | negligible | 0.585 | 0.585 | No |
| Mobile money | Phone type | Pearson chi-square test of independence | 0.236 | small | 8.39e-14 | 6.16e-13 | Yes |
| Mobile money | Household income quintile | Pearson chi-square test of independence | 0.227 | small | 7.47e-12 | 1.49e-11 | Yes |
| Mobile money | Recent internet use | Pearson chi-square test of independence | 0.226 | small | 1.54e-13 | 6.16e-13 | Yes |
| Mobile money | Mobile phone ownership | Pearson chi-square test of independence | 0.213 | small | 3.04e-12 | 8.11e-12 | Yes |
| Mobile money | Workforce status | Pearson chi-square test of independence | 0.172 | small | 1.58e-08 | 2.52e-08 | Yes |
| Mobile money | Education | Pearson chi-square test of independence | 0.151 | small | 2.56e-06 | 3.42e-06 | Yes |
| Mobile money | Respondent age | Two-sided Mann-Whitney U | 0.108 | small | 0.00278 | 0.00317 | Yes |
| Mobile money | Gender | Pearson chi-square test of independence | 0.000 | negligible | 0.699 | 0.699 | No |

## Main statistical findings

- Financial inclusion was associated after FDR adjustment with education, income quintile, workforce status, recent internet use, phone ownership, phone type, and age; gender was not associated.
- Mobile-money adoption was associated after FDR adjustment with education, income quintile, workforce status, recent internet use, phone ownership, phone type, and age; gender was not associated.
- The largest categorical effect for financial inclusion was income quintile (bias-corrected Cramér's V=0.270), closely followed by workforce status.
- The largest categorical effect for mobile money was phone type (bias-corrected Cramér's V=0.236), followed by income quintile and recent internet use.
- Included respondents were older on average for both outcomes; the age effect was small for financial inclusion (rank-biserial=0.203) and mobile money (rank-biserial=0.108).

## Assumption checks

- All 14 categorical tests had zero expected cells below 5.
- Minimum expected cell count across all categorical tests: 36.4.
- Mann–Whitney inference uses its asymptotic two-sided implementation and accommodates tied ages through SciPy's tie correction.

## Interpretation limits

- Statistical significance does not measure practical importance; effect sizes are reported for that reason.
- Conventional effect labels are descriptive guides, not universal cutoffs.
- Tests are bivariate and are not adjusted for confounding characteristics.
- Survey weighting is not sufficient for design-corrected inference without the relevant strata and cluster information.
- `internet_use=0` still combines no, don't know, and refused.
- These results inform later analysis but do not automatically determine model features.
