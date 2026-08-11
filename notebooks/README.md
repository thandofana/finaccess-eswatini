# Analytical notebooks

Notebooks are added, executed, and validated phase by phase. They are concise portfolio entry points backed by reusable code in `src/finaccess_eswatini/`; business logic is not duplicated inside notebooks. Saved outputs are committed inside each notebook so tables, findings, and analytical graphs are visible immediately in GitHub and Jupyter.

Re-execute and persist every completed notebook with `scripts/execute_notebooks.ps1`.

| Notebook | Project phase | Purpose | Status |
|---|---:|---|---|
| `01_data_understanding.ipynb` | 1 | Reproduce the raw-data audit and inspect the highest-missingness fields | Complete |
| `02_data_dictionary_feature_eligibility.ipynb` | 2 | Reproduce the full dictionary and compare the two leakage-reviewed feature sets | Complete |
| `03_data_cleaning_preprocessing.ipynb` | 3 | Reproduce model-specific cleaned datasets and inspect the unfitted preprocessing contracts | Complete |
| `04_exploratory_analysis.ipynb` | 4 | Reproduce weighted/unweighted EDA tables, charts, and question-driven findings | Complete |
| `05_statistical_analysis.ipynb` | 5 | Reproduce association tests, FDR-adjusted p-values, effect sizes, and assumption checks | Complete |
| `06_feature_engineering.ipynb` | 6 | Reproduce leakage-safe transformations, final feature blueprints, and engineered-feature coverage | Complete |
| `07_financial_inclusion_model.ipynb` | 7 | Reproduce group-aware Model 1 tuning, selection, protected-holdout evaluation, and calibration diagnostics | Complete |
| `08_mobile_money_model.ipynb` | 8 | Reproduce independent Model 2 tuning, selection, protected-holdout evaluation, and Model 1 integrity checks | Complete |
| `09_model_explainability.ipynb` | 9 | Reproduce global and individual SHAP explanations, source-feature aggregation, and faithfulness checks for both models | Complete |
| `10_prediction_api.ipynb` | 10 | Exercise API health, combined prediction, explanation output, structured rejection, and OpenAPI documentation | Complete |
| `11_web_application.ipynb` | 11 | Document the three frontend directions, shared product contract, saved validation checks, and generated social preview | Complete |
| `12_deployment.ipynb` | 12 | Validate the public Vercel frontend, same-origin API, artifact integrity, prediction equivalence, and publication safety | Complete |
| `13_portfolio_polish.ipynb` | 13 | Present final model results, fresh live-product screenshots, portfolio evidence, and responsible-use boundaries | Complete |

The approved 13-phase roadmap is complete. Any future notebook should correspond to a separately approved extension rather than silently changing the validated workflow.
