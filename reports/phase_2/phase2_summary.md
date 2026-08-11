# Phase 2 Data Dictionary and Eligibility Summary

- Variables documented: **199**
- Primary categories: `{"DEMOGRAPHIC": 3, "DIGITAL": 53, "FINANCIAL": 114, "IDENTIFIER": 1, "IDENTITY": 16, "METADATA": 6, "SOCIOECONOMIC": 4, "TARGET": 2}`
- Model 1 candidates: **16**
- Model 2 candidates: **26**
- Variables at least 50% missing: **107**
- All-missing variables: **14**

The complete row-level decisions are in `data_dictionary.csv` and `feature_eligibility.csv`. Every variable has a category, coverage record, source URL, Model 1 decision, Model 2 decision, leakage rating, and reason.

## Source and scope decisions

- World Bank reference: `SWZ_2024_FINDEX_v02_M`
- The 2024 survey year is confirmed by the DDI and dataset, while the publication/database edition is Global Findex 2025.
- The CSV variable `internet_use` corresponds to `internet` in the PDF codebook; the DDI uses `internet_use`, confirming the file-specific name.
- Raw microdata and source PDFs/XML remain Git-ignored under the Microdata Library terms.
- No modelling or Phase 3 data cleaning was performed.
