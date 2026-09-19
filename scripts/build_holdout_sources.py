"""Render the fixed, prediction-blind holdout pages for source transcription.

This script deliberately has no dependency on extraction results. The pages were
selected with ``random.Random(87100)`` from the audited schedule ranges.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pymupdf


SELECTION = [
    ("81-85 Bridgeport/08-70-00-Hardware-Schedule.pdf", 22),
    ("HFH DG - HOSPITAL/08 71 00 - DOOR HARDWARE.pdf", 181),
    ("Morris Bank/030f2d1d-Morris_Bank_Macon_-Spec_Manual_Issued_for_Const._1-26-26_FULL_SPECS.pdf", 251),
    ("SAT TDP/2025.12.19 - SAT TDP - Project Manual.pdf", 807),
    ("SJC Well Behavioral/89671ede-20260218_SJC_BeWell_Bldg_B_85__DESIGN_UPDATE_-_SPECIFICATIONS.pdf", 740),
    ("StarHardware/9839d1a1-Division_8_Specs_-_Commons_Lane.pdf", 101),
    ("The Door Company _Copy_/Vantage TX-22 Div 01, 08.pdf", 418),
    ("Village of Oswego New Public Works Facility  _Copy_/SPECIFICATIONS VOLUME 1.pdf", 437),
]


def main() -> None:
    source_root = Path("Fresco Coding Challenge (Hardware Sets)")
    output = Path("tmp/pdfs/holdout")
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, (relative, page_number) in enumerate(SELECTION, 1):
        source = source_root / relative
        with pymupdf.open(source) as document:
            page = document[page_number - 1]
            stem = f"{index:02d}-{source.parent.name}-{page_number}".replace(" ", "_")
            text_path = output / f"{stem}.txt"
            image_path = output / f"{stem}.png"
            text_path.write_text(page.get_text("text", sort=True), encoding="utf-8")
            page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(image_path)
            manifest.append({
                "source_path": relative,
                "page": page_number,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "text_file": text_path.as_posix(),
                "image_file": image_path.as_posix(),
            })
    (output / "selection.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    evidence = {"selection_seed": 87100, "selection_scope": "One page chosen from each of eight predeclared audited schedule ranges before inspecting predictions",
                "pages": [{key: row[key] for key in ("source_path", "page", "source_sha256")} for row in manifest]}
    Path("docs/validation/heldout-selection.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Rendered {len(manifest)} fixed holdout pages to {output}")


if __name__ == "__main__":
    main()
