"""Exhaustively verify extracted rows against source PDF geometry and text.

This is an independent source-grounding audit, not a substitute for a human
gold transcription. It checks every saved set/component row in the corpus.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import pymupdf


ROOT = Path("Fresco Coding Challenge (Hardware Sets)")
CORPUS = Path("output/corpus")
TOKEN = re.compile(r"[A-Za-z0-9]+")


def tokens(value: str | None) -> list[str]:
    return [item.casefold() for item in TOKEN.findall(value or "") if len(item) >= 2]


def compact(value: str) -> str:
    return "".join(character.casefold() for character in value if character.isalnum())


def words_in_box(page: pymupdf.Page, box: list[float]) -> list[str]:
    rect = pymupdf.Rect(box)
    return [item[4].casefold() for item in page.get_text("words") if rect.intersects(pymupdf.Rect(item[:4]))]


def overlap(expected: list[str], observed: list[str]) -> int:
    available = Counter(compact(item) for item in observed)
    matched = 0
    for item in expected:
        needle = compact(item)
        hit = next((candidate for candidate in available if candidate and available[candidate] and (needle == candidate or needle in candidate or candidate in needle)), None)
        if hit is not None:
            matched += 1
            available[hit] -= 1
    return matched


def main() -> None:
    summary = json.loads((CORPUS / "summary.json").read_text(encoding="utf-8"))
    metrics = Counter()
    failures: list[dict[str, object]] = []
    for document in summary["documents"]:
        source = document["source_path"]
        result_path = CORPUS / document["output_file"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        source_path = ROOT / source
        with pymupdf.open(source_path) as pdf:
            page_words = {index + 1: [word[4].casefold() for word in page.get_text("words")] for index, page in enumerate(pdf)}
            for hardware_set in result.get("sets", []):
                metrics["sets"] += 1
                set_pages = {location["page"] for location in hardware_set.get("locations", [])}
                if not set_pages:
                    failures.append({"source": source, "set": hardware_set.get("set_number"), "kind": "set_without_location"})
                for component in hardware_set.get("components", []):
                    metrics["components"] += 1
                    locations = component.get("locations", [])
                    if not locations:
                        failures.append({"source": source, "set": hardware_set.get("set_number"), "kind": "component_without_location", "description": component.get("description")})
                        continue
                    observed: list[str] = []
                    valid_box = True
                    for location in locations:
                        page_number = location["page"]
                        if page_number < 1 or page_number > len(pdf):
                            valid_box = False
                            continue
                        page = pdf[page_number - 1]
                        rect = pymupdf.Rect(location["bbox"])
                        if rect.x0 < -1 or rect.y0 < -1 or rect.x1 > page.rect.width + 1 or rect.y1 > page.rect.height + 1 or rect.is_empty:
                            valid_box = False
                        observed.extend(words_in_box(page, location["bbox"]))
                    if valid_box:
                        metrics["valid_component_boxes"] += 1
                    else:
                        failures.append({"source": source, "set": hardware_set.get("set_number"), "kind": "invalid_component_box", "description": component.get("description")})
                    description = tokens(component.get("description"))
                    description_hits = overlap(description, observed)
                    if description and description_hits >= max(1, math.ceil(len(description) * 0.5)):
                        metrics["description_grounded"] += 1
                    else:
                        failures.append({"source": source, "set": hardware_set.get("set_number"), "kind": "description_not_grounded", "description": component.get("description"), "observed": " ".join(observed[:30])})
                    raw = tokens(component.get("raw_text"))
                    if raw and overlap(raw, observed) >= max(1, math.ceil(len(raw) * 0.5)):
                        metrics["raw_text_grounded"] += 1
                    else:
                        metrics["raw_text_unchecked"] += 1
                    for field, metric in (("catalog_number", "catalog_grounded"), ("mfr", "mfr_grounded"), ("finish", "finish_grounded")):
                        value = tokens(component.get(field))
                        if not value:
                            metrics[f"{field}_missing_or_null"] += 1
                        elif overlap(value, observed) >= 1:
                            metrics[metric] += 1
                        else:
                            failures.append({"source": source, "set": hardware_set.get("set_number"), "kind": f"{field}_not_grounded", "value": component.get(field), "description": component.get("description")})
    report = {"scope": "All saved corpus results", "metrics": dict(metrics), "failure_count": len(failures), "failures": failures[:200]}
    output = Path("docs/validation/corpus-source-grounding.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
