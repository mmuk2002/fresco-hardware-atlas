"""Honest, annotation-scoped extraction evaluation with one-to-one matching.

The fixture is a sample, not a complete corpus inventory. Unannotated sets are
never counted as false positives. Components are scored only inside annotated
sets and pages. Missing rows count as wrong for every annotated field, including
null fields, so failures cannot inflate scores by matching absent values.
"""

from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

FIELDS = ("qty", "description", "catalog_number", "mfr", "finish", "notes")


def normalize(value: Any, field: str = "") -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    text = unicodedata.normalize("NFKC", str(value)).translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
    }))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    if not text:
        return None
    if field == "qty":
        try:
            number = Decimal(text)
            if number.is_finite():
                return str(number.normalize())
        except InvalidOperation:
            pass
    return text


def _path(value: str) -> str:
    return re.sub(r"/+", "/", value.replace("\\", "/")).strip("/").casefold()


def _source_matches(left: str, right: str) -> bool:
    left, right = _path(left), _path(right)
    return left == right or left.endswith("/" + right) or right.endswith("/" + left)


def load_gold(path: str | Path) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("sets")
    if not isinstance(value, list) or not value:
        raise ValueError("Gold data must be a nonempty list of annotated sets")
    seen: set[tuple[Any, ...]] = set()
    for item in value:
        if not all(key in item for key in ("source_path", "set_number", "components")):
            raise ValueError("Each gold set needs source_path, set_number, and components")
        pages = item.get("pages", [item.get("page")])
        if not pages or any(not isinstance(page, int) or page < 1 for page in pages):
            raise ValueError("Each gold set needs one-based page or pages")
        identity = (_path(item["source_path"]), tuple(sorted(pages)), normalize(item["set_number"]))
        if identity in seen:
            raise ValueError(f"Duplicate gold annotation: {identity}")
        seen.add(identity)
    return value


def load_corpus(directory: str | Path) -> list[dict[str, Any]]:
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Corpus output directory does not exist: {directory}")
    values = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "summary.json":
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "source_path" in value and isinstance(value.get("sets"), list):
            values.append(value)
    return values


def _ratio(left: Any, right: Any) -> float:
    left, right = normalize(left), normalize(right)
    return SequenceMatcher(None, left, right).ratio() if left and right else 0.0


def _row_similarity(gold: dict[str, Any], predicted: dict[str, Any]) -> float:
    description = _ratio(gold.get("description"), predicted.get("description"))
    catalog = _ratio(gold.get("catalog_number"), predicted.get("catalog_number"))
    # Quantity/manufacturer/finish agreement alone cannot establish row identity.
    if description < 0.5 and catalog < 0.7:
        return 0.0
    exact_identity = int(description == 1) + int(catalog == 1)
    tie_breaker = sum(normalize(gold.get(field), field) == normalize(predicted.get(field), field)
                      for field in ("qty", "mfr", "finish")) / 100
    return 2 * description + 2 * catalog + exact_identity + tie_breaker


