# Phase 1 Data Quality Report

> Scope: raw-data structure and quality only. No cleaning, feature eligibility decisions, leakage review, statistical testing, or modelling was performed.

## Source integrity

- File: `data/raw/Findex_Microdata_2025_updateEswatini.csv`
- Size: 410,650 bytes
- SHA-256: `4968eaa568df1ddf8d5fadea39f4797d1bdecc2c3f941546936a200ce4bc210c`
- Decoded as: `utf-8-sig`

## Structural validation

- Shape: **1,051 rows × 199 columns**
- Row widths: `{199: 1051}`
- Blank headers: 0
- Duplicate headers: 0
- Exact duplicate rows excluding the first occurrence: **0**
- Duplicate respondent-ID values: **0**
- Duplicate response profiles after excluding only `wpid_random`: **1** across 1 group(s)

## Target validation

Target | Observed counts | Missing | Unweighted positive rate | Binary validation
--- | ---: | ---: | ---: | ---
`account_fin` | `{'0': 514, '1': 537}` | 0 | 51.09% | PASS
`account_mob` | `{'0': 440, '1': 611}` | 0 | 58.14% | PASS

Rates above are unweighted audit statistics. The `wgt` field must be evaluated and used appropriately for population-representative descriptive analysis in later phases.

## Missingness

- Blank cells: **102,514 of 209,149** (49.01%)
- 100% missing columns (14): `fin11_0`, `fin11_1`, `fin11_2`, `fin11a`, `fin11b`, `fin11c`, `fin11d`, `fin11e`, `fin11f`, `fin36a`, `fin41a`, `con15`, `fin50`, `fin51`
- Columns with at least 50% missingness: **107**
- Columns with at least 75% missingness: **63**
- Columns with at least 90% missingness: **31**

Column | Missing count | Missing % | Non-missing unique values
--- | ---: | ---: | ---:
`con15` | 1051 | 100.00% | 0
`fin11_0` | 1051 | 100.00% | 0
`fin11_1` | 1051 | 100.00% | 0
`fin11_2` | 1051 | 100.00% | 0
`fin11a` | 1051 | 100.00% | 0
`fin11b` | 1051 | 100.00% | 0
`fin11c` | 1051 | 100.00% | 0
`fin11d` | 1051 | 100.00% | 0
`fin11e` | 1051 | 100.00% | 0
`fin11f` | 1051 | 100.00% | 0
`fin36a` | 1051 | 100.00% | 0
`fin41a` | 1051 | 100.00% | 0
`fin50` | 1051 | 100.00% | 0
`fin51` | 1051 | 100.00% | 0
`con13` | 1036 | 98.57% | 2
`fin34d` | 1030 | 98.00% | 3
`fin43d` | 1016 | 96.67% | 2
`fin22h` | 1013 | 96.38% | 4
`fin31c` | 1000 | 95.15% | 2
`con5` | 995 | 94.67% | 3
`con6` | 995 | 94.67% | 2
`con7` | 995 | 94.67% | 3
`con8` | 989 | 94.10% | 3
`fin22g` | 983 | 93.53% | 3
`fin43c` | 979 | 93.15% | 2
`con29` | 973 | 92.58% | 3
`fin31d` | 963 | 91.63% | 3
`fin13f_1` | 958 | 91.15% | 2
`fin34c` | 958 | 91.15% | 3
`fin39d` | 957 | 91.06% | 3
`fin39c` | 946 | 90.01% | 2
`con3` | 944 | 89.82% | 10
`fin27` | 939 | 89.34% | 5
`fin7` | 934 | 88.87% | 3
`con2a` | 933 | 88.77% | 4
`con2b` | 933 | 88.77% | 4
`con2c` | 933 | 88.77% | 4
`con2d` | 933 | 88.77% | 4
`con2e` | 933 | 88.77% | 3
`con2f` | 933 | 88.77% | 4
`con2g` | 933 | 88.77% | 3
`con4` | 933 | 88.77% | 4
`fin48a` | 922 | 87.73% | 4
`fin48b` | 922 | 87.73% | 4
`fin48c` | 922 | 87.73% | 4
`fin48d` | 922 | 87.73% | 4
`fin48e` | 922 | 87.73% | 4
`fin48f` | 922 | 87.73% | 4
`fin49a` | 922 | 87.73% | 4
`fin49b` | 922 | 87.73% | 4
`fin49c` | 922 | 87.73% | 4
`fin49d` | 922 | 87.73% | 4
`fin49e` | 922 | 87.73% | 4
`fin49f` | 922 | 87.73% | 4
`fin40` | 912 | 86.77% | 5
`fin41` | 912 | 86.77% | 3
`fin43a` | 901 | 85.73% | 3
`fin43b` | 901 | 85.73% | 2
`fin44` | 901 | 85.73% | 3
`fin25e3` | 834 | 79.35% | 4
`fin39a` | 815 | 77.55% | 2
`fin39b` | 815 | 77.55% | 3
`fin13_1` | 808 | 76.88% | 4
`fin22c` | 780 | 74.22% | 3
`fin35` | 769 | 73.17% | 3
`fin36` | 769 | 73.17% | 4
`con22` | 760 | 72.31% | 2
`con32` | 742 | 70.60% | 11
`fin14a` | 733 | 69.74% | 4
`fin14b` | 733 | 69.74% | 4
`fin14c` | 733 | 69.74% | 4
`fin14d` | 733 | 69.74% | 4
`fin14e` | 733 | 69.74% | 4
`fin15` | 733 | 69.74% | 4
`fin16` | 733 | 69.74% | 4
`con10` | 709 | 67.46% | 4
`con31a` | 700 | 66.60% | 4
`con31b` | 700 | 66.60% | 4
`con31c` | 700 | 66.60% | 4
`con31d` | 700 | 66.60% | 4
`con31e` | 700 | 66.60% | 4
`con31f` | 700 | 66.60% | 4
`con31g` | 700 | 66.60% | 4
`con31h` | 700 | 66.60% | 4
`fin24d3` | 696 | 66.22% | 4
`fin21` | 693 | 65.94% | 2
`fin33` | 679 | 64.61% | 3
`fin34a` | 679 | 64.61% | 3
`fin34b` | 679 | 64.61% | 3
`fin23` | 647 | 61.56% | 3
`fin17d` | 645 | 61.37% | 5
`fin17e` | 645 | 61.37% | 4
`fin17f` | 645 | 61.37% | 3
`fin24d1` | 583 | 55.47% | 3
`fin24d2` | 583 | 55.47% | 4
`fin10` | 571 | 54.33% | 4
`fin3` | 571 | 54.33% | 3
`fin4` | 571 | 54.33% | 4
`fin5` | 571 | 54.33% | 5
`fin6` | 571 | 54.33% | 5
`fin8` | 571 | 54.33% | 4
`fin9a` | 571 | 54.33% | 3
`fin9b` | 571 | 54.33% | 3
`con25` | 569 | 54.14% | 4
`fin28` | 564 | 53.66% | 2
`fin18` | 539 | 51.28% | 3
`con19` | 528 | 50.24% | 2

