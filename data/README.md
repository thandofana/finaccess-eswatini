# Data directory

- `raw/` contains the supplied source data and is treated as immutable.
- `reference/` contains local source documentation and metadata used to build the data dictionary.
- `processed/` contains the reproducibly generated Phase 3 datasets:
  - `model1_financial_inclusion.csv` — `account_fin` plus 16 approved predictors
  - `model2_mobile_money.csv` — `account_mob` plus 26 approved predictors

The raw, reference, and processed respondent-level data are ignored by Git pending a publication/licensing review. Generated reports contain aggregate schema, mappings, and quality information rather than respondent-level extracts.

The source CSV remains immutable. Recreate the processed files with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase3_preprocessing.ps1
```

The Phase 3 outputs contain no identifier, metadata, survey weight, parallel target, or post-outcome financial-behaviour fields. They are cleaned inputs, not final Phase 6 modelling matrices.
