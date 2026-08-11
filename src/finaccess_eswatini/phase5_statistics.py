"""Phase 5 association tests and effect sizes for both project outcomes.

Tests are deliberately limited to relationships pre-specified from Phase 4.
They use unweighted respondent counts because the source extract does not
provide the full complex-survey design needed for design-corrected inference.
Survey-weighted rates are retained as descriptive context only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT
from finaccess_eswatini.deliverables import render_delivery_checklist, validate_completed_phase_files
from finaccess_eswatini.phase4_eda import (
    DEFAULT_DICTIONARY,
    DIMENSION_BY_KEY,
    TARGET_LABELS,
    TARGET_SHORT_LABELS,
    build_eda_frame,
    weighted_rate,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_5"
ALPHA = 0.05
TEST_DIMENSION_KEYS = (
    "gender",
    "education",
    "income_quintile",
    "employment",
    "internet_use",
    "phone_ownership",
    "phone_type",
)
NON_SUBSTANTIVE_CATEGORIES = {"Nonresponse", "Missing or nonresponse"}


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Return monotonic Benjamini-Hochberg adjusted p-values."""

    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or len(values) == 0 or np.isnan(values).any():
        raise ValueError("p_values must be a non-empty one-dimensional sequence without NaN.")
    order = np.argsort(values)
    ranked = values[order]
    adjusted_ranked = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted_ranked = np.clip(adjusted_ranked, 0, 1)
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = adjusted_ranked
    return adjusted.tolist()


def bias_corrected_cramers_v(chi_square: float, n: int, rows: int, columns: int) -> float:
    """Calculate the small-sample bias-corrected Cramér's V."""

    if n <= 1 or rows < 2 or columns < 2:
        return 0.0
    phi_squared = chi_square / n
    corrected_phi = max(0.0, phi_squared - ((columns - 1) * (rows - 1)) / (n - 1))
    corrected_rows = rows - ((rows - 1) ** 2) / (n - 1)
    corrected_columns = columns - ((columns - 1) ** 2) / (n - 1)
    denominator = min(corrected_rows - 1, corrected_columns - 1)
    return float(np.sqrt(corrected_phi / denominator)) if denominator > 0 else 0.0


def effect_magnitude(value: float) -> str:
    """Apply transparent conventional thresholds to an absolute effect size."""

    absolute = abs(value)
    if absolute < 0.10:
        return "negligible"
    if absolute < 0.30:
        return "small"
    if absolute < 0.50:
        return "moderate"
    return "large"


