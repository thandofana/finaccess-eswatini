"""Reproducible Phase 1 audit of the raw FinAccess Eswatini CSV.

The audit intentionally uses only Python's standard library. It describes the
raw file without changing or imputing respondent-level values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "Findex_Microdata_2025_updateEswatini.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_1"
TARGETS = ("account_fin", "account_mob")
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
SPECIAL_MISSING_TOKENS = {
    "NA",
    "N/A",
    "NULL",
    "NONE",
    "NAN",
    "MISSING",
    "DK",
    "DON'T KNOW",
    "DONT KNOW",
    "REFUSED",
}
CANDIDATE_NUMERIC_SPECIAL_CODES = {
    "8",
    "9",
    "97",
    "98",
    "99",
    "997",
    "998",
    "999",
    "-8",
    "-9",
    "-97",
    "-98",
    "-99",
}


@dataclass(frozen=True)
class CsvData:
    headers: list[str]
    rows: list[list[str]]
    encoding: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> CsvData:
    """Read a UTF-8 CSV and preserve raw string values for auditability."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            rows = list(csv.reader(source))
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        with path.open("r", encoding="cp1252", newline="") as source:
            rows = list(csv.reader(source))
        encoding = "cp1252"

    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return CsvData(headers=rows[0], rows=rows[1:], encoding=encoding)


