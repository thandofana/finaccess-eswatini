# Completed-Phase Deliverable Checklist

This checklist covers every completed phase. A missing required file causes validation to fail.

## Phase 1

- ✅ `notebooks/01_data_understanding.ipynb`
- ✅ `src/finaccess_eswatini/data_audit.py`
- ✅ `scripts/run_phase1_audit.ps1`
- ✅ `reports/phase_1/audit_summary.json`
- ✅ `reports/phase_1/column_profile.csv`
- ✅ `reports/phase_1/value_set_summary.csv`
- ✅ `reports/phase_1/special_code_inventory.csv`
- ✅ `reports/phase_1/data_quality_report.md`

## Phase 2

- ✅ `notebooks/02_data_dictionary_feature_eligibility.ipynb`
- ✅ `src/finaccess_eswatini/phase2_dictionary.py`
- ✅ `scripts/run_phase2_dictionary.ps1`
- ✅ `reports/phase_2/data_dictionary.csv`
- ✅ `reports/phase_2/feature_eligibility.csv`
- ✅ `reports/phase_2/candidate_features_model1.csv`
- ✅ `reports/phase_2/candidate_features_model2.csv`
- ✅ `reports/phase_2/feature_blueprint.md`
- ✅ `reports/phase_2/leakage_review.md`
- ✅ `reports/phase_2/target_review.md`
- ✅ `reports/phase_2/source_notes.md`
- ✅ `reports/phase_2/phase2_summary.json`
- ✅ `reports/phase_2/phase2_summary.md`

## Phase 3

- ✅ `notebooks/03_data_cleaning_preprocessing.ipynb`
- ✅ `src/finaccess_eswatini/feature_config.py`
- ✅ `src/finaccess_eswatini/phase3_preprocessing.py`
- ✅ `src/finaccess_eswatini/preprocessing/cleaning.py`
- ✅ `src/finaccess_eswatini/preprocessing/pipelines.py`
- ✅ `scripts/run_phase3_preprocessing.ps1`
- ✅ `scripts/run_tests.ps1`
- ✅ `scripts/execute_notebooks.py`
- ✅ `scripts/execute_notebooks.ps1`
- ✅ `requirements-lock.txt`
- ✅ `tests/test_notebook_outputs.py`
- ✅ `tests/test_phase3_preprocessing.py`
- ✅ `tests/test_project_structure.py`
- ✅ `reports/phase_3/phase3_summary.json`
- ✅ `reports/phase_3/phase3_summary.md`
- ✅ `reports/phase_3/preprocessing_spec.json`
- ✅ `reports/phase_3/category_mappings.csv`
- ✅ `reports/phase_3/processed_schema_model1.csv`
- ✅ `reports/phase_3/processed_schema_model2.csv`
- ✅ `data/processed/model1_financial_inclusion.csv`
- ✅ `data/processed/model2_mobile_money.csv`

## Phase 4

- ✅ `notebooks/04_exploratory_analysis.ipynb`
- ✅ `src/finaccess_eswatini/phase4_eda.py`
- ✅ `scripts/run_phase4_eda.ps1`
- ✅ `tests/test_phase4_eda.py`
- ✅ `reports/phase_4/eda_summary.json`
- ✅ `reports/phase_4/eda_report.md`
- ✅ `reports/phase_4/overall_rates.csv`
- ✅ `reports/phase_4/subgroup_rates.csv`
- ✅ `reports/phase_4/chart_manifest.csv`
- ✅ `reports/phase_4/figures/01_overall_access_rates.png`
- ✅ `reports/phase_4/figures/01_overall_access_rates.svg`
- ✅ `reports/phase_4/figures/02_demographic_patterns.png`
- ✅ `reports/phase_4/figures/02_demographic_patterns.svg`
- ✅ `reports/phase_4/figures/03_socioeconomic_patterns.png`
- ✅ `reports/phase_4/figures/03_socioeconomic_patterns.svg`
- ✅ `reports/phase_4/figures/04_digital_access_patterns.png`
- ✅ `reports/phase_4/figures/04_digital_access_patterns.svg`

