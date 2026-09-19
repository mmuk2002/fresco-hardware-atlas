"""Resolve short component codes only from explicit lookup evidence on the page."""
from __future__ import annotations

import re

from .layout import Line, Page, clean, line_location
from .models import CatalogResolution, Component, Location


ROLE_NAMES = {
    "CODE": "code", "KEY": "code", "REF": "code", "REFERENCE": "code",
    "DESCRIPTION": "description", "HARDWARE": "description", "TYPE": "description",
    "CATALOG": "catalog_number", "MODEL": "catalog_number", "PRODUCT": "catalog_number",
    "MFR": "mfr", "MFG": "mfr", "MANUFACTURER": "mfr",
    "FINISH": "finish", "FIN": "finish", "NOTES": "notes", "REMARKS": "notes",
}
SHORT_CODE = re.compile(r"^[A-Z][A-Z0-9]{0,4}$", re.I)


def _header(line: Line) -> dict[str, float] | None:
    roles: dict[str, float] = {}
    for word in line.words:
        token = word.text.upper().strip(".:#()")
        role = ROLE_NAMES.get(token)
        if role and role not in roles:
            roles[role] = word.x0
    return roles if "code" in roles and len(roles) >= 3 else None


def _cells(line: Line, starts: dict[str, float]) -> dict[str, str]:
    ordered = sorted(starts, key=starts.get)
    cells: dict[str, list[str]] = {role: [] for role in ordered}
    for word in line.words:
        role = ordered[0]
        for candidate in ordered:
            if word.x0 >= starts[candidate] - 3:
                role = candidate
        cells[role].append(word.text)
    return {role: clean(" ".join(words)) for role, words in cells.items()}


def find_code_lookups(page: Page) -> dict[str, CatalogResolution]:
    """Read explicit code tables or legend entries; never infer from isolated codes."""
    found: dict[str, CatalogResolution] = {}
    for index, line in enumerate(page.lines):
        roles = _header(line)
        if roles:
            for candidate in page.lines[index + 1:index + 36]:
                if _header(candidate) or re.match(r"^(?:SET|GROUP|HW|HEADING)\b", candidate.text, re.I):
                    break
                cells = _cells(candidate, roles)
                code = cells.get("code", "").upper()
                details = {key: value or None for key, value in cells.items() if key != "code"}
                if not SHORT_CODE.fullmatch(code) or not any(details.values()):
                    continue
                found[code] = CatalogResolution(
                    code=code, **details, location=Location(**line_location(page, [candidate])), confidence=.98,
                )

        if re.search(r"\b(?:CODE|HARDWARE|PRODUCT|CATALOG)\s+(?:KEY|LEGEND)\b", line.text, re.I):
            for candidate in page.lines[index + 1:index + 26]:
                if identify := re.match(r"^\s*(?:CODE\s+)?([A-Z][A-Z0-9]{0,4})\s*(?:=|:|[-–—])\s*(.{3,})$", candidate.text, re.I):
                    code, expansion = identify[1].upper(), clean(identify[2])
                    parts = [clean(part) or None for part in expansion.split("|")]
                    parts += [None] * (5 - len(parts))
                    found[code] = CatalogResolution(
                        code=code, description=parts[0], catalog_number=parts[1], mfr=parts[2],
                        finish=parts[3], notes=parts[4],
                        location=Location(**line_location(page, [candidate])), confidence=.94,
                    )
                elif candidate.text and not re.match(r"^\s*(?:CODE\s+)?[A-Z][A-Z0-9]{0,4}\s*(?:=|:|[-–—])", candidate.text, re.I):
                    break
    return found


def apply_code_lookups(components: list[Component], lookups: dict[str, CatalogResolution], page_number: int) -> int:
    resolved = 0
    for component in components:
        if not any(location.page == page_number for location in component.locations):
            continue
        candidates = [component.catalog_number, component.description]
        code = next((value.strip().upper() for value in candidates if value and SHORT_CODE.fullmatch(value.strip())), None)
        if not code or code not in lookups:
            continue
        component.catalog_resolution = lookups[code].model_copy(deep=True)
        component.warnings.append(f"Code {code} resolved from an explicit lookup on PDF page {page_number}.")
        resolved += 1
    return resolved
