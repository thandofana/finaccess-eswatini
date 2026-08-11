"""Question-driven Phase 4 exploratory analysis for both project outcomes.

This module produces descriptive weighted and unweighted summaries plus static
figures. It deliberately performs no hypothesis tests, feature selection,
model fitting, or causal analysis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT
from finaccess_eswatini.deliverables import render_delivery_checklist, validate_completed_phase_files
from finaccess_eswatini.preprocessing import clean_model_frame, load_data_dictionary, read_raw_data


DEFAULT_DICTIONARY = PROJECT_ROOT / "reports" / "phase_2" / "data_dictionary.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_4"
DEFAULT_FIGURE_DIR = DEFAULT_OUTPUT_DIR / "figures"
RAW_DATA_SHA256 = "4968eaa568df1ddf8d5fadea39f4797d1bdecc2c3f941546936a200ce4bc210c"

TARGET_LABELS = {
    "account_fin": "Financial institution account",
    "account_mob": "Mobile money account",
}
TARGET_SHORT_LABELS = {
    "account_fin": "Financial inclusion",
    "account_mob": "Mobile money",
}
TARGET_COLORS = {
    "account_fin": "#0F6B78",
    "account_mob": "#D17A22",
}

NON_SUBSTANTIVE_CATEGORIES = {"Nonresponse", "Missing or nonresponse"}
INTERNET_ZERO_LABEL = "No / don't know / refused"


@dataclass(frozen=True)
class Dimension:
    key: str
    column: str
    label: str
    question: str
    order: tuple[str, ...]


DIMENSIONS = (
    Dimension(
        "gender",
        "female",
        "Gender",
        "Do financial-access outcomes differ by gender in the observed data?",
        ("Female", "Male"),
    ),
    Dimension(
        "age_group",
        "age_group",
        "Age group",
        "How do financial inclusion and mobile-money adoption vary across age groups?",
        ("15–24", "25–34", "35–44", "45–54", "55–64", "65+"),
    ),
    Dimension(
        "education",
        "educ",
        "Education",
        "How do outcomes vary by education level?",
        (
            "Primary education or less",
            "Secondary education",
            "Tertiary education or more",
            "Missing or nonresponse",
        ),
    ),
    Dimension(
        "income_quintile",
        "inc_q",
        "Household income quintile",
        "How do outcomes vary across within-economy income quintiles?",
        tuple(f"Income quintile {value}" for value in range(1, 6)),
    ),
    Dimension(
        "employment",
        "emp_in",
        "Workforce status",
        "Do outcomes differ by workforce participation?",
        ("In the workforce", "Out of the workforce"),
    ),
    Dimension(
        "internet_use",
        "internet_use",
        "Recent internet use",
        "How are financial-access outcomes associated with recent internet use?",
        ("Yes", INTERNET_ZERO_LABEL),
    ),
    Dimension(
        "phone_ownership",
        "con1",
        "Mobile phone ownership",
        "How are outcomes associated with mobile phone ownership?",
        ("Yes", "No", "Nonresponse"),
    ),
    Dimension(
        "phone_type",
        "con9",
        "Phone type",
        "How do outcomes vary by the respondent's available phone type?",
        (
            "A smartphone",
            "A basic text phone",
            "Not applicable / skipped",
            "Nonresponse",
        ),
    ),
)

DIMENSION_BY_KEY = {dimension.key: dimension for dimension in DIMENSIONS}

SHORT_CATEGORY_LABELS = {
    "Primary education or less": "Primary or less",
    "Secondary education": "Secondary",
    "Tertiary education or more": "Tertiary or more",
    "Income quintile 1": "Quintile 1",
    "Income quintile 2": "Quintile 2",
    "Income quintile 3": "Quintile 3",
    "Income quintile 4": "Quintile 4",
    "Income quintile 5": "Quintile 5",
    "No / don't know / refused": "No / DK / refused",
    "A smartphone": "Smartphone",
    "A basic text phone": "Basic text phone",
    "Not applicable / skipped": "No phone / skipped",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def weighted_rate(outcome: pd.Series, weights: pd.Series) -> float:
    denominator = float(weights.sum())
    if denominator <= 0:
        raise ValueError("Survey weights must sum to a positive value.")
    return float((outcome.astype(float) * weights.astype(float)).sum() / denominator)


def build_eda_frame(
    raw_path: Path = DEFAULT_INPUT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build an in-memory descriptive frame while preserving the raw row order."""

    source_hash = file_hash(raw_path)
    if source_hash != RAW_DATA_SHA256:
        raise ValueError(f"Raw data hash changed: expected {RAW_DATA_SHA256}, found {source_hash}")
    raw = read_raw_data(raw_path)
    dictionary = load_data_dictionary(dictionary_path)
    model1 = clean_model_frame(raw, dictionary, "model1")
    model2 = clean_model_frame(raw, dictionary, "model2")
    if not model1.index.equals(model2.index) or not model1.index.equals(raw.index):
        raise ValueError("Phase 4 inputs are not aligned in the original respondent order.")

    weights = pd.to_numeric(raw["wgt"], errors="raise").astype(float)
    if weights.isna().any() or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("wgt must be complete, finite, and strictly positive.")

    base = model2.loc[:, [*model2.columns]].copy()
    base.insert(0, "account_fin", model1["account_fin"].astype("int8"))
    base["wgt"] = weights
    base["age_group"] = pd.cut(
        base["age"],
        bins=[14, 24, 34, 44, 54, 64, np.inf],
        labels=list(DIMENSION_BY_KEY["age_group"].order),
        right=True,
        ordered=True,
    )
    if base["age_group"].isna().any():
        raise ValueError("Age grouping left one or more respondents unclassified.")

    validation = {
        "source_sha256": source_hash,
        "rows": int(len(base)),
        "weight_count": int(weights.count()),
        "weight_missing": int(weights.isna().sum()),
        "weight_nonpositive": int((weights <= 0).sum()),
        "weight_min": float(weights.min()),
        "weight_max": float(weights.max()),
        "weight_sum": float(weights.sum()),
    }
    return base, validation