## Data types and coding patterns

- Inferred raw types: `{'integer': 181, 'string': 3, 'float': 1, 'empty': 14}`
- Exact 0/1 binary columns: **9**
- Constant non-missing columns: `year`, `economy`, `economycode`, `regionwb`, `pop_adult`, `urbanicity`
- Constant or fully empty columns: **20**
- Unique non-missing columns: `wpid_random`
- `female` and `emp_in` use observed 1/2 indicator coding; they must not be treated as Boolean 0/1 fields until labels are confirmed.
- Empty strings are treated as structural missingness. No non-empty textual missing markers were automatically recoded.
- Candidate special-code column/token pairs: **85**. The inventory includes possible numeric codes such as 8/9/97/98/99; these require dictionary-based confirmation in Phase 2.
- Many survey items use small integer code sets. `value_set_summary.csv` records the exact observed sets and affected columns; the codes must not be interpreted without the official variable definitions.

## Preliminary identifier and metadata review

Column | Preliminary role | Unique values | Missing % | Reason
--- | --- | ---: | ---: | ---
`year` | METADATA | 1 | 0.00% | Survey-year metadata; constant or near-constant in a single-wave extract.
`economy` | METADATA | 1 | 0.00% | Economy label metadata; expected to be constant in an Eswatini-only extract.
`economycode` | METADATA | 1 | 0.00% | Economy code metadata; expected to be constant in a single-economy extract.
`regionwb` | METADATA | 1 | 0.00% | World Bank region metadata; expected to be constant here.
`pop_adult` | METADATA | 1 | 0.00% | Population-level metadata, not a respondent characteristic.
`wpid_random` | IDENTIFIER | 1051 | 0.00% | Respondent identifier candidate; uniqueness must be checked.
`wgt` | METADATA | 567 | 0.00% | Survey weight; required for representative estimates but not an ordinary predictor.

This review is intentionally narrow. It is not the Phase 2 variable classification or feature-selection decision.

## Basic plausibility checks

Column | Check | Flagged | Status | Assumption
--- | --- | ---: | --- | ---
`age` | expected range 15 to 110 | 0 | PASS | Adult survey plausibility bound, not a recoding rule.
`inc_q` | expected range 1 to 5 | 0 | PASS | Expected income-quintile coding.
`account_fin` | expected range 0 to 1 | 0 | PASS | Required binary target.
`account_mob` | expected range 0 to 1 | 0 | PASS | Required binary target.
`wgt` | survey weight must be positive | 0 | PASS | Non-positive survey weights are not analytically usable.
`female` | observed indicator codes ['1', '2'] | 0 | PASS | Indicator code set is structurally plausible; semantic labels require the data dictionary.
`emp_in` | observed indicator codes ['1', '2'] | 0 | PASS | Indicator code set is structurally plausible; semantic labels require the data dictionary.

## Phase 1 risks and decisions

- The file contains many financial-behaviour variables alongside the targets. They are not automatically eligible predictors and create a high target-leakage risk for both future models.
- Survey item codes are numeric but are not necessarily continuous quantities. Phase 2 must use the real dictionary/metadata before assigning semantic types or missing codes.
- The survey weight needs a deliberate distinction between weighted population description and predictive model training/evaluation.
- `urbanicity` is constant (`1`) for all respondents, so this extract cannot support an urban-versus-rural comparison unless the coding or extract scope is clarified.
- One pair of rows has identical values after excluding only the unique respondent ID. This is a duplicate candidate, not proof of duplication, and no row was removed.
- Extensive missingness is likely influenced by questionnaire routing/skip logic; it must not be treated as random missingness without the data dictionary.
- Raw respondent microdata are kept local and Git-ignored pending a licensing/publication review.
- No value was removed, recoded, imputed, or transformed during this audit.

## Generated artifacts

- `audit_summary.json`: machine-readable audit summary
- `column_profile.csv`: one-row-per-column profile
- `value_set_summary.csv`: recurring low-cardinality coding patterns
- `special_code_inventory.csv`: possible textual and numeric special-response codes
- `data_quality_report.md`: this human-readable report
