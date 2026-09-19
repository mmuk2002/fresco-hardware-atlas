"""Measure source-page component box coverage against independent gold labels."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

from hardware_sets.evaluation import match_components


def main() -> None:
    root = Path("Fresco Coding Challenge (Hardware Sets)")
    summary = json.loads(Path("output/corpus/summary.json").read_text(encoding="utf-8"))
    docs = {row["source_path"]: row for row in summary["documents"]}
    gold = json.loads(Path("tests/fixtures/heldout_gold.json").read_text(encoding="utf-8"))
    checked, failures = [], []
    for expected in gold:
        source = expected["source_path"]
        predicted = json.loads((Path("output/corpus") / docs[source]["output_file"]).read_text(encoding="utf-8"))
        pages = set(expected.get("pages", [expected.get("page")]))
        candidates = [item for item in predicted["sets"] if item["set_number"] == expected["set_number"]
                      and pages & {location["page"] for location in item["locations"]}]
        if len(candidates) != 1:
            raise AssertionError(f"Set identity ambiguous: {source} {expected['set_number']}")
        rows = [component for component in candidates[0]["components"] if pages &
                {location["page"] for location in component["locations"]}]
        assignment = match_components(expected["components"], rows)
        with pymupdf.open(root / source) as pdf:
            for index, gold_row in enumerate(expected["components"]):
                if index not in assignment:
                    failures.append((source, expected["set_number"], index + 1, "unmatched"))
                    continue
                row = rows[assignment[index]]
                # One independently transcribed word of length >=4 is enough to
                # prove that the row box points to the correct printed item.
                tokens = [word for word in re.findall(r"[A-Za-z0-9]+", gold_row["description"])
                          if len(word) >= 4]
                covered = False
                for location in row["locations"]:
                    if location["page"] not in pages:
                        continue
                    page = pdf[location["page"] - 1]
                    box = pymupdf.Rect(location["bbox"])
                    for token in tokens:
                        for anchor in page.search_for(token):
                            intersection = anchor & box
                            if intersection.width * intersection.height >= .8 * anchor.width * anchor.height:
                                covered = True
                                break
                        if covered:
                            break
                (checked if covered else failures).append((source, expected["set_number"], index + 1))
    result = {
        "scope": "Independent gold-description word intersecting the component PDF bounding box on the annotated page",
        "rows_checked": len(checked) + len(failures), "rows_located": len(checked),
        "coverage": len(checked) / (len(checked) + len(failures)),
        "failures": failures,
    }
    Path("docs/validation/evaluation-holdout-component-locations.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(f"Located {len(checked)}/{len(checked) + len(failures)} independently labeled component rows")
    if failures:
        print(f"Unlocated examples: {failures[:8]}")


if __name__ == "__main__":
    main()