def build_overall_rates(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for target, outcome_label in TARGET_LABELS.items():
        weighted = weighted_rate(frame[target], frame["wgt"])
        unweighted = float(frame[target].mean())
        rows.append(
            {
                "target": target,
                "outcome": outcome_label,
                "n": int(len(frame)),
                "positive_count": int(frame[target].sum()),
                "weight_sum": float(frame["wgt"].sum()),
                "weighted_rate": weighted,
                "unweighted_rate": unweighted,
                "weighted_minus_unweighted_pp": (weighted - unweighted) * 100,
            }
        )
    return pd.DataFrame(rows)


def build_subgroup_rates(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dimension in DIMENSIONS:
        available = set(frame[dimension.column].astype("string").unique().tolist())
        unexpected = sorted(available - set(dimension.order))
        if unexpected:
            raise ValueError(f"Unexpected categories for {dimension.key}: {unexpected}")
        for target, outcome_label in TARGET_LABELS.items():
            for order, category in enumerate(dimension.order, start=1):
                group = frame.loc[frame[dimension.column].astype("string") == category]
                if group.empty:
                    continue
                rows.append(
                    {
                        "target": target,
                        "outcome": outcome_label,
                        "dimension": dimension.key,
                        "dimension_label": dimension.label,
                        "question": dimension.question,
                        "category_order": order,
                        "category": category,
                        "n": int(len(group)),
                        "positive_count": int(group[target].sum()),
                        "weight_sum": float(group["wgt"].sum()),
                        "weighted_positive": float((group[target] * group["wgt"]).sum()),
                        "weighted_rate": weighted_rate(group[target], group["wgt"]),
                        "unweighted_rate": float(group[target].mean()),
                        "chart_eligible": bool(
                            len(group) >= 10 and category not in NON_SUBSTANTIVE_CATEGORIES
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _apply_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#263A43",
            "text.color": "#263A43",
            "xtick.color": "#50636C",
            "ytick.color": "#263A43",
            "axes.edgecolor": "#C7D1D6",
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "finaccess-eswatini-phase4",
        }
    )


def _save_figure(fig: plt.Figure, figure_dir: Path, stem: str) -> list[Path]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs = [figure_dir / f"{stem}.png", figure_dir / f"{stem}.svg"]
    fig.savefig(
        outputs[0],
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": "FinAccess Eswatini Phase 4"},
    )
    fig.savefig(
        outputs[1],
        bbox_inches="tight",
        facecolor="white",
        metadata={"Date": None, "Creator": "FinAccess Eswatini Phase 4"},
    )
    plt.close(fig)
    return outputs


def _format_percent_axis(ax: plt.Axes) -> None:
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    ax.grid(axis="x", color="#DDE4E7", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#C7D1D6")


def plot_overall_rates(overall: pd.DataFrame, figure_dir: Path) -> list[Path]:
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ordered = overall.set_index("target").loc[["account_fin", "account_mob"]].reset_index()
    y = np.arange(len(ordered))
    weighted = ordered["weighted_rate"].to_numpy() * 100
    unweighted = ordered["unweighted_rate"].to_numpy() * 100
    colors = [TARGET_COLORS[target] for target in ordered["target"]]
    bars = ax.barh(y, weighted, height=0.48, color=colors)
    ax.scatter(unweighted, y, marker="D", s=55, color="#263A43", zorder=4)
    for bar, value in zip(bars, weighted, strict=True):
        ax.text(value + 1.2, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontweight="bold")
    for x_value, y_value in zip(unweighted, y, strict=True):
        ax.text(x_value + 1.2, y_value + 0.21, f"{x_value:.1f}% sample", va="bottom", color="#50636C", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels([TARGET_SHORT_LABELS[target] for target in ordered["target"]])
    ax.invert_yaxis()
    _format_percent_axis(ax)
    ax.set_title("Survey weighting lowers both national access estimates")
    ax.set_xlabel("Share of adults")
    fig.text(0.01, 0.01, "Weighted estimates use wgt; diamonds show raw sample proportions. n = 1,051.", fontsize=9, color="#50636C")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return _save_figure(fig, figure_dir, "01_overall_access_rates")


def _plot_dimension_panels(
    subgroup: pd.DataFrame,
    dimension_keys: Sequence[str],
    title: str,
    note: str,
    figure_dir: Path,
    stem: str,
) -> list[Path]:
    _apply_plot_style()
    fig, axes = plt.subplots(1, len(dimension_keys), figsize=(5.2 * len(dimension_keys), 6.4), sharex=True)
    if len(dimension_keys) == 1:
        axes = [axes]
    handles = None
    labels = None
    for ax, key in zip(axes, dimension_keys, strict=True):
        dimension = DIMENSION_BY_KEY[key]
        panel = subgroup.loc[(subgroup["dimension"] == key) & subgroup["chart_eligible"]].copy()
        pivot = panel.pivot(index="category", columns="target", values="weighted_rate")
        categories = [category for category in dimension.order if category in pivot.index]
        pivot = pivot.loc[categories]
        y = np.arange(len(categories))
        height = 0.34
        fin = pivot["account_fin"].to_numpy() * 100
        mob = pivot["account_mob"].to_numpy() * 100
        bars_fin = ax.barh(y - height / 2, fin, height=height, color=TARGET_COLORS["account_fin"], label="Financial inclusion")
        bars_mob = ax.barh(y + height / 2, mob, height=height, color=TARGET_COLORS["account_mob"], label="Mobile money")
        for bars in (bars_fin, bars_mob):
            for bar in bars:
                value = bar.get_width()
                ax.text(value + 0.8, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontsize=8.5)
        ax.set_yticks(y)
        ax.set_yticklabels([SHORT_CATEGORY_LABELS.get(category, category) for category in categories])
        ax.invert_yaxis()
        ax.set_title(dimension.label)
        _format_percent_axis(ax)
        handles, labels = ax.get_legend_handles_labels()
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)
    if handles and labels:
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=2, frameon=False)
    fig.text(0.01, 0.01, note, fontsize=9, color="#50636C")
    fig.tight_layout(rect=(0, 0.05, 1, 0.89), w_pad=2.5)
    return _save_figure(fig, figure_dir, stem)


def create_figures(overall: pd.DataFrame, subgroup: pd.DataFrame, figure_dir: Path) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    figure_specs = [
        (
            "01_overall_access_rates",
            "How common are the two financial-access outcomes?",
            "Weighted estimates with unweighted sample-rate markers.",
            plot_overall_rates(overall, figure_dir),
        ),
        (
            "02_demographic_patterns",
            "How do outcomes vary by gender and age?",
            "Weighted rates; all substantive groups shown.",
            _plot_dimension_panels(
                subgroup,
                ("gender", "age_group"),
                "Age differences are larger than gender differences in the observed data",
                "Weighted rates. Bars describe associations in these data; they do not establish causation.",
                figure_dir,
                "02_demographic_patterns",
            ),
        ),
        (
            "03_socioeconomic_patterns",
            "How do education, income, and employment relate to access?",
            "Weighted rates; non-substantive response categories omitted from the chart but retained in CSV summaries.",
            _plot_dimension_panels(
                subgroup,
                ("education", "income_quintile", "employment"),
                "Financial access varies substantially across socioeconomic groups",
                "Weighted rates. Non-substantive response categories are omitted visually and retained in subgroup_rates.csv.",
                figure_dir,
                "03_socioeconomic_patterns",
            ),
        ),
        (
            "04_digital_access_patterns",
            "How do internet and phone access relate to the two outcomes?",
            "Weighted rates; non-substantive response categories omitted from the chart and retained in CSV summaries.",
            _plot_dimension_panels(
                subgroup,
                ("internet_use", "phone_ownership", "phone_type"),
                "Internet and phone access align with higher observed financial-access rates",
                "Weighted rates. Internet-use zero combines no, don't know, and refused in the source variable.",
                figure_dir,
                "04_digital_access_patterns",
            ),
        ),
    ]
    for stem, question, note, paths in figure_specs:
        for path in paths:
            manifest.append(
                {
                    "figure": path.name,
                    "stem": stem,
                    "format": path.suffix.lstrip("."),
                    "question": question,
                    "estimate": "survey-weighted subgroup rate" if stem != "01_overall_access_rates" else "weighted and unweighted overall rates",
                    "note": note,
                    "sha256": file_hash(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return manifest


def _rate_lookup(subgroup: pd.DataFrame, target: str, dimension: str, category: str) -> float:
    match = subgroup.loc[
        (subgroup["target"] == target)
        & (subgroup["dimension"] == dimension)
        & (subgroup["category"] == category),
        "weighted_rate",
    ]
    if len(match) != 1:
        raise ValueError(f"Could not uniquely locate {target}/{dimension}/{category}.")
    return float(match.iloc[0])


def build_findings(overall: pd.DataFrame, subgroup: pd.DataFrame) -> list[dict[str, object]]:
    overall_lookup = overall.set_index("target")
    findings = [
        {
            "question": "How common are financial inclusion and mobile-money adoption?",
            "finding": (
                f"The weighted financial-inclusion estimate is {overall_lookup.loc['account_fin', 'weighted_rate']:.1%}; "
                f"the weighted mobile-money estimate is {overall_lookup.loc['account_mob', 'weighted_rate']:.1%}."
            ),
            "interpretation": "Mobile-money adoption is more common than financial-institution account ownership in the weighted descriptive estimates.",
        },
        {
            "question": "Does financial access differ by education?",
            "finding": (
                f"Financial inclusion is {_rate_lookup(subgroup, 'account_fin', 'education', 'Tertiary education or more'):.1%} "
                f"among respondents with tertiary education or more and {_rate_lookup(subgroup, 'account_fin', 'education', 'Primary education or less'):.1%} "
                "among those with primary education or less."
            ),
            "interpretation": "Education level is associated with a large descriptive financial-inclusion gap.",
        },
        {
            "question": "Does financial access differ by household income?",
            "finding": (
                f"Financial inclusion rises from {_rate_lookup(subgroup, 'account_fin', 'income_quintile', 'Income quintile 1'):.1%} "
                f"in quintile 1 to {_rate_lookup(subgroup, 'account_fin', 'income_quintile', 'Income quintile 5'):.1%} in quintile 5."
            ),
            "interpretation": "Higher income quintiles are associated with higher financial-inclusion rates, although mobile-money rates are not perfectly monotonic across all quintiles.",
        },
        {
            "question": "Does workforce participation matter descriptively?",
            "finding": (
                f"Financial inclusion is {_rate_lookup(subgroup, 'account_fin', 'employment', 'In the workforce'):.1%} in the workforce and "
                f"{_rate_lookup(subgroup, 'account_fin', 'employment', 'Out of the workforce'):.1%} outside it."
            ),
            "interpretation": "Workforce participation is associated with higher observed financial inclusion and mobile-money adoption.",
        },
        {
            "question": "How is recent internet use associated with the outcomes?",
            "finding": (
                f"Mobile-money adoption is {_rate_lookup(subgroup, 'account_mob', 'internet_use', 'Yes'):.1%} among recent internet users and "
                f"{_rate_lookup(subgroup, 'account_mob', 'internet_use', INTERNET_ZERO_LABEL):.1%} in the combined zero category."
            ),
            "interpretation": "Recent internet use is associated with higher observed financial inclusion and mobile-money adoption.",
        },
        {
            "question": "How is mobile-phone ownership associated with mobile money?",
            "finding": (
                f"Mobile-money adoption is {_rate_lookup(subgroup, 'account_mob', 'phone_ownership', 'Yes'):.1%} among phone owners and "
                f"{_rate_lookup(subgroup, 'account_mob', 'phone_ownership', 'No'):.1%} among respondents reporting no phone."
            ),
            "interpretation": "Phone ownership is associated with a sizeable mobile-money adoption gap.",
        },
    ]
    return findings


def _render_report(summary: dict[str, object]) -> str:
    overall = summary["overall_rates"]
    findings = summary["findings"]
    lines = [
        "# Phase 4 — Exploratory Data Analysis",
        "",
        "## Scope and estimation",
        "",
        "This phase describes patterns in the supplied Eswatini microdata. Weighted rates use the supplied `wgt` field and are accompanied by unweighted respondent counts in the CSV tables. The results show association, not causation. No hypothesis tests, p-values, predictive models, or feature-selection decisions are included.",
        "",
        "## Overall access",
        "",
        "| Outcome | Weighted estimate | Unweighted sample rate | Positive responses | n |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in overall:
        lines.append(
            f"| {row['outcome']} | {row['weighted_rate']:.1%} | {row['unweighted_rate']:.1%} | {row['positive_count']:,} | {row['n']:,} |"
        )
    lines.extend(["", "## Question-driven findings", ""])
    for index, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"### {index}. {finding['question']}",
                "",
                str(finding["finding"]),
                "",
                f"**Interpretation:** {finding['interpretation']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Additional observations",
            "",
            "- Gender gaps are modest in the weighted descriptive rates compared with several age, education, income, employment, internet, and phone-access differences.",
            "- Respondents aged 15–24 have the lowest observed weighted rates for both outcomes among the defined age groups.",
            "- The highest mobile-money rate by income appears in quintile 4 rather than quintile 5, so the income pattern for mobile money is not strictly monotonic.",
            "- `urbanicity` cannot support an urban/rural comparison because Phase 1 found it is constant in this country extract.",
            "",
            "## Interpretation guardrails",
            "",
            "- These are bivariate descriptive comparisons and may reflect confounding or correlated characteristics.",
            "- Weighted estimates are population-oriented descriptions; unweighted counts show the actual sample evidence behind each group.",
            "- The file provides a weight but no strata or cluster variables used here, so Phase 4 does not calculate survey-design standard errors or confidence intervals.",
            "- Nonresponse and routed states remain in `subgroup_rates.csv`; non-substantive response categories are omitted from figures, and substantive groups require at least 10 respondents.",
            "- The constructed `internet_use=0` category combines no, don't know, and refused and cannot be disaggregated.",
            "- Formal association testing and effect sizes belong to Phase 5 and have not been performed.",
            "",
            "## Deliverables",
            "",
            "- `overall_rates.csv`: weighted and unweighted national descriptive rates",
            "- `subgroup_rates.csv`: complete outcome-by-group summary with sample sizes and chart-eligibility flags",
            "- `figures/`: publication-ready PNG and SVG charts",
            "- `chart_manifest.csv`: chart purpose, notes, hashes, and file sizes",
            "- `eda_summary.json`: machine-readable findings and validation metadata",
            "",
        ]
    )
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(
    raw_path: Path = DEFAULT_INPUT,
    dictionary_path: Path = DEFAULT_DICTIONARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    frame, validation = build_eda_frame(raw_path, dictionary_path)
    overall = build_overall_rates(frame)
    subgroup = build_subgroup_rates(frame)
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = output_dir / "figures"

    overall.to_csv(output_dir / "overall_rates.csv", index=False, encoding="utf-8", lineterminator="\n")
    subgroup.to_csv(output_dir / "subgroup_rates.csv", index=False, encoding="utf-8", lineterminator="\n")
    chart_manifest = create_figures(overall, subgroup, figure_dir)
    _write_csv(output_dir / "chart_manifest.csv", chart_manifest)
    findings = build_findings(overall, subgroup)

    summary: dict[str, object] = {
        "phase": 4,
        "status": "PASS_WITH_NOTES",
        "scope": "descriptive exploratory analysis only",
        "source_validation": validation,
        "estimation": {
            "primary_rate": "survey-weighted using wgt",
            "supporting_rate": "unweighted sample proportion",
            "sample_size_reporting": "unweighted n",
            "hypothesis_tests_performed": False,
            "causal_claims_made": False,
        },
        "overall_rates": overall.to_dict(orient="records"),
        "subgroup_row_count": int(len(subgroup)),
        "dimensions": [dimension.key for dimension in DIMENSIONS],
        "findings": findings,
        "figures": chart_manifest,
        "limitations": [
            "urbanicity is constant and cannot support an urban/rural comparison",
            "survey-design strata and cluster variables were not used",
            "internet_use=0 combines no, don't know, and refused",
            "bivariate associations do not imply causation",
        ],
    }
    (output_dir / "eda_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "eda_report.md").write_text(_render_report(summary), encoding="utf-8")
    missing_deliverables = validate_completed_phase_files(PROJECT_ROOT, through_phase=4)
    (output_dir / "deliverable_checklist.md").write_text(
        render_delivery_checklist(PROJECT_ROOT, through_phase=4), encoding="utf-8"
    )
    if missing_deliverables:
        raise RuntimeError(f"Completed-phase deliverable validation failed: {missing_deliverables}")
    summary["deliverable_validation"] = {
        "passed": True,
        "phases_checked": [1, 2, 3, 4],
        "missing_files": {},
        "checklist": "reports/phase_4/deliverable_checklist.md",
    }
    (output_dir / "eda_summary.json").write_text(
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
    print(
        json.dumps(
            {
                "status": summary["status"],
                "rows": summary["source_validation"]["rows"],
                "overall_rates": summary["overall_rates"],
                "figure_count": len(summary["figures"]),
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