## Phase 5

- ✅ `notebooks/05_statistical_analysis.ipynb`
- ✅ `src/finaccess_eswatini/phase5_statistics.py`
- ✅ `scripts/run_phase5_statistics.ps1`
- ✅ `tests/test_phase5_statistics.py`
- ✅ `reports/phase_5/categorical_tests.csv`
- ✅ `reports/phase_5/numeric_tests.csv`
- ✅ `reports/phase_5/association_results.csv`
- ✅ `reports/phase_5/contingency_tables.csv`
- ✅ `reports/phase_5/age_distributions.csv`
- ✅ `reports/phase_5/phase5_summary.json`
- ✅ `reports/phase_5/statistical_analysis_report.md`

## Phase 6

- ✅ `notebooks/06_feature_engineering.ipynb`
- ✅ `src/finaccess_eswatini/phase6_feature_engineering.py`
- ✅ `scripts/run_phase6_feature_engineering.ps1`
- ✅ `tests/test_phase6_feature_engineering.py`
- ✅ `reports/phase_6/feature_engineering_review.csv`
- ✅ `reports/phase_6/final_feature_manifest.csv`
- ✅ `reports/phase_6/engineered_feature_distributions.csv`
- ✅ `reports/phase_6/transformation_spec.json`
- ✅ `reports/phase_6/phase6_summary.json`
- ✅ `reports/phase_6/feature_engineering_report.md`
- ✅ `reports/phase_6/figures/01_engineered_feature_distributions.png`
- ✅ `reports/phase_6/figures/01_engineered_feature_distributions.svg`
- ✅ `data/processed/model1_financial_inclusion_final.csv`
- ✅ `data/processed/model2_mobile_money_final.csv`

## Phase 7

- ✅ `notebooks/07_financial_inclusion_model.ipynb`
- ✅ `src/finaccess_eswatini/phase7_model1.py`
- ✅ `scripts/run_phase7_model1.ps1`
- ✅ `tests/test_phase7_model1.py`
- ✅ `reports/phase_7/model_comparison.csv`
- ✅ `reports/phase_7/cv_search_results.csv`
- ✅ `reports/phase_7/cv_fold_audit.csv`
- ✅ `reports/phase_7/holdout_metrics.csv`
- ✅ `reports/phase_7/confusion_matrix.csv`
- ✅ `reports/phase_7/calibration_curve.csv`
- ✅ `reports/phase_7/bootstrap_intervals.csv`
- ✅ `reports/phase_7/test_category_coverage.csv`
- ✅ `reports/phase_7/phase7_summary.json`
- ✅ `reports/phase_7/model1_report.md`
- ✅ `reports/phase_7/figures/01_model_comparison.png`
- ✅ `reports/phase_7/figures/01_model_comparison.svg`
- ✅ `reports/phase_7/figures/02_holdout_evaluation.png`
- ✅ `reports/phase_7/figures/02_holdout_evaluation.svg`
- ✅ `models/model1_financial_inclusion_pipeline.joblib`
- ✅ `models/model1_financial_inclusion_metadata.json`

## Phase 8

- ✅ `notebooks/08_mobile_money_model.ipynb`
- ✅ `src/finaccess_eswatini/phase8_model2.py`
- ✅ `scripts/run_phase8_model2.ps1`
- ✅ `tests/test_phase8_model2.py`
- ✅ `reports/phase_8/model_comparison.csv`
- ✅ `reports/phase_8/cv_search_results.csv`
- ✅ `reports/phase_8/cv_fold_audit.csv`
- ✅ `reports/phase_8/holdout_metrics.csv`
- ✅ `reports/phase_8/confusion_matrix.csv`
- ✅ `reports/phase_8/calibration_curve.csv`
- ✅ `reports/phase_8/bootstrap_intervals.csv`
- ✅ `reports/phase_8/test_category_coverage.csv`
- ✅ `reports/phase_8/phase8_summary.json`
- ✅ `reports/phase_8/model2_report.md`
- ✅ `reports/phase_8/figures/01_model_comparison.png`
- ✅ `reports/phase_8/figures/01_model_comparison.svg`
- ✅ `reports/phase_8/figures/02_holdout_evaluation.png`
- ✅ `reports/phase_8/figures/02_holdout_evaluation.svg`
- ✅ `models/model2_mobile_money_pipeline.joblib`
- ✅ `models/model2_mobile_money_metadata.json`

