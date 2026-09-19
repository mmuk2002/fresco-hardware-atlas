"""Extract ruled schedules whose set descriptions occupy vertically merged cells.

The column labels, rather than document identity or isolated code values, select
this parser. PyMuPDF's cell geometry keeps wrapped products and right-hand notes
together even when a merged set description spans several component rows.
"""
from __future__ import annotations

import hashlib
import re

from .models import Component, HardwareSet, Location


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _header(row: list[str | None]) -> dict[str, int] | None:
    roles = {}
    for i, value in enumerate(row):
        text = _clean(value).upper().rstrip(".")
        if text in {"SET", "SET NO", "SET NUMBER", "HARDWARE SET"}:
            roles["set"] = i
        elif text in {"HARDWARE TYPE", "HARDWARE DESCRIPTION", "DESCRIPTION"}:
            roles["description"] = i
        elif "MANUFACTURER" in text and "PRODUCT" in text and len(text) < 60:
            roles["product"] = i
        elif text in {"QTY", "QUANTITY"}:
            roles["qty"] = i
        elif text == "FINISH":
            roles["finish"] = i
        elif text in {"NOTES", "NOTE", "REMARKS"}:
            roles["notes"] = i
    required = {"set", "description", "product", "qty", "finish"}
    return roles if required.issubset(roles) else None


def _box(cells) -> list[float] | None:
    boxes = [cell for cell in cells if cell is not None]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _qty(value: str):
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        number = float(value)
        return int(number) if number.is_integer() else number
    if re.fullmatch(r"\d+/\d+", value):
        return value
    return None


def extract_table_page(pdf_page, page_number: int, source_digest: str) -> list[HardwareSet]:
    """Return sets from a recognized merged-cell schedule, or [] otherwise.

    Locations use one-based physical page numbers and top-left PDF points.
    A missing manufacturer/product separator is retained as unresolved product
    text and flagged instead of guessing a manufacturer from the first token.
    """
    text = pdf_page.get_text()
    # Avoid expensive table discovery on ordinary specification pages.
    if not (re.search(r"MANUFACTURER\s*[-–—]\s*PRODUCT", text, re.I)
            and re.search(r"HARDWARE\s+(?:TYPE|DESCRIPTION)", text, re.I)):
        return []
    tables = pdf_page.find_tables().tables
    result = []
    for table_index, table in enumerate(tables):
        rows = table.extract()
        header_index, roles = None, None
        for index, row in enumerate(rows):
            detected = _header(row)
            if detected:
                header_index, roles = index, detected
                break
        if roles is None:
            continue
        current = None
        for index in range(header_index + 1, len(rows)):
            row = rows[index]
            if _header(row):
                continue
            values = {role: _clean(row[column]) for role, column in roles.items()}
            cells = table.rows[index].cells
            bounds = _box(cells[roles["set"]:])
            if bounds is None:
                continue
            marker = values["set"]
            match = re.fullmatch(r"(?:SET\s*#?\s*)?([A-Z0-9]+(?:[.\-/][A-Z0-9]+)*)(?:\s+((?:NOT USED|N/A|UNUSED).*))?", marker, re.I)
            if match and (any(char.isdigit() for char in match[1]) or match[1].upper() == "MISC"):
                set_number = match[1]
                set_id = hashlib.sha256(f"{source_digest}:table:{page_number}:{table_index}:{index}:{set_number}".encode()).hexdigest()[:16]
                current = HardwareSet(
                    id=set_id, set_number=set_number, description=match[2],
                    status="not_used" if match[2] else "active", confidence=.97,
                    locations=[Location(page=page_number, bbox=bounds,
                                        page_width=pdf_page.rect.width, page_height=pdf_page.rect.height)],
                )
                result.append(current)
            elif current is not None and marker:
                current.description = " ".join(filter(None, [current.description, marker]))
                if re.search(r"\b(?:NOT USED|N/A|UNUSED)\b", marker, re.I):
                    current.status = "not_used"
            if current is None:
                continue
            old = current.locations[0].bbox
            current.locations[0].bbox = _box([old, bounds])
            description, product = values["description"], values["product"]
            notes = values.get("notes", "")
            if not description and not product:
                if notes:
                    current.notes.append(notes)
                continue
            # Split only an explicit separator, preserving further hyphens in a
            # catalog string (e.g. LCN - 4040XP - EDA ARM - METAL COVER).
            split = re.split(r"\s+[-–—]\s+", product, maxsplit=1)
            mfr, catalog = (split[0], split[1]) if len(split) == 2 else (None, product or None)
            warnings = []
            if product and mfr is None:
                warnings.append("Manufacturer/product cell has no explicit separator; manufacturer left null.")
            quantity = _qty(values["qty"])
            if quantity is None:
                warnings.append("Quantity is absent or unspecified in the source.")
            component_bounds = _box([cells[column] for role, column in roles.items() if role != "set"])
            component_id = hashlib.sha256(f"{current.id}:{index}".encode()).hexdigest()[:16]
            current.components.append(Component(
                id=component_id, qty=quantity, description=description,
                catalog_number=catalog, mfr=mfr, finish=values["finish"] or None,
                notes=notes or None, raw_text=" | ".join(values.values()),
                warnings=warnings,
                confidence={"qty": .99, "description": .98, "catalog_number": .98 if mfr else .6,
                            "mfr": .99 if mfr else .35, "finish": .99, "notes": .98},
                locations=[Location(page=page_number, bbox=component_bounds or bounds,
                                    page_width=pdf_page.rect.width, page_height=pdf_page.rect.height)],
            ))
    return result