def match_components(gold: list[dict[str, Any]], predicted: list[dict[str, Any]]) -> dict[int, int]:
    """Maximum-weight bipartite assignment, with dummy columns for missing rows.

    Hungarian assignment is implemented here to avoid a scientific-stack runtime
    dependency. Every prediction can be used at most once, including duplicates.
    """
    if not gold or not predicted:
        return {}
    scores = [[_row_similarity(expected, actual) for actual in predicted] for expected in gold]
    n, m = len(gold), len(predicted) + len(gold)
    costs = [[-score for score in row] + [0.0] * n for row in scores]
    u, v, p, way = [0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minimum, used = [float("inf")] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float("inf"), 0
            for j in range(1, m + 1):
                if not used[j]:
                    current = costs[i0 - 1][j - 1] - u[i0] - v[j]
                    if current < minimum[j]:
                        minimum[j], way[j] = current, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return {p[j] - 1: j - 1 for j in range(1, len(predicted) + 1)
            if p[j] and scores[p[j] - 1][j - 1] > 0}


def _metric(correct: int, total: int) -> dict[str, Any]:
    return {"correct": correct, "total": total, "accuracy": correct / total if total else None}


def _pages(item: dict[str, Any]) -> set[int]:
    return {location["page"] for location in item.get("locations", []) if "page" in location}


def evaluate(gold: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate only the reviewed sample; return denominators and row-level errors."""
    fields = {field: [0, 0] for field in FIELDS}
    set_fields = {field: [0, 0] for field in ("description", "status", "notes")}
    detected = expected_rows = matched_rows = predicted_rows = whole_rows = swaps = 0
    used_sets: set[tuple[int, int, tuple[int, ...]]] = set()
    details = []
    for expected in gold:
        annotated_pages = set(expected.get("pages", [expected.get("page")]))
        documents = [(index, document) for index, document in enumerate(predictions)
                     if _source_matches(expected["source_path"], document.get("source_path", ""))]
        if len(documents) > 1:
            raise ValueError(f"Multiple result documents match {expected['source_path']}; use one corpus run")
        candidates = []
        for doc_index, document in documents:
            for set_index, candidate in enumerate(document.get("sets", [])):
                identity = (doc_index, set_index, tuple(sorted(annotated_pages)))
                if identity not in used_sets and normalize(candidate.get("set_number")) == normalize(expected["set_number"]):
                    overlap = _pages(candidate) & annotated_pages
                    if overlap:
                        candidates.append((len(overlap), identity, candidate))
        candidates.sort(key=lambda item: -item[0])
        actual = candidates[0][2] if candidates else None
        if candidates:
            used_sets.add(candidates[0][1])
        detected += actual is not None
        expected_components = expected.get("components", [])
        # A page sample does not annotate components on continuation pages.
        actual_components = [item for item in actual.get("components", [])
                             if not _pages(item) or _pages(item) & annotated_pages] if actual else []
        assignment = match_components(expected_components, actual_components)
        expected_rows += len(expected_components)
        matched_rows += len(assignment)
        predicted_rows += len(actual_components)
        errors = []
        for row_index, row in enumerate(expected_components):
            actual_index = assignment.get(row_index)
            predicted = actual_components[actual_index] if actual_index is not None else None
            differences = {}
            annotated_fields = [field for field in FIELDS if field in row]
            for field in annotated_fields:
                fields[field][1] += 1
                correct = predicted is not None and normalize(row.get(field), field) == normalize(predicted.get(field), field)
                fields[field][0] += correct
                if not correct:
                    differences[field] = {"expected": row.get(field), "actual": predicted.get(field) if predicted else None}
            whole_rows += predicted is not None and not differences
            is_swap = bool(predicted and normalize(row.get("mfr")) and normalize(row.get("finish"))
                           and normalize(row.get("mfr")) != normalize(row.get("finish"))
                           and normalize(row.get("mfr")) == normalize(predicted.get("finish"))
                           and normalize(row.get("finish")) == normalize(predicted.get("mfr")))
            swaps += is_swap
            if differences or predicted is None:
                errors.append({"gold_row": row_index + 1,
                               "predicted_row": actual_index + 1 if actual_index is not None else None,
                               "differences": differences, "mfr_finish_swap": is_swap})
        heading_errors = {}
        for field, counts in set_fields.items():
            if field in expected:
                counts[1] += 1
                correct = actual is not None and normalize(expected.get(field)) == normalize(actual.get(field))
                counts[0] += correct
                if not correct:
                    heading_errors[field] = {"expected": expected[field], "actual": actual.get(field) if actual else None}
        details.append({"source_path": expected["source_path"], "pages": sorted(annotated_pages),
                        "set_number": expected["set_number"], "detected": actual is not None,
                        "gold_components": len(expected_components), "predicted_components": len(actual_components),
                        "matched_components": len(assignment),
                        "extra_predicted_rows": [index + 1 for index in range(len(actual_components)) if index not in assignment.values()],
                        "set_field_errors": heading_errors, "component_errors": errors})
    return {
        "scope": "Reviewed set/page annotations only; unannotated sets are excluded. This is not corpus-wide accuracy.",
        "normalization": "Unicode NFKC, case, whitespace, typographic quotes/dashes; numeric quantity equivalence. No manufacturer aliases or code expansion.",
        "matching": "Exact normalized set number with page overlap; one-to-one maximum-weight component identity matching (description/catalog).",
        "annotated_documents": len({_path(item["source_path"]) for item in gold}),
        "annotated_pages": len({(_path(item["source_path"]), page) for item in gold for page in item.get("pages", [item.get("page")])}),
        "set_detection": {"matched": detected, "gold": len(gold), "recall": detected / len(gold) if gold else None,
                          "precision": None, "precision_note": "Requires exhaustive set annotations; unavailable for a sampled fixture."},
        "components": {"matched": matched_rows, "gold": expected_rows, "predicted_in_annotated_sets": predicted_rows,
                       "recall": matched_rows / expected_rows if expected_rows else None,
                       "precision": matched_rows / predicted_rows if predicted_rows else None},
        "fields": {field: _metric(*counts) for field, counts in fields.items()},
        "whole_row": _metric(whole_rows, expected_rows),
        "set_fields": {field: _metric(*counts) for field, counts in set_fields.items()},
        "mfr_finish_swaps": swaps,
        "details": details,
    }