## Phase 9

- ✅ `notebooks/09_model_explainability.ipynb`
- ✅ `src/finaccess_eswatini/phase9_explainability.py`
- ✅ `scripts/run_phase9_explainability.ps1`
- ✅ `tests/test_phase9_explainability.py`
- ✅ `reports/phase_9/global_shap_importance.csv`
- ✅ `reports/phase_9/encoded_shap_importance.csv`
- ✅ `reports/phase_9/native_feature_importance.csv`
- ✅ `reports/phase_9/individual_explanations.csv`
- ✅ `reports/phase_9/additivity_validation.csv`
- ✅ `reports/phase_9/phase9_summary.json`
- ✅ `reports/phase_9/explainability_report.md`
- ✅ `reports/phase_9/figures/01_global_shap_importance.png`
- ✅ `reports/phase_9/figures/01_global_shap_importance.svg`
- ✅ `reports/phase_9/figures/02_individual_explanations.png`
- ✅ `reports/phase_9/figures/02_individual_explanations.svg`
- ✅ `models/model1_shap_explainer.joblib`
- ✅ `models/model2_shap_explainer.joblib`

## Phase 10

- ✅ `notebooks/10_prediction_api.ipynb`
- ✅ `api/app/main.py`
- ✅ `api/app/schemas.py`
- ✅ `api/app/service.py`
- ✅ `api/examples/assessment_request.json`
- ✅ `api/examples/assessment_response.json`
- ✅ `api/README.md`
- ✅ `src/finaccess_eswatini/phase10_api_validation.py`
- ✅ `scripts/run_phase10_api.ps1`
- ✅ `scripts/start_api.ps1`
- ✅ `tests/test_phase10_api.py`
- ✅ `reports/phase_10/endpoint_contract.json`
- ✅ `reports/phase_10/validation_cases.csv`
- ✅ `reports/phase_10/phase10_summary.json`
- ✅ `reports/phase_10/api_report.md`

## Phase 11

- ✅ `notebooks/11_web_application.ipynb`
- ✅ `OPEN_DESIGN_REVIEW.cmd`
- ✅ `design_review/index.html`
- ✅ `design_review/ledger.html`
- ✅ `design_review/open-field.html`
- ✅ `design_review/signal.html`
- ✅ `frontend/web/app/page.tsx`
- ✅ `frontend/web/app/concepts/[concept]/page.tsx`
- ✅ `frontend/web/app/components/FinAccessExperience.tsx`
- ✅ `frontend/web/app/components/Assessment.tsx`
- ✅ `frontend/web/app/globals.css`
- ✅ `frontend/web/public/og.png`
- ✅ `frontend/web/tests/rendered-html.test.mjs`
- ✅ `frontend/README.md`
- ✅ `src/finaccess_eswatini/phase11_frontend_validation.py`
- ✅ `scripts/run_phase11_frontend.ps1`
- ✅ `scripts/review_phase11_designs.ps1`
- ✅ `scripts/stop_phase11_review.ps1`
- ✅ `scripts/build_offline_design_review.py`
- ✅ `tests/test_phase11_frontend.py`
- ✅ `reports/phase_11/concept_comparison.md`
- ✅ `reports/phase_11/frontend_validation.json`
- ✅ `reports/phase_11/phase11_summary.json`
- ✅ `reports/phase_11/web_application_report.md`

## Result

**PASS** — all required files through Phase 11 are present.