def _parse_decimal(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def infer_type(values: Sequence[str]) -> str:
    non_missing = [value.strip() for value in values if value.strip()]
    if not non_missing:
        return "empty"
    if all(INTEGER_PATTERN.fullmatch(value) for value in non_missing):
        return "integer"
    if all(_parse_decimal(value) is not None for value in non_missing):
        return "float"
    return "string"


def _top_values(counter: Counter[str], limit: int = 8) -> str:
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return json.dumps([{"value": value, "count": count} for value, count in ranked])


def profile_columns(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    row_count = len(rows)
    for index, name in enumerate(headers):
        values = [row[index].strip() for row in rows]
        non_missing_values = [value for value in values if value]
        counts = Counter(non_missing_values)
        inferred_type = infer_type(values)
        numeric_values = (
            [_parse_decimal(value) for value in non_missing_values]
            if inferred_type in {"integer", "float"}
            else []
        )
        numeric_values = [value for value in numeric_values if value is not None]
        missing_count = row_count - len(non_missing_values)
        n_unique = len(counts)
        profile: dict[str, object] = {
            "position": index + 1,
            "column": name,
            "inferred_type": inferred_type,
            "non_missing_count": len(non_missing_values),
            "missing_count": missing_count,
            "missing_pct": round((missing_count / row_count * 100) if row_count else 0.0, 4),
            "unique_count": n_unique,
            "unique_pct_non_missing": round(
                (n_unique / len(non_missing_values) * 100) if non_missing_values else 0.0,
                4,
            ),
            "is_all_missing": missing_count == row_count,
            "is_constant_non_missing": n_unique <= 1,
            "is_unique_non_missing": bool(non_missing_values) and n_unique == len(non_missing_values),
            "min": None,
            "max": None,
            "mean": None,
            "top_values": _top_values(counts),
        }
        if numeric_values:
            profile["min"] = str(min(numeric_values))
            profile["max"] = str(max(numeric_values))
            profile["mean"] = str(sum(numeric_values) / Decimal(len(numeric_values)))
        profiles.append(profile)
    return profiles


def target_summary(
    target: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> dict[str, object]:
    if target not in headers:
        return {"present": False, "valid_binary_0_1": False}
    index = headers.index(target)
    values = [row[index].strip() for row in rows]
    counts = Counter(values)
    missing_count = counts.pop("", 0)
    observed = set(counts)
    total_non_missing = sum(counts.values())
    return {
        "present": True,
        "position": index + 1,
        "missing_count": missing_count,
        "observed_values": sorted(observed),
        "distribution": dict(sorted(counts.items())),
        "valid_binary_0_1": observed == {"0", "1"} and missing_count == 0,
        "unweighted_positive_rate": (
            counts.get("1", 0) / total_non_missing if total_non_missing else None
        ),
    }


def duplicate_summary(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> dict[str, int]:
    row_counts = Counter(tuple(row) for row in rows)
    duplicate_groups = [count for count in row_counts.values() if count > 1]
    result = {
        "exact_duplicate_groups": len(duplicate_groups),
        "duplicate_rows_excluding_first": sum(count - 1 for count in duplicate_groups),
        "rows_in_duplicate_groups": sum(duplicate_groups),
        "duplicate_identifier_values": 0,
        "duplicate_profiles_excluding_identifier_groups": 0,
        "duplicate_profiles_excluding_identifier_rows_excluding_first": 0,
    }
    if "wpid_random" in headers:
        identifier_index = headers.index("wpid_random")
        identifiers = [row[identifier_index].strip() for row in rows]
        result["duplicate_identifier_values"] = len(identifiers) - len(set(identifiers))
        profiles_without_identifier = Counter(
            tuple(row[:identifier_index]) + tuple(row[identifier_index + 1 :]) for row in rows
        )
        candidate_groups = [count for count in profiles_without_identifier.values() if count > 1]
        result["duplicate_profiles_excluding_identifier_groups"] = len(candidate_groups)
        result["duplicate_profiles_excluding_identifier_rows_excluding_first"] = sum(
            count - 1 for count in candidate_groups
        )
    return result


def preliminary_field_review(profiles: Sequence[dict[str, object]]) -> list[dict[str, str]]:
    """Flag only obvious identifier/metadata fields; Phase 2 owns full classification."""
    profile_by_name = {str(profile["column"]): profile for profile in profiles}
    rationales = {
        "year": "Survey-year metadata; constant or near-constant in a single-wave extract.",
        "economy": "Economy label metadata; expected to be constant in an Eswatini-only extract.",
        "economycode": "Economy code metadata; expected to be constant in a single-economy extract.",
        "regionwb": "World Bank region metadata; expected to be constant here.",
        "pop_adult": "Population-level metadata, not a respondent characteristic.",
        "wpid_random": "Respondent identifier candidate; uniqueness must be checked.",
        "wgt": "Survey weight; required for representative estimates but not an ordinary predictor.",
    }
    review = []
    for column, rationale in rationales.items():
        if column in profile_by_name:
            profile = profile_by_name[column]
            review.append(
                {
                    "column": column,
                    "preliminary_role": "IDENTIFIER" if column == "wpid_random" else "METADATA",
                    "rationale": rationale,
                    "unique_count": str(profile["unique_count"]),
                    "missing_pct": str(profile["missing_pct"]),
                }
            )
    return review


def special_token_inventory(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> list[dict[str, object]]:
    findings: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        for index, raw_value in enumerate(row):
            value = raw_value.strip()
            if value.upper() in SPECIAL_MISSING_TOKENS:
                findings[(headers[index], value, "textual_candidate")] += 1
            if value in CANDIDATE_NUMERIC_SPECIAL_CODES:
                findings[(headers[index], value, "numeric_candidate")] += 1
    return [
        {"column": column, "token": token, "kind": kind, "count": count}
        for (column, token, kind), count in sorted(findings.items())
    ]


def value_set_summary(
    headers: Sequence[str], rows: Sequence[Sequence[str]], max_values: int = 12
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for index, name in enumerate(headers):
        unique_values = sorted({row[index].strip() for row in rows if row[index].strip()})
        if 0 < len(unique_values) <= max_values:
            grouped[tuple(unique_values)].append(name)
    result = []
    for values, columns in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        result.append(
            {
                "observed_values": json.dumps(list(values)),
                "column_count": len(columns),
                "columns": json.dumps(columns),
            }
        )
    return result


def _numeric_values(column: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[Decimal]:
    if column not in headers:
        return []
    index = headers.index(column)
    values = [_parse_decimal(row[index].strip()) for row in rows if row[index].strip()]
    return [value for value in values if value is not None]


def plausibility_checks(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []

    def add_numeric_range(column: str, lower: Decimal, upper: Decimal, assumption: str) -> None:
        values = _numeric_values(column, headers, rows)
        if not values:
            return
        invalid = sum(value < lower or value > upper for value in values)
        checks.append(
            {
                "column": column,
                "check": f"expected range {lower} to {upper}",
                "flagged_count": invalid,
                "status": "PASS" if invalid == 0 else "REVIEW",
                "assumption": assumption,
            }
        )

    add_numeric_range("age", Decimal(15), Decimal(110), "Adult survey plausibility bound, not a recoding rule.")
    add_numeric_range("inc_q", Decimal(1), Decimal(5), "Expected income-quintile coding.")
    add_numeric_range("account_fin", Decimal(0), Decimal(1), "Required binary target.")
    add_numeric_range("account_mob", Decimal(0), Decimal(1), "Required binary target.")

    weights = _numeric_values("wgt", headers, rows)
    if weights:
        invalid_weights = sum(value <= 0 for value in weights)
        checks.append(
            {
                "column": "wgt",
                "check": "survey weight must be positive",
                "flagged_count": invalid_weights,
                "status": "PASS" if invalid_weights == 0 else "REVIEW",
                "assumption": "Non-positive survey weights are not analytically usable.",
            }
        )
    for column in ("female", "emp_in"):
        if column in headers:
            index = headers.index(column)
            observed = sorted({row[index].strip() for row in rows if row[index].strip()})
            expected_sets = ({"0", "1"}, {"1", "2"})
            accepted = set(observed) in expected_sets
            checks.append(
                {
                    "column": column,
                    "check": f"observed indicator codes {observed}",
                    "flagged_count": 0 if accepted else len(rows),
                    "status": "PASS" if accepted else "REVIEW",
                    "assumption": (
                        "Indicator code set is structurally plausible; semantic labels require the data dictionary."
                    ),
                }
            )
    return checks


def build_audit(input_path: Path) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    data = read_csv(input_path)
    headers = data.headers
    rows = data.rows
    profiles = profile_columns(headers, rows)
    row_widths = Counter(len(row) for row in rows)
    profile_by_name = {str(profile["column"]): profile for profile in profiles}
    all_missing = [name for name, p in profile_by_name.items() if p["is_all_missing"]]
    constant = [name for name, p in profile_by_name.items() if p["is_constant_non_missing"]]
    high_missing = {
        threshold: [
            name
            for name, profile in profile_by_name.items()
            if float(profile["missing_pct"]) >= threshold
        ]
        for threshold in (50, 75, 90)
    }
    binary_columns = []
    for index, name in enumerate(headers):
        observed = {row[index].strip() for row in rows if row[index].strip()}
        if observed == {"0", "1"}:
            binary_columns.append(name)

    try:
        display_path = input_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_path = str(input_path)

    summary: dict[str, object] = {
        "phase": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": display_path,
            "size_bytes": input_path.stat().st_size,
            "sha256": sha256_file(input_path),
            "encoding": data.encoding,
        },
        "shape": {"rows": len(rows), "columns": len(headers)},
        "structure": {
            "delimiter": ",",
            "row_width_counts": dict(sorted(row_widths.items())),
            "blank_header_positions": [i + 1 for i, name in enumerate(headers) if not name.strip()],
            "duplicate_headers": sorted(name for name, count in Counter(headers).items() if count > 1),
        },
        "targets": {target: target_summary(target, headers, rows) for target in TARGETS},
        "duplicates": duplicate_summary(headers, rows),
        "missingness": {
            "total_blank_cells": sum(int(profile["missing_count"]) for profile in profiles),
            "total_cells": len(rows) * len(headers),
            "all_missing_columns": all_missing,
            "columns_at_least_50_pct_missing": high_missing[50],
            "columns_at_least_75_pct_missing": high_missing[75],
            "columns_at_least_90_pct_missing": high_missing[90],
        },
        "types": dict(Counter(str(profile["inferred_type"]) for profile in profiles)),
        "cardinality": {
            "constant_or_all_missing_columns": constant,
            "constant_non_missing_columns": [
                name
                for name, p in profile_by_name.items()
                if p["is_constant_non_missing"] and not p["is_all_missing"]
            ],
            "unique_non_missing_columns": [
                name for name, p in profile_by_name.items() if p["is_unique_non_missing"]
            ],
            "binary_0_1_columns": binary_columns,
        },
        "preliminary_identifier_metadata_review": preliminary_field_review(profiles),
        "candidate_special_missing_tokens": special_token_inventory(headers, rows),
        "basic_plausibility_checks": plausibility_checks(headers, rows),
        "scope_note": (
            "Only obvious metadata/identifier fields are flagged in Phase 1. Full variable meaning, "
            "feature eligibility, leakage decisions, and special-code interpretation belong to Phase 2."
        ),
    }
    return summary, profiles, value_set_summary(headers, rows)


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _markdown_list(values: Sequence[str], empty_text: str = "None") -> str:
    return empty_text if not values else ", ".join(f"`{value}`" for value in values)


def render_markdown(summary: dict[str, object], profiles: Sequence[dict[str, object]]) -> str:
    shape = summary["shape"]
    targets = summary["targets"]
    missingness = summary["missingness"]
    duplicates = summary["duplicates"]
    types = summary["types"]
    structure = summary["structure"]
    cardinality = summary["cardinality"]
    source = summary["source"]
    high_missing_profiles = sorted(
        (profile for profile in profiles if float(profile["missing_pct"]) >= 50),
        key=lambda profile: (-float(profile["missing_pct"]), str(profile["column"])),
    )
    metadata_review = summary["preliminary_identifier_metadata_review"]
    plausibility = summary["basic_plausibility_checks"]
    special_tokens = summary["candidate_special_missing_tokens"]

    lines = [
        "# Phase 1 Data Quality Report",
        "",
        "> Scope: raw-data structure and quality only. No cleaning, feature eligibility decisions, leakage review, statistical testing, or modelling was performed.",
        "",
        "## Source integrity",
        "",
        f"- File: `{source['path']}`",
        f"- Size: {source['size_bytes']:,} bytes",
        f"- SHA-256: `{source['sha256']}`",
        f"- Decoded as: `{source['encoding']}`",
        "",
        "## Structural validation",
        "",
        f"- Shape: **{shape['rows']:,} rows × {shape['columns']:,} columns**",
        f"- Row widths: `{structure['row_width_counts']}`",
        f"- Blank headers: {len(structure['blank_header_positions'])}",
        f"- Duplicate headers: {len(structure['duplicate_headers'])}",
        f"- Exact duplicate rows excluding the first occurrence: **{duplicates['duplicate_rows_excluding_first']:,}**",
        f"- Duplicate respondent-ID values: **{duplicates['duplicate_identifier_values']:,}**",
        f"- Duplicate response profiles after excluding only `wpid_random`: **{duplicates['duplicate_profiles_excluding_identifier_rows_excluding_first']:,}** across {duplicates['duplicate_profiles_excluding_identifier_groups']:,} group(s)",
        "",
        "## Target validation",
        "",
        "Target | Observed counts | Missing | Unweighted positive rate | Binary validation",
        "--- | ---: | ---: | ---: | ---",
    ]
    for target in TARGETS:
        target_data = targets[target]
        lines.append(
            f"`{target}` | `{target_data.get('distribution')}` | "
            f"{target_data.get('missing_count', 'n/a')} | "
            f"{_format_pct(target_data.get('unweighted_positive_rate'))} | "
            f"{'PASS' if target_data.get('valid_binary_0_1') else 'FAIL'}"
        )
    lines.extend(
        [
            "",
            "Rates above are unweighted audit statistics. The `wgt` field must be evaluated and used appropriately for population-representative descriptive analysis in later phases.",
            "",
            "## Missingness",
            "",
            f"- Blank cells: **{missingness['total_blank_cells']:,} of {missingness['total_cells']:,}** ({missingness['total_blank_cells'] / missingness['total_cells'] * 100:.2f}%)",
            f"- 100% missing columns ({len(missingness['all_missing_columns'])}): {_markdown_list(missingness['all_missing_columns'])}",
            f"- Columns with at least 50% missingness: **{len(missingness['columns_at_least_50_pct_missing'])}**",
            f"- Columns with at least 75% missingness: **{len(missingness['columns_at_least_75_pct_missing'])}**",
            f"- Columns with at least 90% missingness: **{len(missingness['columns_at_least_90_pct_missing'])}**",
            "",
            "Column | Missing count | Missing % | Non-missing unique values",
            "--- | ---: | ---: | ---:",
        ]
    )
    if high_missing_profiles:
        lines.extend(
            f"`{profile['column']}` | {profile['missing_count']} | {float(profile['missing_pct']):.2f}% | {profile['unique_count']}"
            for profile in high_missing_profiles
        )
    else:
        lines.append("_No columns meet the 50% threshold._ |  |  | ")

    lines.extend(
        [
            "",
            "## Data types and coding patterns",
            "",
            f"- Inferred raw types: `{types}`",
            f"- Exact 0/1 binary columns: **{len(cardinality['binary_0_1_columns'])}**",
            f"- Constant non-missing columns: {_markdown_list(cardinality['constant_non_missing_columns'])}",
            f"- Constant or fully empty columns: **{len(cardinality['constant_or_all_missing_columns'])}**",
            f"- Unique non-missing columns: {_markdown_list(cardinality['unique_non_missing_columns'])}",
            "- `female` and `emp_in` use observed 1/2 indicator coding; they must not be treated as Boolean 0/1 fields until labels are confirmed.",
            "- Empty strings are treated as structural missingness. No non-empty textual missing markers were automatically recoded.",
            f"- Candidate special-code column/token pairs: **{len(special_tokens)}**. The inventory includes possible numeric codes such as 8/9/97/98/99; these require dictionary-based confirmation in Phase 2.",
            "- Many survey items use small integer code sets. `value_set_summary.csv` records the exact observed sets and affected columns; the codes must not be interpreted without the official variable definitions.",
            "",
            "## Preliminary identifier and metadata review",
            "",
            "Column | Preliminary role | Unique values | Missing % | Reason",
            "--- | --- | ---: | ---: | ---",
        ]
    )
    lines.extend(
        f"`{item['column']}` | {item['preliminary_role']} | {item['unique_count']} | {float(item['missing_pct']):.2f}% | {item['rationale']}"
        for item in metadata_review
    )

    lines.extend(
        [
            "",
            "This review is intentionally narrow. It is not the Phase 2 variable classification or feature-selection decision.",
            "",
            "## Basic plausibility checks",
            "",
            "Column | Check | Flagged | Status | Assumption",
            "--- | --- | ---: | --- | ---",
        ]
    )
    lines.extend(
        f"`{item['column']}` | {item['check']} | {item['flagged_count']} | {item['status']} | {item['assumption']}"
        for item in plausibility
    )

    lines.extend(
        [
            "",
            "## Phase 1 risks and decisions",
            "",
            "- The file contains many financial-behaviour variables alongside the targets. They are not automatically eligible predictors and create a high target-leakage risk for both future models.",
            "- Survey item codes are numeric but are not necessarily continuous quantities. Phase 2 must use the real dictionary/metadata before assigning semantic types or missing codes.",
            "- The survey weight needs a deliberate distinction between weighted population description and predictive model training/evaluation.",
            "- `urbanicity` is constant (`1`) for all respondents, so this extract cannot support an urban-versus-rural comparison unless the coding or extract scope is clarified.",
            "- One pair of rows has identical values after excluding only the unique respondent ID. This is a duplicate candidate, not proof of duplication, and no row was removed.",
            "- Extensive missingness is likely influenced by questionnaire routing/skip logic; it must not be treated as random missingness without the data dictionary.",
            "- Raw respondent microdata are kept local and Git-ignored pending a licensing/publication review.",
            "- No value was removed, recoded, imputed, or transformed during this audit.",
            "",
            "## Generated artifacts",
            "",
            "- `audit_summary.json`: machine-readable audit summary",
            "- `column_profile.csv`: one-row-per-column profile",
            "- `value_set_summary.csv`: recurring low-cardinality coding patterns",
            "- `special_code_inventory.csv`: possible textual and numeric special-response codes",
            "- `data_quality_report.md`: this human-readable report",
            "",
        ]
    )
    return "\n".join(lines)


def run(input_path: Path, output_dir: Path) -> dict[str, object]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {input_path}")
    summary, profiles, value_sets = build_audit(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_csv(output_dir / "column_profile.csv", profiles)
    write_csv(output_dir / "value_set_summary.csv", value_sets)
    write_csv(output_dir / "special_code_inventory.csv", summary["candidate_special_missing_tokens"])
    (output_dir / "data_quality_report.md").write_text(
        render_markdown(summary, profiles), encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(args.input.resolve(), args.output_dir.resolve())
    print(
        json.dumps(
            {
                "status": "PASS",
                "shape": summary["shape"],
                "targets": summary["targets"],
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
