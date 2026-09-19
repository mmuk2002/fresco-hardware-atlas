"""Build a stratified, render-backed manual acceptance sample.

The script deliberately chooses schedule boundaries and interior pages from
every source with candidate hardware pages. It emits a review manifest and
PNG renders; it does not use predictions to choose pages.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf


ROOT = Path("Fresco Coding Challenge (Hardware Sets)")
AUDIT = Path("data/audit/manifest.json")
CORPUS = Path("output/corpus")
OUT = Path("tmp/manual-audit")


def choose(pages: list[int]) -> list[int]:
    if not pages:
        return []
    values = {pages[0], pages[-1], pages[len(pages) // 2]}
    # Include the pages immediately around a schedule's interior midpoint,
    # since page-break continuation is one of the acceptance risks.
    midpoint = pages[len(pages) // 2]
    values.update(page for page in (midpoint - 1, midpoint + 1) if page in pages)
    return sorted(values)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pages").mkdir(exist_ok=True)
    manifest = json.loads(AUDIT.read_text(encoding="utf-8"))
    summary = json.loads((CORPUS / "summary.json").read_text(encoding="utf-8"))
    by_source = {row["source_path"]: row for row in summary["documents"]}
    rows = []
    for source in manifest:
        pages = choose(source.get("candidate_pages", []))
        if not pages:
            continue
        relative = source["path"].replace("\\", "/")
        result_path = CORPUS / by_source[relative]["output_file"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        source_path = ROOT / relative
        with pymupdf.open(source_path) as pdf:
            for page_number in pages:
                page = pdf[page_number - 1]
                text = page.get_text("text")
                page_sets = [item for item in result["sets"] if any(loc["page"] == page_number for loc in item["locations"])]
                image_path = OUT / "pages" / f"{source['id']}-p{page_number:04d}.png"
                pix = page.get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False)
                pix.save(image_path)
                rows.append({
                    "source_path": relative,
                    "source_id": source["id"],
                    "page": page_number,
                    "image": str(image_path).replace("\\", "/"),
                    "set_numbers": [item["set_number"] for item in page_sets],
                    "component_count": sum(len(item["components"]) for item in page_sets),
                    "text_excerpt": re.sub(r"\\s+", " ", text).strip()[:500],
                    "manual_status": "REVIEW",
                })
    (OUT / "sample-manifest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"schedule_documents": len({row['source_id'] for row in rows}), "sample_pages": len(rows), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