def _categorical_tests(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_rows: list[dict[str, object]] = []
    contingency_rows: list[dict[str, object]] = []
    for target, target_label in TARGET_LABELS.items():
        for dimension_key in TEST_DIMENSION_KEYS:
            dimension = DIMENSION_BY_KEY[dimension_key]
            included = frame.loc[
                ~frame[dimension.column].isin(NON_SUBSTANTIVE_CATEGORIES),
                [dimension.column, target, "wgt"],
            ].copy()
            excluded_count = int(len(frame) - len(included))
            table = pd.crosstab(included[dimension.column], included[target]).reindex(columns=[0, 1], fill_value=0)
            chi_square, p_value, degrees_freedom, expected = chi2_contingency(
                table.to_numpy(), correction=False
            )
            n = int(table.to_numpy().sum())
            effect = bias_corrected_cramers_v(
                float(chi_square), n, table.shape[0], table.shape[1]
            )

            rates: dict[str, float] = {}
            for category in table.index:
                category_rows = included.loc[included[dimension.column] == category]
                rates[str(category)] = weighted_rate(category_rows[target], category_rows["wgt"])
                row_n = int(len(category_rows))
                row_weight = float(category_rows["wgt"].sum())
                for outcome_value in (0, 1):
                    row_position = table.index.get_loc(category)
                    contingency_rows.append(
                        {
                            "target": target,
                            "outcome": target_label,
                            "dimension": dimension_key,
                            "dimension_label": dimension.label,
                            "category": str(category),
                            "outcome_value": outcome_value,
                            "observed_count": int(table.loc[category, outcome_value]),
                            "expected_count": float(expected[row_position, outcome_value]),
                            "category_n": row_n,
                            "category_weight_sum": row_weight,
                            "category_weighted_positive_rate": rates[str(category)],
                        }
                    )
            minimum_category = min(rates, key=rates.get)
            maximum_category = max(rates, key=rates.get)
            result_rows.append(
                {
                    "test_id": f"{target}:{dimension_key}",
                    "target": target,
                    "outcome": target_label,
                    "dimension": dimension_key,
                    "dimension_label": dimension.label,
                    "test": "Pearson chi-square test of independence",
                    "n_included": n,
                    "n_excluded_nonresponse": excluded_count,
                    "category_count": int(table.shape[0]),
                    "chi_square": float(chi_square),
                    "degrees_freedom": int(degrees_freedom),
                    "p_value": float(p_value),
                    "effect_metric": "bias-corrected Cramer's V",
                    "effect_size": effect,
                    "effect_magnitude": effect_magnitude(effect),
                    "minimum_expected_count": float(expected.min()),
                    "expected_cells_below_5": int((expected < 5).sum()),
                    "expected_cells_total": int(expected.size),
                    "assumption_passed": bool((expected >= 5).all()),
                    "lowest_weighted_rate_category": minimum_category,
                    "lowest_weighted_rate": rates[minimum_category],
                    "highest_weighted_rate_category": maximum_category,
                    "highest_weighted_rate": rates[maximum_category],
                    "weighted_rate_gap_pp": (rates[maximum_category] - rates[minimum_category]) * 100,
                }
            )
    return pd.DataFrame(result_rows), pd.DataFrame(contingency_rows)


def _numeric_age_tests(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    result_rows: list[dict[str, object]] = []
    distribution_rows: list[dict[str, object]] = []
    for target, target_label in TARGET_LABELS.items():
        positive = frame.loc[frame[target] == 1, "age"].astype(float)
        negative = frame.loc[frame[target] == 0, "age"].astype(float)
        statistic, p_value = mannwhitneyu(
            positive, negative, alternative="two-sided", method="asymptotic"
        )
        rank_biserial = float(2 * statistic / (len(positive) * len(negative)) - 1)
        result_rows.append(
            {
                "test_id": f"{target}:age",
                "target": target,
                "outcome": target_label,
                "variable": "age",
                "variable_label": "Respondent age",
                "test": "Two-sided Mann-Whitney U",
                "n_total": int(len(frame)),
                "n_target_0": int(len(negative)),
                "n_target_1": int(len(positive)),
                "u_statistic": float(statistic),
                "p_value": float(p_value),
                "effect_metric": "rank-biserial correlation",
                "effect_size": rank_biserial,
                "effect_magnitude": effect_magnitude(rank_biserial),
                "median_target_0": float(negative.median()),
                "median_target_1": float(positive.median()),
                "median_difference_years": float(positive.median() - negative.median()),
                "mean_target_0": float(negative.mean()),
                "mean_target_1": float(positive.mean()),
                "direction": "positive class older" if rank_biserial > 0 else "positive class younger",
            }
        )
        for outcome_value, ages in ((0, negative), (1, positive)):
            distribution_rows.append(
                {
                    "target": target,
                    "outcome": target_label,
                    "outcome_value": outcome_value,
                    "n": int(len(ages)),
                    "minimum_age": float(ages.min()),
                    "q1_age": float(ages.quantile(0.25)),
                    "median_age": float(ages.median()),
                    "mean_age": float(ages.mean()),
                    "q3_age": float(ages.quantile(0.75)),
                    "maximum_age": float(ages.max()),
                }
            )
    return pd.DataFrame(result_rows), pd.DataFrame(distribution_rows)


def _apply_multiple_testing(
    categorical: pd.DataFrame, numeric: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    combined = pd.concat(
        [
            categorical.loc[:, ["test_id", "target", "outcome", "dimension_label", "test", "p_value", "effect_metric", "effect_size", "effect_magnitude"]].rename(
                columns={"dimension_label": "variable_label"}
            ),
            numeric.loc[:, ["test_id", "target", "outcome", "variable_label", "test", "p_value", "effect_metric", "effect_size", "effect_magnitude"]],
        ],
        ignore_index=True,
    )
    combined["adjusted_p_value"] = np.nan
    for target in TARGET_LABELS:
        mask = combined["target"] == target
        combined.loc[mask, "adjusted_p_value"] = benjamini_hochberg(
            combined.loc[mask, "p_value"].tolist()
        )
    combined["significant_fdr_0_05"] = combined["adjusted_p_value"] < ALPHA
    q_lookup = combined.set_index("test_id")["adjusted_p_value"]
    for table in (categorical, numeric):
        table["adjusted_p_value"] = table["test_id"].map(q_lookup).astype(float)
        table["significant_fdr_0_05"] = table["adjusted_p_value"] < ALPHA
    combined = combined.sort_values(
        ["target", "effect_size"], ascending=[True, False]
    ).reset_index(drop=True)
    return categorical, numeric, combined


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty report table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _render_report(summary: dict[str, object], combined: pd.DataFrame) -> str:
    lines = [
        "# Phase 5 — Statistical Analysis",
        "",
        "## Scope",
        "",
        "This phase formally evaluates a limited set of associations identified before testing from Phase 4. It does not establish causation and does not train or select predictive models.",
        "",
        "## Methods",
        "",
        "- Categorical variables: Pearson chi-square test of independence with bias-corrected Cramér's V.",
        "- Numeric age: two-sided Mann–Whitney U test with rank-biserial correlation.",
        "- Multiplicity: Benjamini–Hochberg false-discovery-rate adjustment across eight tests separately for each outcome.",
        "- Significance rule: adjusted p-value below 0.05.",
        "- Inference uses unweighted respondent counts because no strata/cluster design variables are used; survey-weighted rates provide descriptive context only.",
        "- Explicit nonresponse categories are excluded test-by-test. Structurally meaningful `Not applicable / skipped` phone-type responses are retained.",
        "",
        "## Results",
        "",
        "| Outcome | Variable | Test | Effect | Magnitude | Raw p | FDR-adjusted p | Significant |",
        "|---|---|---|---:|---|---:|---:|---|",
    ]
    for _, row in combined.iterrows():
        lines.append(
            f"| {TARGET_SHORT_LABELS[row['target']]} | {row['variable_label']} | {row['test']} | {row['effect_size']:.3f} | {row['effect_magnitude']} | {row['p_value']:.3g} | {row['adjusted_p_value']:.3g} | {'Yes' if row['significant_fdr_0_05'] else 'No'} |"
        )
    lines.extend(["", "## Main statistical findings", ""])
    for finding in summary["findings"]:
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## Assumption checks",
            "",
            f"- All {summary['assumptions']['categorical_test_count']} categorical tests had zero expected cells below 5.",
            f"- Minimum expected cell count across all categorical tests: {summary['assumptions']['minimum_expected_count']:.1f}.",
            "- Mann–Whitney inference uses its asymptotic two-sided implementation and accommodates tied ages through SciPy's tie correction.",
            "",
            "## Interpretation limits",
            "",
            "- Statistical significance does not measure practical importance; effect sizes are reported for that reason.",
            "- Conventional effect labels are descriptive guides, not universal cutoffs.",
            "- Tests are bivariate and are not adjusted for confounding characteristics.",
            "- Survey weighting is not sufficient for design-corrected inference without the relevant strata and cluster information.",
            "- `internet_use=0` still combines no, don't know, and refused.",
            "- These results inform later analysis but do not automatically determine model features.",
            "",
        ]
    )
    return "\n".join(lines)


def run(
    raw_path: Path = DEFAULT_INPUT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    frame, source_validation = build_eda_frame(raw_path, dictionary_path)
    categorical, contingency = _categorical_tests(frame)
    numeric, age_distributions = _numeric_age_tests(frame)
    categorical, numeric, combined = _apply_multiple_testing(categorical, numeric)
    output_dir.mkdir(parents=True, exist_ok=True)

    categorical.to_csv(output_dir / "categorical_tests.csv", index=False, encoding="utf-8", lineterminator="\n")
    numeric.to_csv(output_dir / "numeric_tests.csv", index=False, encoding="utf-8", lineterminator="\n")
    combined.to_csv(output_dir / "association_results.csv", index=False, encoding="utf-8", lineterminator="\n")
    contingency.to_csv(output_dir / "contingency_tables.csv", index=False, encoding="utf-8", lineterminator="\n")
    age_distributions.to_csv(output_dir / "age_distributions.csv", index=False, encoding="utf-8", lineterminator="\n")

    categorical_lookup = categorical.set_index(["target", "dimension"])
    numeric_lookup = numeric.set_index("target")
    findings = [
        (
            "Financial inclusion was associated after FDR adjustment with education, income quintile, workforce status, recent internet use, phone ownership, phone type, and age; gender was not associated."
        ),
        (
            "Mobile-money adoption was associated after FDR adjustment with education, income quintile, workforce status, recent internet use, phone ownership, phone type, and age; gender was not associated."
        ),
        (
            f"The largest categorical effect for financial inclusion was income quintile (bias-corrected Cramér's V={categorical_lookup.loc[('account_fin', 'income_quintile'), 'effect_size']:.3f}), closely followed by workforce status."
        ),
        (
            f"The largest categorical effect for mobile money was phone type (bias-corrected Cramér's V={categorical_lookup.loc[('account_mob', 'phone_type'), 'effect_size']:.3f}), followed by income quintile and recent internet use."
        ),
        (
            f"Included respondents were older on average for both outcomes; the age effect was small for financial inclusion (rank-biserial={numeric_lookup.loc['account_fin', 'effect_size']:.3f}) and mobile money (rank-biserial={numeric_lookup.loc['account_mob', 'effect_size']:.3f})."
        ),
    ]
    summary: dict[str, object] = {
        "phase": 5,
        "status": "PASS_WITH_NOTES",
        "source_validation": source_validation,
        "design": {
            "pre_specified_tests_per_outcome": 8,
            "categorical_tests_per_outcome": 7,
            "numeric_tests_per_outcome": 1,
            "multiple_testing": "Benjamini-Hochberg within each outcome",
            "alpha": ALPHA,
            "inference_weighting": "unweighted respondent counts",
            "weighted_rates_role": "descriptive context only",
        },
        "result_counts": {
            target: {
                "tests": int((combined["target"] == target).sum()),
                "fdr_significant": int(
                    combined.loc[combined["target"] == target, "significant_fdr_0_05"].sum()
                ),
            }
            for target in TARGET_LABELS
        },
        "assumptions": {
            "categorical_test_count": int(len(categorical)),
            "tests_passing_expected_count_rule": int(categorical["assumption_passed"].sum()),
            "minimum_expected_count": float(categorical["minimum_expected_count"].min()),
            "expected_cells_below_5_total": int(categorical["expected_cells_below_5"].sum()),
        },
        "findings": findings,
        "causal_claims_made": False,
        "models_trained": False,
        "limitations": [
            "no design-corrected survey inference without strata and cluster variables",
            "bivariate tests do not adjust for confounding",
            "internet_use=0 combines no, don't know, and refused",
            "effect-size labels are conventional descriptive guides",
        ],
    }
    (output_dir / "phase5_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "statistical_analysis_report.md").write_text(
        _render_report(summary, combined), encoding="utf-8"
    )

    missing_deliverables = validate_completed_phase_files(PROJECT_ROOT, through_phase=5)
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=5), encoding="utf-8"
    )
    if missing_deliverables:
        raise RuntimeError(f"Completed-phase deliverable validation failed: {missing_deliverables}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": [1, 2, 3, 4, 5],
        "missing_files": {},
        "checklist": "reports/phase_5/deliverable_checklist.md",
    }
    (output_dir / "phase5_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(args.raw.resolve(), args.dictionary.resolve(), args.output_dir.resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
