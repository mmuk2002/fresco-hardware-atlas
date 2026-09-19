"""Independent, geometry-based semantic proxy audit for all extracted rows.

It reads source words and nearby column headers directly from PDFs, then checks
whether predicted manufacturer/finish values occupy the source column labelled
for that field. It is deliberately separate from the extraction code. It is a
proxy for human review, not a replacement for independently typed gold labels.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

ROOT = Path("Fresco Coding Challenge (Hardware Sets)")
CORPUS = Path("output/corpus")
WORD_RE = re.compile(r"[A-Za-z0-9]+")


def compact(value: str | None) -> str:
    return "".join(ch.casefold() for ch in (value or "") if ch.isalnum())


def find_value(words: list[tuple], value: str | None, row: pymupdf.Rect) -> list[tuple]:
    parts = WORD_RE.findall(value or "")
    target = next((part for part in parts if part.isdigit()), parts[0] if parts else "")
    needle = compact(target)
    if not needle or (value or "").strip() in {"--", "---", "__"}:
        return []
    hits = []
    for word in words:
        rect = pymupdf.Rect(word[:4])
        if not row.intersects(rect):
            continue
        candidate = compact(word[4])
        if candidate and (needle == candidate or needle in candidate or candidate in needle):
            hits.append(word)
    return hits


def header_positions(page: pymupdf.Page) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    mfr, finish = [], []
    for word in page.get_text("words"):
        text = compact(word[4])
        if text in {"mfr", "manufacturer", "manufacturers"}:
            mfr.append(((word[0] + word[2]) / 2, word[1]))
        if text in {"finish", "finishes"}:
            finish.append(((word[0] + word[2]) / 2, word[1]))
    return mfr, finish


def main() -> None:
    summary = json.loads((CORPUS / "summary.json").read_text(encoding="utf-8"))
    metrics = Counter()
    unresolved: list[dict[str, object]] = []
    for document in summary["documents"]:
        source = document["source_path"]
        result = json.loads((CORPUS / document["output_file"]).read_text(encoding="utf-8"))
        with pymupdf.open(ROOT / source) as pdf:
            pages_needed = sorted({loc["page"] for item in result.get("sets", []) for component in item.get("components", []) for loc in component.get("locations", [])})
            cache: dict[int, tuple[list[tuple], list[float], list[float]]] = {}
            for page_number in pages_needed:
                page = pdf[page_number - 1]
                cache[page_number] = (page.get_text("words"), *header_positions(page))
            for hardware_set in result.get("sets", []):
                for component in hardware_set.get("components", []):
                    metrics["components"] += 1
                    for location in component.get("locations", []):
                        page_number = location["page"]
                        words, mfr_headers, finish_headers = cache[page_number]
                        row = pymupdf.Rect(location["bbox"])
                        mfr_blank = not compact(component.get("mfr")) or (component.get("mfr") or "").strip() in {"--", "---", "__"}
                        finish_blank = not compact(component.get("finish")) or (component.get("finish") or "").strip() in {"--", "---", "__"}
                        if mfr_blank and finish_blank:
                            metrics["explicit_blank_fields"] += 1
                            continue
                        # Use the nearest header line above this row. This avoids
                        # treating a manufacturer legend or prose reference on
                        # another part of the page as the active column header.
                        header_y = [y for _, y in (*mfr_headers, *finish_headers) if y <= row.y0 + 2]
                        if header_y and row.y0 - max(header_y) <= 140:
                            active_y = max(header_y)
                            mfr_headers = [(x, y) for x, y in mfr_headers if abs(y - active_y) <= 4]
                            finish_headers = [(x, y) for x, y in finish_headers if abs(y - active_y) <= 4]
                        else:
                            mfr_headers = []
                            finish_headers = []
                        mfr_hits = find_value(words, component.get("mfr"), row)
                        finish_hits = find_value(words, component.get("finish"), row)
                        if component.get("mfr") and component.get("finish") and not (mfr_blank or finish_blank):
                            if not mfr_hits or not finish_hits:
                                metrics["field_position_unresolved"] += 1
                                unresolved.append({"source": source, "page": page_number, "set": hardware_set["set_number"], "description": component.get("description"), "kind": "value_not_located"})
                                continue
                            mfr_x = sum((w[0] + w[2]) / 2 for w in mfr_hits) / len(mfr_hits)
                            finish_x = sum((w[0] + w[2]) / 2 for w in finish_hits) / len(finish_hits)
                            if mfr_headers and finish_headers:
                                mfr_header = min(mfr_headers, key=lambda item: abs(item[0] - mfr_x))[0]
                                finish_header = min(finish_headers, key=lambda item: abs(item[0] - finish_x))[0]
                                mfr_positions = [(w[0] + w[2]) / 2 for w in mfr_hits]
                                finish_positions = [(w[0] + w[2]) / 2 for w in finish_hits]
                                best_mfr, best_finish = min(((mx, fx) for mx in mfr_positions for fx in finish_positions), key=lambda pair: abs(pair[0] - mfr_header) + abs(pair[1] - finish_header))
                                if abs(best_mfr - mfr_header) <= 35 and abs(best_finish - finish_header) <= 35:
                                    metrics["mfr_finish_column_confirmed"] += 1
                                else:
                                    metrics["mfr_finish_column_exception"] += 1
                                    unresolved.append({"source": source, "page": page_number, "set": hardware_set["set_number"], "description": component.get("description"), "kind": "column_role_exception", "mfr": component.get("mfr"), "finish": component.get("finish")})
                            else:
                                metrics["mfr_finish_geometry_located"] += 1
                            continue
                        if component.get("mfr") or component.get("finish"):
                            metrics["single_field_geometry_located"] += 1
    report = {"scope": "All non-null mfr/finish fields in all saved corpus results", "metrics": dict(metrics), "exception_count": len(unresolved), "exceptions": unresolved[:200]}
    path = Path("docs/validation/corpus-semantic-proxy.json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(1 if unresolved else 0)


if __name__ == "__main__":
    main()
