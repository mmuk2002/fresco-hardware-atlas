"""Check independently read heading locations on the fixed holdout pages.

Each listed heading comes from the source-page render, including headers whose
component rows continue beyond a sampled page. Predictions are only loaded when
this script runs; they are never used to build the source labels.
"""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf


HEADINGS = {
    "81-85 Bridgeport/08-70-00-Hardware-Schedule.pdf": [
        (22, "37", "Heading #37"), (22, "38", "Heading #38"), (22, "39", "Heading #39"),
    ],
    "HFH DG - HOSPITAL/08 71 00 - DOOR HARDWARE.pdf": [
        (180, "266", "Hardware Group No.266"), (180, "267", "Hardware Group No.267"),
        (181, "268", "Hardware Group No.268"),
    ],
    "Morris Bank/030f2d1d-Morris_Bank_Macon_-Spec_Manual_Issued_for_Const._1-26-26_FULL_SPECS.pdf": [
        (251, "203", "Set #203"),
    ],
    "SAT TDP/2025.12.19 - SAT TDP - Project Manual.pdf": [
        (807, "E210T", "Hardware Group No. E210T"),
        (807, "E210TW", "Hardware Group No. E210TW"),
    ],
    "SJC Well Behavioral/89671ede-20260218_SJC_BeWell_Bldg_B_85__DESIGN_UPDATE_-_SPECIFICATIONS.pdf": [
        (740, "E11", "HW E11"),
    ],
    "StarHardware/9839d1a1-Division_8_Specs_-_Commons_Lane.pdf": [
        (101, "31", "Hardware Group/Set #31"),
    ],
    "The Door Company _Copy_/Vantage TX-22 Div 01, 08.pdf": [
        (418, "D201", "HARDWARE GROUP NO. D201"),
        (418, "D204Z", "HARDWARE GROUP NO. D204Z"),
        (419, "D705DXZ", "HARDWARE GROUP NO. D705DXZ"),
        (419, "D714DXZ", "HARDWARE GROUP NO. D714DXZ"),
    ],
    "Village of Oswego New Public Works Facility  _Copy_/SPECIFICATIONS VOLUME 1.pdf": [
        (437, "44", "HARDWARE GROUP NO. 44"), (437, "45", "HARDWARE GROUP NO. 45"),
    ],
}


def main() -> None:
    root = Path("Fresco Coding Challenge (Hardware Sets)")
    summary = json.loads(Path("output/corpus/summary.json").read_text(encoding="utf-8"))
    documents = {item["source_path"]: item for item in summary["documents"]}
    checked = []
    for source, headings in HEADINGS.items():
        result = json.loads((Path("output/corpus") / documents[source]["output_file"]).read_text(encoding="utf-8"))
        pages = {page for page, _, _ in headings}
        expected = {(page, number) for page, number, _ in headings}
        predicted = {(item["locations"][0]["page"], item["set_number"])
                     for item in result["sets"] if item["locations"] and item["locations"][0]["page"] in pages}
        if expected != predicted:
            raise AssertionError(f"Unexpected set headings in {source}: missing={expected-predicted}, extra={predicted-expected}")
        with pymupdf.open(root / source) as pdf:
            for page_number, number, text in headings:
                page = pdf[page_number - 1]
                hits = page.search_for(text)
                # "E210T" is a prefix of "E210TW" lower on the same page.
                if source.startswith("SAT TDP/") and number == "E210T" and len(hits) == 2:
                    hits = [min(hits, key=lambda hit: hit.y0)]
                if len(hits) != 1:
                    raise AssertionError(f"Heading anchor ambiguous or missing: {source}:{page_number} {text!r} ({len(hits)} hits)")
                hardware_set = next(item for item in result["sets"] if item["set_number"] == number
                                    and item["locations"][0]["page"] == page_number)
                location = next(item for item in hardware_set["locations"] if item["page"] == page_number)
                box = pymupdf.Rect(location["bbox"])
                anchor = hits[0]
                intersect = box & anchor
                overlap = max(0, intersect.width * intersect.height) / (anchor.width * anchor.height)
                if overlap < .90:
                    raise AssertionError(f"Heading outside set location: {source}:{page_number} {number}: {overlap:.3f}")
                if not (0 <= box.x0 < box.x1 <= page.rect.width and 0 <= box.y0 < box.y1 <= page.rect.height):
                    raise AssertionError(f"Set box outside page: {source}:{page_number} {number}")
                checked.append({"source_path": source, "page": page_number, "set_number": number,
                                "heading_coverage": round(overlap, 4), "bbox": location["bbox"]})
    output = {"scope": "Every printed set heading on the eight fixed holdout pages plus adjacent continuation pages; independent source text anchors",
              "expected_headings": len(checked), "matched_headings": len(checked),
              "heading_precision": 1.0, "heading_recall": 1.0,
              "heading_box_minimum_coverage": min(item["heading_coverage"] for item in checked),
              "details": checked}
    target = Path("docs/validation/evaluation-holdout-locations.json")
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Verified {len(checked)}/{len(checked)} source headings and all physical-page boxes")


if __name__ == "__main__":
    main()
