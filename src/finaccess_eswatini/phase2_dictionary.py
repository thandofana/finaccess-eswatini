"""Build the Phase 2 data dictionary and model-specific feature blueprints.

This module performs documentation and eligibility review only. It does not
clean data, engineer features, split data, or train models.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree import ElementTree as ET

import pdfplumber

from finaccess_eswatini.data_audit import DEFAULT_INPUT, PROJECT_ROOT
from finaccess_eswatini.feature_config import (
    MODEL1_CONDITIONAL_FEATURES,
    MODEL1_CORE_FEATURES,
    MODEL2_CONDITIONAL_FEATURES,
    MODEL2_CORE_FEATURES,
)


CATALOG_ID = "7900"
REFERENCE_ID = "SWZ_2024_FINDEX_v02_M"
DOI_URL = "https://doi.org/10.48529/5rsc-p773"
CATALOG_URL = "https://microdata.worldbank.org/catalog/7900"
RELATED_MATERIALS_URL = f"{CATALOG_URL}/related-materials"
DDI_URL = f"https://microdata.worldbank.org/metadata/export/{CATALOG_ID}/ddi"
CODEBOOK_URL = f"{CATALOG_URL}/download/352255"
DEFAULT_REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
DEFAULT_DDI = DEFAULT_REFERENCE_DIR / "catalog_7900_ddi.xml"
DEFAULT_CODEBOOK = DEFAULT_REFERENCE_DIR / "codebook_microdata_2025.pdf"
DEFAULT_PHASE1_PROFILE = PROJECT_ROOT / "reports" / "phase_1" / "column_profile.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "phase_2"

TARGETS = {"account_fin", "account_mob"}
METADATA = {"year", "economy", "economycode", "regionwb", "pop_adult", "wgt"}
IDENTIFIERS = {"wpid_random"}
DEMOGRAPHIC = {"female", "age", "urbanicity"}
SOCIOECONOMIC = {"educ", "inc_q", "emp_in", "fin24c"}
IDENTITY = {"fin46", "fin47", "fin48a", "fin48b", "fin48c", "fin48d", "fin48e", "fin48f", "fin49a", "fin49b", "fin49c", "fin49d", "fin49e", "fin49f", "fin50", "fin51"}
CONSTRUCTED = {
    "account_fin",
    "account_mob",
    "account",
    "dig_account",
    "borrowed",
    "saved",
    "receive_wages",
    "receive_transfers",
    "receive_pensions",
    "receive_agriculture",
    "merchantpay_dig",
    "pay_utilities",
    "domestic_remittances",
    "anydigpayment",
    "internet_use",
}

MODEL1_CORE = set(MODEL1_CORE_FEATURES)
MODEL1_CONDITIONAL = set(MODEL1_CONDITIONAL_FEATURES)
MODEL2_CORE = set(MODEL2_CORE_FEATURES)
MODEL2_CONDITIONAL = set(MODEL2_CONDITIONAL_FEATURES)

REDUNDANT_DIGITAL = {"con24", "con25"}
POST_DIGITAL_EVENTS = {"con21", "con22", "con23", "fin47"}
NON_CAPACITY_DIGITAL = {"con17", "con30f"}

DIRECT_MODEL1 = {
    "account",
    "dig_account",
    "receive_wages",
    "receive_transfers",
    "receive_pensions",
    "receive_agriculture",
    "pay_utilities",
    "fin2",
    "fin3",
    "fin4",
    "fin5",
    "fin6",
    "fin7",
    "fin8",
    "fin9a",
    "fin9b",
    "fin10",
    "fin11_0",
    "fin11_1",
    "fin11_2",
    "fin11a",
    "fin11b",
    "fin11c",
    "fin11d",
    "fin11e",
    "fin11f",
}
DIRECT_MODEL2 = {
    "account",
    "dig_account",
    "receive_wages",
    "receive_transfers",
    "receive_pensions",
    "receive_agriculture",
    "merchantpay_dig",
    "pay_utilities",
    "domestic_remittances",
    "anydigpayment",
    "fin13_1",
    "fin13a",
    "fin13b",
    "fin13c",
    "fin13d",
    "fin13e",
    "fin13f",
    "fin13f_1",
    "fin14a",
    "fin14b",
    "fin14c",
    "fin14d",
    "fin14e",
    "fin15",
    "fin16",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_reference(path: Path, url: str) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "FinAccess-Eswatini/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as destination:
        destination.write(response.read())


def clean_text(value: str | None) -> str:
    normalized = (value or "").translate(
        str.maketrans(
            {
                "\u2018": "'",
                "\u2019": "'",
                "\u201c": '"',
                "\u201d": '"',
                "\u2013": "-",
                "\u2014": "-",
            }
        )
    )
    return re.sub(r"\s+", " ", normalized).strip()


def element_text(element: ET.Element | None) -> str:
    return clean_text("".join(element.itertext())) if element is not None else ""


def parse_ddi(path: Path) -> list[dict[str, object]]:
    namespace = {"d": "ddi:codebook:2_5"}
    root = ET.parse(path).getroot()
    records: list[dict[str, object]] = []
    for position, variable in enumerate(root.findall(".//d:var", namespace), start=1):
        summary_stats = {
            stat.attrib.get("type", ""): clean_text(stat.text)
            for stat in variable.findall("d:sumStat", namespace)
        }
        categories = []
        for category in variable.findall("d:catgry", namespace):
            categories.append(
                {
                    "value": clean_text(category.findtext("d:catValu", default="", namespaces=namespace)),
                    "label": clean_text(category.findtext("d:labl", default="", namespaces=namespace)),
                }
            )
        variable_format = variable.find("d:varFormat", namespace)
        name = variable.attrib["name"]
        records.append(
            {
                "position": position,
                "ddi_id": variable.attrib.get("ID", ""),
                "variable": name,
                "ddi_type": variable_format.attrib.get("type", "") if variable_format is not None else "",
                "label": clean_text(variable.findtext("d:labl", default="", namespaces=namespace)),
                "literal_question": element_text(variable.find("d:qstn/d:qstnLit", namespace)),
                "ddi_notes": element_text(variable.find("d:notes", namespace)),
                "ddi_valid_count": int(summary_stats.get("vald") or 0),
                "ddi_missing_count": int(summary_stats.get("invd") or 0),
                "ddi_min": summary_stats.get("min", ""),
                "ddi_max": summary_stats.get("max", ""),
                "documented_codes": categories,
                "source_url": f"{CATALOG_URL}/variable/F1/{variable.attrib.get('ID', '')}?name={name}",
            }
        )
    return records


def _codebook_heading(line: str) -> bool:
    value = line.strip()
    return value.startswith(
        (
            "Global Findex",
            "Using responses from",
            "Variable names and definitions",
            "(ID4D)",
            "Identification for Development",
            "Note: For documentation",
            "The Global Findex",
        )
    )


def parse_codebook(path: Path, dataset_variables: Sequence[str]) -> dict[str, dict[str, object]]:
    aliases = {name.lower(): name for name in dataset_variables}
    aliases["internet"] = "internet_use"
    known = set(aliases)
    records = {
        name: {"codebook_variable": "", "label_parts": [], "definition_parts": [], "pages": set()}
        for name in dataset_variables
    }
    current: str | None = None
    pending_name = ""
    pending_lines: list[tuple[str, str, int, str]] = []

    def resolve(name: str) -> str | None:
        return aliases.get(name.lower())

    def is_prefix(name: str) -> bool:
        return any(candidate.startswith(name.lower()) for candidate in known)

    def add_line(variable: str | None, label: str, definition: str, page: int, full_line: str) -> None:
        if variable is None or _codebook_heading(full_line):
            return
        if label:
            records[variable]["label_parts"].append(clean_text(label))
        if definition:
            records[variable]["definition_parts"].append(clean_text(definition))
        records[variable]["pages"].add(page)

    with pdfplumber.open(path) as pdf:
        # Page 1 is introductory; page 35 contains only a closing source note.
        for page_number, page in enumerate(pdf.pages[1:34], start=2):
            line_groups: dict[float, list[dict[str, object]]] = {}
            for word in page.extract_words(use_text_flow=False, keep_blank_chars=False):
                line_groups.setdefault(round(float(word["top"]), 1), []).append(word)

            for top, words in sorted(line_groups.items()):
                if top > 735:
                    continue
                words = sorted(words, key=lambda item: float(item["x0"]))
                full_line = clean_text(" ".join(str(word["text"]) for word in words))
                if _codebook_heading(full_line):
                    continue
                variable_text = clean_text(
                    " ".join(
                        str(word["text"])
                        for word in words
                        if 65 <= float(word["x0"]) < 150
                    )
                )
                label = clean_text(
                    " ".join(
                        str(word["text"])
                        for word in words
                        if 150 <= float(word["x0"]) < 260
                    )
                )
                definition = clean_text(
                    " ".join(str(word["text"]) for word in words if float(word["x0"]) >= 260)
                )
                compact_name = variable_text.replace(" ", "")
                resolved = resolve(compact_name) if compact_name else None
                prefix = bool(compact_name and is_prefix(compact_name))

                if resolved:
                    pending_name = ""
                    pending_lines = []
                    current = resolved
                    records[current]["codebook_variable"] = compact_name
                    add_line(current, label, definition, page_number, full_line)
                elif pending_name and compact_name and is_prefix(pending_name + compact_name):
                    pending_name += compact_name
                    pending_lines.append((label, definition, page_number, full_line))
                    resolved = resolve(pending_name)
                    if resolved:
                        current = resolved
                        records[current]["codebook_variable"] = pending_name
                        for pending_label, pending_definition, pending_page, pending_full in pending_lines:
                            add_line(current, pending_label, pending_definition, pending_page, pending_full)
                        pending_name = ""
                        pending_lines = []
                elif prefix:
                    pending_name = compact_name
                    pending_lines = [(label, definition, page_number, full_line)]
                else:
                    add_line(current, label, definition, page_number, full_line)

    parsed: dict[str, dict[str, object]] = {}
    for name, record in records.items():
        parsed[name] = {
            "codebook_variable": record["codebook_variable"],
            "codebook_label": clean_text(" ".join(record["label_parts"])),
            "definition": clean_text(" ".join(record["definition_parts"])),
            "codebook_pages": ";".join(str(page) for page in sorted(record["pages"])),
        }
    return parsed


def load_phase1_profiles(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return {row["column"]: row for row in csv.DictReader(source)}


def observed_value_counts(path: Path) -> dict[str, Counter[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        counters = {name: Counter() for name in reader.fieldnames or []}
        for row in reader:
            for name, raw_value in row.items():
                value = (raw_value or "").strip()
                counters[name][value if value else "<BLANK>"] += 1
    return counters


def primary_category(name: str) -> str:
    if name in TARGETS:
        return "TARGET"
    if name in METADATA:
        return "METADATA"
    if name in IDENTIFIERS:
        return "IDENTIFIER"
    if name in DEMOGRAPHIC:
        return "DEMOGRAPHIC"
    if name in SOCIOECONOMIC:
        return "SOCIOECONOMIC"
    if name in IDENTITY:
        return "IDENTITY"
    if name == "internet_use" or name.startswith("con"):
        return "DIGITAL"
    return "FINANCIAL"


def variable_origin(name: str) -> str:
    if name in CONSTRUCTED:
        return "CONSTRUCTED"
    if name in METADATA or name in IDENTIFIERS:
        return "FILE_METADATA"
    if name in DEMOGRAPHIC or name in {"educ", "inc_q", "emp_in"}:
        return "RESPONDENT_PROFILE"
    return "QUESTIONNAIRE"


def missingness_band(missing_pct: float) -> str:
    if missing_pct == 100:
        return "ALL_MISSING"
    if missing_pct >= 75:
        return "HIGH_75_PLUS"
    if missing_pct >= 50:
        return "HIGH_50_TO_74"
    if missing_pct >= 25:
        return "MODERATE_25_TO_49"
    if missing_pct > 0:
        return "LOW_UNDER_25"
    return "NONE"


def leakage_review(name: str, model: int, category: str) -> tuple[str, str]:
    target = "account_fin" if model == 1 else "account_mob"
    parallel_target = "account_mob" if model == 1 else "account_fin"
    if name == target:
        return "TARGET", "This is the prediction target."
    if name == parallel_target:
        return "HIGH", "Parallel financial-access outcome; conceptually intertwined with the target."
    direct_set = DIRECT_MODEL1 if model == 1 else DIRECT_MODEL2
    if name in direct_set:
        return "DIRECT", "Target component, target-screened item, or close reconstruction of the outcome."
    if name in POST_DIGITAL_EVENTS:
        return "MODERATE", "Post-access digital experience that may occur after adoption."
    if name in NON_CAPACITY_DIGITAL:
        return "MODERATE", "Contemporaneous preference or activity rather than stable pre-outcome access."
    if category == "FINANCIAL":
        return "HIGH", "Financial behaviour or transaction measured during/after the outcome period."
    if model == 2 and name.startswith("con30"):
        return "MODERATE", "Recent digital activity overlaps the mobile-money adoption period but is not the target."
    if name == "fin24c":
        return "LOW", "Exogenous shock measure; temporal overlap should be retained as a limitation."
    if category in {"DEMOGRAPHIC", "SOCIOECONOMIC", "DIGITAL", "IDENTITY"}:
        return "LOW", "Plausibly available as a profile characteristic before prediction."
    return "NONE", "Not a substantive predictor."


def eligibility(
    name: str,
    model: int,
    category: str,
    missing_pct: float,
    unique_count: int,
) -> tuple[str, str, str]:
    target = "account_fin" if model == 1 else "account_mob"
    parallel_target = "account_mob" if model == 1 else "account_fin"
    core = MODEL1_CORE if model == 1 else MODEL2_CORE
    conditional = MODEL1_CONDITIONAL if model == 1 else MODEL2_CONDITIONAL
    risk, basis = leakage_review(name, model, category)

    if name == target:
        return "TARGET", "NOT_APPLICABLE", "Prediction target; never included in its own feature matrix."
    if name == parallel_target:
        return "EXCLUDE_PARALLEL_OUTCOME", "NO", basis
    if name in IDENTIFIERS:
        return "EXCLUDE_IDENTIFIER", "NO", "Unique respondent identifier with no legitimate predictive meaning."
    if name in METADATA:
        return "EXCLUDE_METADATA", "NO", "Survey/economy metadata or weight, not an individual predictor."
    if missing_pct == 100:
        return "EXCLUDE_ALL_MISSING", "NO", f"No observed values in Eswatini; conceptual leakage risk is {risk}."
    if unique_count <= 1:
        return "EXCLUDE_NO_VARIANCE", "NO", "Constant in the Eswatini extract and cannot support prediction."
    if name in core:
        return "CANDIDATE_CORE", "YES", "Interpretable pre-outcome profile characteristic with usable coverage."
    if name in conditional:
        return (
            "CANDIDATE_CONDITIONAL",
            "CONDITIONAL",
            "Relevant pre-outcome characteristic, but routing, temporal overlap, or structural missingness requires Phase 3 handling.",
        )
    other_model_candidates = (MODEL2_CORE | MODEL2_CONDITIONAL) if model == 1 else (MODEL1_CORE | MODEL1_CONDITIONAL)
    if name in other_model_candidates:
        return (
            "EXCLUDE_MODEL_SCOPE",
            "CONDITIONAL",
            "Reserved for the other model's distinct feature blueprint; not required for this model's initial scope.",
        )
    if name in REDUNDANT_DIGITAL:
        return "EXCLUDE_REDUNDANT", "YES", "Component/nested measure retained through the complete `internet_use` indicator instead."
    if missing_pct >= 50:
        return "EXCLUDE_HIGH_MISSING", "CONDITIONAL", f"{missing_pct:.2f}% structurally missing; insufficient standalone coverage."
    if name in POST_DIGITAL_EVENTS:
        return "EXCLUDE_POST_OUTCOME", "NO", basis
    if name in NON_CAPACITY_DIGITAL:
        return "EXCLUDE_CONCEPTUAL", "CONDITIONAL", basis
    if risk == "DIRECT":
        return "EXCLUDE_DIRECT_LEAKAGE", "NO", basis
    if category == "FINANCIAL" or risk == "HIGH":
        return "EXCLUDE_POST_OUTCOME", "NO", basis
    return "EXCLUDE_NOT_ELIGIBLE", "CONDITIONAL", "Not selected for the defensible initial feature blueprint."


def normalize_documented_codes(
    categories: Sequence[dict[str, str]], observed: Counter[str]
) -> list[dict[str, str]]:
    normalized = [dict(category) for category in categories]
    for category in normalized:
        if not category["value"] and category["label"] == "No/DK/Ref" and "0" in observed:
            category["value"] = "0"
    return normalized


def build_dictionary(
    raw_path: Path,
    profile_path: Path,
    ddi_path: Path,
    codebook_path: Path,
) -> list[dict[str, object]]:
    ddi_records = parse_ddi(ddi_path)
    dataset_variables = [str(record["variable"]) for record in ddi_records]
    codebook = parse_codebook(codebook_path, dataset_variables)
    profiles = load_phase1_profiles(profile_path)
    observed = observed_value_counts(raw_path)

    rows: list[dict[str, object]] = []
    for ddi in ddi_records:
        name = str(ddi["variable"])
        profile = profiles[name]
        missing_pct = float(profile["missing_pct"])
        unique_count = int(profile["unique_count"])
        category = primary_category(name)
        model1_risk, model1_basis = leakage_review(name, 1, category)
        model2_risk, model2_basis = leakage_review(name, 2, category)
        model1_status, model1_available, model1_reason = eligibility(
            name, 1, category, missing_pct, unique_count
        )
        model2_status, model2_available, model2_reason = eligibility(
            name, 2, category, missing_pct, unique_count
        )
        documented_codes = normalize_documented_codes(ddi["documented_codes"], observed[name])
        codebook_record = codebook[name]
        label = str(ddi["label"] or codebook_record["codebook_label"])
        definition = str(codebook_record["definition"])
        if name == "year":
            label = "Survey year"
            definition = "Survey data-collection year represented by this extract; the observed value is 2024."

        special_codes = [
            code["value"]
            for code in documented_codes
            if any(term in code["label"].lower() for term in ("don't know", "refused", "no/dk/ref"))
        ]
        tags = [category]
        if name in CONSTRUCTED:
            tags.append("CONSTRUCTED")
        band = missingness_band(missing_pct)
        if missing_pct >= 50:
            tags.append("HIGH_MISSING")
        if missing_pct == 100:
            tags.append("ALL_MISSING")
        if unique_count <= 1:
            tags.append("LOW_VARIANCE")
        if model1_status.startswith("CANDIDATE"):
            tags.append("CANDIDATE_MODEL_1")
        if model2_status.startswith("CANDIDATE"):
            tags.append("CANDIDATE_MODEL_2")
        if model1_risk in {"DIRECT", "HIGH"} or model2_risk in {"DIRECT", "HIGH"}:
            tags.append("POSSIBLE_LEAKAGE")
        if model1_status.startswith("EXCLUDE") and model2_status.startswith("EXCLUDE"):
            tags.append("EXCLUDED")

        rows.append(
            {
                "position": ddi["position"],
                "variable": name,
                "label": label,
                "definition": definition,
                "literal_question": ddi["literal_question"],
                "documented_codes": json.dumps(documented_codes, ensure_ascii=False),
                "observed_value_counts": json.dumps(dict(sorted(observed[name].items())), ensure_ascii=False),
                "special_missing_codes_present": ";".join(special_codes),
                "raw_inferred_type": profile["inferred_type"],
                "observed_unique_count": unique_count,
                "valid_count": int(profile["non_missing_count"]),
                "missing_count": int(profile["missing_count"]),
                "missing_pct": missing_pct,
                "missingness_band": band,
                "primary_category": category,
                "tags": ";".join(dict.fromkeys(tags)),
                "variable_origin": variable_origin(name),
                "model1_status": model1_status,
                "model1_available_pre_outcome": model1_available,
                "model1_leakage_risk": model1_risk,
                "model1_leakage_basis": model1_basis,
                "model1_reason": model1_reason,
                "model2_status": model2_status,
                "model2_available_pre_outcome": model2_available,
                "model2_leakage_risk": model2_risk,
                "model2_leakage_basis": model2_basis,
                "model2_reason": model2_reason,
                "codebook_variable": codebook_record["codebook_variable"],
                "codebook_pages": codebook_record["codebook_pages"],
                "source_url": ddi["source_url"],
            }
        )
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, object]], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(fields or (list(rows[0]) if rows else []))
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def status_counts(rows: Sequence[dict[str, object]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def render_candidate_table(rows: Sequence[dict[str, object]], model: int) -> list[str]:
    status_field = f"model{model}_status"
    reason_field = f"model{model}_reason"
    candidates = [row for row in rows if str(row[status_field]).startswith("CANDIDATE")]
    lines = [
        "Variable | Category | Missing | Tier | Rationale",
        "--- | --- | ---: | --- | ---",
    ]
    for row in candidates:
        lines.append(
            f"`{row['variable']}` | {row['primary_category']} | {float(row['missing_pct']):.2f}% | "
            f"{row[status_field]} | {row[reason_field]}"
        )
    return lines


def render_feature_blueprint(rows: Sequence[dict[str, object]]) -> str:
    return "\n".join(
        [
            "# Phase 2 Feature Blueprint",
            "",
            "> Scope: documentation and eligibility decisions only. No preprocessing, feature engineering, data splitting, statistical testing, or model training was performed.",
            "",
            "## Eligibility method",
            "",
            "A variable is eligible only when it is plausibly available as a profile characteristic before prediction, is not the target or a target component, is not screened by target ownership, has usable Eswatini coverage, and can be collected in a future assessment without asking for the outcome itself.",
            "",
            "`CANDIDATE_CORE` variables are complete or nearly complete and straightforward to interpret. `CANDIDATE_CONDITIONAL` variables are defensible but require routing-aware preprocessing or a documented temporal limitation in Phase 3. Candidate status is not a guarantee of final inclusion; Phase 6 will finalize engineered modelling matrices.",
            "",
            "## Model 1 - Financial inclusion (`account_fin`)",
            "",
            *render_candidate_table(rows, 1),
            "",
            "Model 1 deliberately excludes `account_mob`, the combined `account` indicator, all financial-account behaviours, target-screened questions, and constructed payment outcomes. Its blueprint emphasizes demographic, socioeconomic, identity, and interpretable digital-access characteristics.",
            "",
            "## Model 2 - Mobile-money adoption (`account_mob`)",
            "",
            *render_candidate_table(rows, 2),
            "",
            "Model 2 deliberately excludes `account_fin`, mobile-money ownership questions, mobile-money transaction behaviours, and constructed digital-payment outcomes. It permits a broader conditional digital-capability set than Model 1 because mobile-money adoption depends directly on phone and internet capability, while still excluding the outcome itself.",
            "",
            "## Missingness policy for the blueprint",
            "",
            "- 100% missing and constant variables are excluded.",
            "- Variables at or above 50% missingness are excluded from the initial blueprint.",
            "- Routed digital variables below 50% missingness may be conditional candidates; Phase 3 must represent structural not-applicable states explicitly rather than treating them as ordinary random missingness.",
            "- No value is imputed or recoded in Phase 2.",
            "",
        ]
    )


def render_target_review(rows: Sequence[dict[str, object]]) -> str:
    by_name = {str(row["variable"]): row for row in rows}
    lines = [
        "# Phase 2 Target Review",
        "",
        "Both targets are complete constructed indicators in the Eswatini file. The World Bank DDI groups negative, don't-know, and refused responses under the constructed zero category (`No/DK/Ref`), so zero must not be described as a separately observed, pure refusal-free 'No' category.",
        "",
    ]
    for name, title in (("account_fin", "Financial inclusion"), ("account_mob", "Mobile-money adoption")):
        row = by_name[name]
        lines.extend(
            [
                f"## {title} - `{name}`",
                "",
                f"- Official label: {row['label']}",
                f"- Observed distribution: `{row['observed_value_counts']}`",
                f"- Missing: {row['missing_count']} ({float(row['missing_pct']):.2f}%)",
                f"- Codebook definition: {row['definition']}",
                f"- Source: {row['source_url']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Consequences for modelling",
            "",
            "- The targets answer different questions and require separate pipelines and evaluations.",
            "- The combined `account` variable and `dig_account` are excluded from both models because they encode one or both outcomes.",
            "- Payment-receipt and utility-payment variables mentioned in the constructed definitions are excluded as direct reconstruction risks.",
            "- Account-owner and mobile-money-owner questionnaire branches are excluded because their availability itself reveals outcome status.",
            "- Reported rates at this phase are unweighted file distributions, not population estimates.",
            "",
        ]
    )
    return "\n".join(lines)


def render_leakage_review(rows: Sequence[dict[str, object]]) -> str:
    lines = [
        "# Phase 2 Leakage Review",
        "",
        "## Decision hierarchy",
        "",
        "1. Remove the target itself, the parallel outcome, identifiers, metadata, constants, and all-missing fields.",
        "2. Exclude variables used to construct or screen the target (`DIRECT`).",
        "3. Exclude contemporaneous financial behaviours and transactions (`HIGH`).",
        "4. Review recent digital behaviours for temporal overlap (`MODERATE`).",
        "5. Retain only interpretable pre-outcome profile characteristics as core or conditional candidates.",
        "",
        "## Model-specific status counts",
        "",
        f"- Model 1: `{json.dumps(status_counts(rows, 'model1_status'), sort_keys=True)}`",
        f"- Model 2: `{json.dumps(status_counts(rows, 'model2_status'), sort_keys=True)}`",
        "",
        "## High-impact exclusions",
        "",
        "- Model 1 excludes `account_mob` as a parallel financial-access outcome and excludes formal-account ownership, debit-card, account-use, and account-barrier branches as leakage.",
        "- Model 2 excludes `account_fin` as a parallel outcome and excludes all mobile-money ownership, barrier, frequency, transaction, and mobile-payment variables as leakage.",
        "- Both models exclude `account`, `dig_account`, payment receipt modes, and constructed digital-payment measures.",
        "- `internet_use` is retained, while nested source questions `con24` and `con25` are excluded as redundant components.",
        "- `fin24c` is the only `fin*` questionnaire field admitted as a conditional candidate because it measures an exogenous disaster exposure rather than financial adoption or behaviour.",
        "- `fin46` is retained as identity-document access; other ID fields are excluded because they are post-event, highly routed, or entirely missing.",
        "",
    ]
    return "\n".join(lines)


def render_summary(rows: Sequence[dict[str, object]], summary: dict[str, object]) -> str:
    categories = summary["category_counts"]
    return "\n".join(
        [
            "# Phase 2 Data Dictionary and Eligibility Summary",
            "",
            f"- Variables documented: **{len(rows)}**",
            f"- Primary categories: `{json.dumps(categories, sort_keys=True)}`",
            f"- Model 1 candidates: **{summary['model1_candidate_count']}**",
            f"- Model 2 candidates: **{summary['model2_candidate_count']}**",
            f"- Variables at least 50% missing: **{summary['high_missing_count']}**",
            f"- All-missing variables: **{summary['all_missing_count']}**",
            "",
            "The complete row-level decisions are in `data_dictionary.csv` and `feature_eligibility.csv`. Every variable has a category, coverage record, source URL, Model 1 decision, Model 2 decision, leakage rating, and reason.",
            "",
            "## Source and scope decisions",
            "",
            f"- World Bank reference: `{REFERENCE_ID}`",
            "- The 2024 survey year is confirmed by the DDI and dataset, while the publication/database edition is Global Findex 2025.",
            "- The CSV variable `internet_use` corresponds to `internet` in the PDF codebook; the DDI uses `internet_use`, confirming the file-specific name.",
            "- Raw microdata and source PDFs/XML remain Git-ignored under the Microdata Library terms.",
            "- No modelling or Phase 3 data cleaning was performed.",
            "",
        ]
    )


def render_source_notes(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Phase 2 Source and Publication Notes",
            "",
            "## Official source",
            "",
            "- Producer: Development Research Group, Finance and Private Sector Development Unit, World Bank",
            "- Dataset: Eswatini - The Global Findex Database 2025: Connectivity and Financial Inclusion in the Digital Economy",
            f"- Reference ID: `{REFERENCE_ID}`",
            f"- DOI: {DOI_URL}",
            f"- Catalog: {CATALOG_URL}",
            f"- Related materials: {RELATED_MATERIALS_URL}",
            f"- DDI/XML metadata: {DDI_URL}",
            "",
            "## Publication safeguards",
            "",
            "The World Bank Microdata Library terms restrict redistribution, require statistical/scientific use, prohibit respondent-identification attempts, and require dataset citation. Raw data and local PDF/XML references are therefore Git-ignored. Before publishing the repository, the owner should confirm whether the generated dictionary's source-derived text is acceptable for redistribution or should be reduced to labels, classifications, and source links only.",
            "",
            "Recommended dataset acknowledgment:",
            "",
            f"> Development Research Group, Finance and Private Sector Development Unit (World Bank). Eswatini - The Global Findex Database 2025: Connectivity and Financial Inclusion in the Digital Economy (FINDEX 2025). Ref: {REFERENCE_ID}. Downloaded from the World Bank Microdata Library.",
            "",
            "## Integrity hashes",
            "",
            f"- Raw CSV: `{summary['source_hashes']['raw_csv_sha256']}`",
            f"- DDI/XML: `{summary['source_hashes']['ddi_xml_sha256']}`",
            f"- Microdata codebook PDF: `{summary['source_hashes']['codebook_pdf_sha256']}`",
            "",
        ]
    )


def write_outputs(
    rows: Sequence[dict[str, object]],
    output_dir: Path,
    raw_path: Path,
    ddi_path: Path,
    codebook_path: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "data_dictionary.csv", rows)

    eligibility_fields = [
        "position",
        "variable",
        "label",
        "primary_category",
        "tags",
        "missing_pct",
        "missingness_band",
        "model1_status",
        "model1_available_pre_outcome",
        "model1_leakage_risk",
        "model1_leakage_basis",
        "model1_reason",
        "model2_status",
        "model2_available_pre_outcome",
        "model2_leakage_risk",
        "model2_leakage_basis",
        "model2_reason",
        "source_url",
    ]
    write_csv(output_dir / "feature_eligibility.csv", rows, eligibility_fields)
    write_csv(
        output_dir / "candidate_features_model1.csv",
        [row for row in rows if str(row["model1_status"]).startswith("CANDIDATE")],
        eligibility_fields,
    )
    write_csv(
        output_dir / "candidate_features_model2.csv",
        [row for row in rows if str(row["model2_status"]).startswith("CANDIDATE")],
        eligibility_fields,
    )

    summary = {
        "phase": 2,
        "reference_id": REFERENCE_ID,
        "doi": DOI_URL,
        "catalog_url": CATALOG_URL,
        "related_materials_url": RELATED_MATERIALS_URL,
        "variable_count": len(rows),
        "category_counts": status_counts(rows, "primary_category"),
        "model1_status_counts": status_counts(rows, "model1_status"),
        "model2_status_counts": status_counts(rows, "model2_status"),
        "model1_candidate_count": sum(str(row["model1_status"]).startswith("CANDIDATE") for row in rows),
        "model2_candidate_count": sum(str(row["model2_status"]).startswith("CANDIDATE") for row in rows),
        "high_missing_count": sum(float(row["missing_pct"]) >= 50 for row in rows),
        "all_missing_count": sum(float(row["missing_pct"]) == 100 for row in rows),
        "source_hashes": {
            "raw_csv_sha256": file_hash(raw_path),
            "ddi_xml_sha256": file_hash(ddi_path),
            "codebook_pdf_sha256": file_hash(codebook_path),
        },
        "target_distributions": {
            str(row["variable"]): json.loads(str(row["observed_value_counts"]))
            for row in rows
            if row["variable"] in TARGETS
        },
        "scope_note": "No cleaning, preprocessing, feature engineering, splitting, statistical testing, or modelling was performed.",
    }
    (output_dir / "phase2_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "phase2_summary.md").write_text(render_summary(rows, summary), encoding="utf-8")
    (output_dir / "feature_blueprint.md").write_text(render_feature_blueprint(rows), encoding="utf-8")
    (output_dir / "target_review.md").write_text(render_target_review(rows), encoding="utf-8")
    (output_dir / "leakage_review.md").write_text(render_leakage_review(rows), encoding="utf-8")
    (output_dir / "source_notes.md").write_text(render_source_notes(summary), encoding="utf-8")
    return summary


def run(
    raw_path: Path = DEFAULT_INPUT,
    profile_path: Path = DEFAULT_PHASE1_PROFILE,
    ddi_path: Path = DEFAULT_DDI,
    codebook_path: Path = DEFAULT_CODEBOOK,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    ensure_reference(ddi_path, DDI_URL)
    ensure_reference(codebook_path, CODEBOOK_URL)
    rows = build_dictionary(raw_path, profile_path, ddi_path, codebook_path)
    return write_outputs(rows, output_dir, raw_path, ddi_path, codebook_path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--phase1-profile", type=Path, default=DEFAULT_PHASE1_PROFILE)
    parser.add_argument("--ddi", type=Path, default=DEFAULT_DDI)
    parser.add_argument("--codebook", type=Path, default=DEFAULT_CODEBOOK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run(
        raw_path=args.raw.resolve(),
        profile_path=args.phase1_profile.resolve(),
        ddi_path=args.ddi.resolve(),
        codebook_path=args.codebook.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
