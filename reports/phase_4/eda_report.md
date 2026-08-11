# Phase 4 — Exploratory Data Analysis

## Scope and estimation

This phase describes patterns in the supplied Eswatini microdata. Weighted rates use the supplied `wgt` field and are accompanied by unweighted respondent counts in the CSV tables. The results show association, not causation. No hypothesis tests, p-values, predictive models, or feature-selection decisions are included.

## Overall access

| Outcome | Weighted estimate | Unweighted sample rate | Positive responses | n |
|---|---:|---:|---:|---:|
| Financial institution account | 43.1% | 51.1% | 537 | 1,051 |
| Mobile money account | 50.4% | 58.1% | 611 | 1,051 |

## Question-driven findings

### 1. How common are financial inclusion and mobile-money adoption?

The weighted financial-inclusion estimate is 43.1%; the weighted mobile-money estimate is 50.4%.

**Interpretation:** Mobile-money adoption is more common than financial-institution account ownership in the weighted descriptive estimates.

### 2. Does financial access differ by education?

Financial inclusion is 82.4% among respondents with tertiary education or more and 36.8% among those with primary education or less.

**Interpretation:** Education level is associated with a large descriptive financial-inclusion gap.

### 3. Does financial access differ by household income?

Financial inclusion rises from 34.1% in quintile 1 to 65.0% in quintile 5.

**Interpretation:** Higher income quintiles are associated with higher financial-inclusion rates, although mobile-money rates are not perfectly monotonic across all quintiles.

### 4. Does workforce participation matter descriptively?

Financial inclusion is 55.8% in the workforce and 30.6% outside it.

**Interpretation:** Workforce participation is associated with higher observed financial inclusion and mobile-money adoption.

### 5. How is recent internet use associated with the outcomes?

Mobile-money adoption is 60.5% among recent internet users and 39.7% in the combined zero category.

**Interpretation:** Recent internet use is associated with higher observed financial inclusion and mobile-money adoption.

### 6. How is mobile-phone ownership associated with mobile money?

Mobile-money adoption is 55.2% among phone owners and 20.4% among respondents reporting no phone.

**Interpretation:** Phone ownership is associated with a sizeable mobile-money adoption gap.

## Additional observations

- Gender gaps are modest in the weighted descriptive rates compared with several age, education, income, employment, internet, and phone-access differences.
- Respondents aged 15–24 have the lowest observed weighted rates for both outcomes among the defined age groups.
- The highest mobile-money rate by income appears in quintile 4 rather than quintile 5, so the income pattern for mobile money is not strictly monotonic.
- `urbanicity` cannot support an urban/rural comparison because Phase 1 found it is constant in this country extract.

## Interpretation guardrails

- These are bivariate descriptive comparisons and may reflect confounding or correlated characteristics.
- Weighted estimates are population-oriented descriptions; unweighted counts show the actual sample evidence behind each group.
- The file provides a weight but no strata or cluster variables used here, so Phase 4 does not calculate survey-design standard errors or confidence intervals.
- Nonresponse and routed states remain in `subgroup_rates.csv`; non-substantive response categories are omitted from figures, and substantive groups require at least 10 respondents.
- The constructed `internet_use=0` category combines no, don't know, and refused and cannot be disaggregated.
- Formal association testing and effect sizes belong to Phase 5 and have not been performed.

## Deliverables

- `overall_rates.csv`: weighted and unweighted national descriptive rates
- `subgroup_rates.csv`: complete outcome-by-group summary with sample sizes and chart-eligibility flags
- `figures/`: publication-ready PNG and SVG charts
- `chart_manifest.csv`: chart purpose, notes, hashes, and file sizes
- `eda_summary.json`: machine-readable findings and validation metadata
