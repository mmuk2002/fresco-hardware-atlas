"""Geometry-first hardware schedules with contextual column assignment.

No document names, expected set counts or gold annotations are used by the parser.
All inferred fields remain linked to their original page regions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
from statistics import median
import time

import pymupdf

from .layout import Line, Page, Word, clean, line_location, read_page
from .models import Component, ExtractionResult, HardwareSet, Location
from .table_schedule import extract_table_page


HEADER = re.compile(
    r'^\s*(?:(?:PART\s+\d+\s*[-–:]\s*)|(?:[A-Z]\.|\d+\.\s+))?\s*'
    r'(?:(?:DOOR\s+)?HARDWARE\s+(?:SETS?|GROUPS?)(?:\s*/\s*(?:SETS?|GROUPS?))?|(?:HW|HDW)\.?\s*(?:SET)?|SET|GROUP|HEADING)'
    r'\s*(?:(?:NO\.?|NUMBER)\s*)?[#:]?\s*'
    r'(?P<id>(?:[A-Z]{1,3}\s+)?[A-Z0-9]+(?:[.\-/][A-Z0-9]+)*)'
    r'(?P<tail>.*)$', re.I)
UNUSED = re.compile(r'\b(?:NOT\s+USED|NOT\s+UTILIZED|UNUSED|NOT\s+IN\s+USE|DELETED|OMITTED|N\s*/\s*A)\b', re.I)
QTY = re.compile(r'^(?:\d+(?:\.\d+)?|\d+/\d+|\d+½|½|¼|¾|AR|A/R|AS\s+REQ(?:UIRED)?\.?|\*|__+|--+)$', re.I)
UNIT = re.compile(r'^(?:EA\.?|EACH|PR\.?|PAIR|PAIRS|SET|SETS|PC\.?|PCS\.?|PK|FT\.?|M)$', re.I)
MANUFACTURERS = set('IVE IVES SCH SCE LCN VON VD GLY GLJ GL IV BE BES BEST MK MCK MCKINNEY HA HAG HAGER SA SAR SARGENT RO ROC RKW ROCKWOOD PE PEM PEMKO NO NOR NORTON RIX RIXSON SDC SE SEC SECURITRON YA YAL YALE RU RUS COR C-R CR CORBIN RUSSWIN NGP ZER ZERO TR TRIMCO BB BBW HES DE DET DETEX ABH ADAMS ADAMS-RITE RCI DOR DORMA DKA DKC BRN BURNS PRE PRECISION EDW CMND CAM CAMDEN GJ KN KNC STANLEY ST SGT ASSA B/O BYO FAL FALCON DON KNIGHT HH AB SCHLAGE MC NATIONAL I/O'.split())
AMBIGUOUS = {'PE', 'NO', 'AL', 'US', 'A', 'NA', 'EN'}
FINISHES = set('BSP SP BLK BLACK BL BLU GREY GRAY GRY CLR CL AL ALM ALUM ALUMINUM US USP MIL MILL S B C A AA BK BN W WHITE US10B US26D US32D US28 US15 10B 26D 32D C26D C32D C28 CA EN D CH US3 US4 US10 US26 DB BRZ BZ 626E -626E 630-316 C32D-316 LS NONE'.split())
FINISH_RE = re.compile(r'^(?:US\d+[A-Z]*|[36]\d{2}(?:[A-Z]|[-/]\d+)?|\d{2}D|C\d{2}D?|\d{3}/\d{3})$', re.I)
COMPONENT_WORDS = re.compile(r'\b(?:hinge|pivot|closer|lock|lockset|latch|latchset|strike|bolt|core|cylinder|handle|pull|plate|stop|gasket|gasketing|seal|seals|silencer|sweep|threshold|astragal|coordinator|operator|actuator|transfer|hardware|device|harness|power|reader|switch|holder|weatherstrip|weatherstripping|viewer|bumper|catch|bracket|mullion|key|keying|button|control|intercom|relay|sequencer|diagrams|schematic|accessory|signage|magnet|flush|exit|panic|guard|rain|door|access|indicator|mounting|electro|push|sensor|wire|padlock)\b', re.I)
NOTE = re.compile(r'^(?:notes?\b|operational?\b|operation\b|sequence\b|doors?\s+(?:are|is|normally|to|opens?|will)|upon\b|free\s+egress|always\b|entry\b|refer\b|provide\s+(?:each|factory)|coordinate\b|valid\b|access\s+control\s+reader\s+by|\*|for\s+use\s+on|each\s+to\s+have|item\s*#|\d+\s*(?:single\s+door|pair\s+of\s+doors)|hardware\s+(?:provided|is\s+furnished)|all\s+low\s+voltage)', re.I)


def identify_header(text: str):
    match = HEADER.match(text)
    if not match:
        return None
    number, tail = match['id'].strip(), match['tail'].strip()
    if number.split()[0].lower() in {'of', 'on', 'in', 'at', 'to'}:
        return None
    if number.upper() in {'S', 'SCHEDULE', 'SCHEDULES', 'SETS', 'GROUPS', 'FOR', 'THE', 'SHALL', 'AND', 'WITH', 'TO', 'AS', 'NO', 'NUMBER', 'UP', 'OUT', 'ITEMS', 'TYPES', 'INDEX', 'LIST'}:
        return None
    if not any(c.isdigit() for c in number) and number.upper() not in {'MISC', 'A', 'B', 'C', 'D', 'E', 'F', 'G'}:
        return None
    # Prose references are not boundaries. Descriptions use punctuation or capitals.
    if tail and not (re.match(r'^(?:[-–—:=([⚡]|NOT\b|N/A\b|UNUSED\b|Moved\b|and\s+#|\(?CONTINUED\b)', tail, re.I)
                     or re.match(r'^and\s+#?\d', tail, re.I) or re.match(r'^[A-Z][A-Z /,-]{3}', tail) or re.match(r'^HW\s', text, re.I)):
        return None
    if len(tail) > 150:
        return None
    description = re.sub(r'^\s*[-–—:=]\s*', '', tail).strip() or None
    return number, description


def is_finish(text: str):
    return text.upper() not in AMBIGUOUS and (text.upper() in FINISHES or FINISH_RE.fullmatch(text) is not None)


def is_manufacturer(text: str, legend: set[str]):
    return text.upper() not in AMBIGUOUS and text.upper() in MANUFACTURERS | legend


def parse_qty(text: str | None):
    if not text or text.upper() in {'AR', 'A/R', '*'} or re.match(r'AS\s+REQ', text, re.I):
        return None
    if '/' in text or any(c in text for c in '½¼¾'):
        return text  # Preserve printed fractional quantities without unit conversion.
    try:
        n = float(text)
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


@dataclass
class Schema:
    starts: dict[str, float]
    explicit: bool = False
    score: float = .82
    reason: str = 'column_consensus'
    centered_rows: bool = False

    def cells(self, line: Line) -> dict[str, str]:
        fields = sorted(self.starts, key=self.starts.get)
        positioned = []
        for w in line.words:
            role = fields[0]
            for field in fields:
                if w.x0 >= self.starts[field] - 3.5:
                    role = field
            positioned.append([w, role])
        if not self.explicit and 'catalog_number' in self.starts:
            # In unruled schedules a prose product cell may extend through empty
            # finish/manufacturer cells. Geometry alone must not turn ordinary
            # words such as "per sill" or "by" into finish/manufacturer codes.
            for role in ('finish', 'mfr'):
                members = [entry for entry in positioned if entry[1] == role]
                value = clean(' '.join(entry[0].text for entry in members))
                if not value:
                    continue
                if role == 'finish' and len(members) == 2 and is_finish(members[0][0].text) and is_manufacturer(members[1][0].text, set()):
                    if 'mfr' in self.starts:
                        members[1][1] = 'mfr'
                        continue
                code = bool(re.fullmatch(r'[A-Z0-9][A-Z0-9/._-]{0,14}', value))
                named = value.upper() in MANUFACTURERS if role == 'mfr' else value.upper() in FINISHES
                if not code and not named:
                    for entry in members:
                        entry[1] = 'catalog_number'
        cells = defaultdict(list)
        for word, role in positioned:
            cells[role].append(word.text)
        return {k: clean(' '.join(v)) for k, v in cells.items()}


def clusters(values: list[float], tolerance: float = 7):
    groups: list[list[float]] = []
    for value in sorted(values):
        if groups and value - median(groups[-1]) <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return sorted(groups, key=len, reverse=True)


def infer_schema(lines: list[Line], width: float, legend: set[str], previous: Schema | None = None):
    for ln in lines:
        text = ln.text.upper()
        if ('DESCRIPTION' in text or 'ITEM' in text) and any(w in text for w in ('CATALOG', 'MFR', 'MANUFACTURER', 'FINISH', 'PRODUCT')):
            starts = {}
            for word in ln.words:
                token = word.text.upper().strip('.:#')
                field = {'QTY': 'qty', 'QT': 'qty', 'QUANTITY': 'qty', 'DESCRIPTION': 'description', 'ITEM': 'description',
                         'CATALOG': 'catalog_number', 'PRODUCT': 'catalog_number', 'MODEL': 'catalog_number',
                         'FINISH': 'finish', 'FIN': 'finish', 'MFR': 'mfr', 'MFG': 'mfr', 'MANUFACTURER': 'mfr',
                         'MANUF': 'mfr', 'MANF': 'mfr', 'NOTES': 'notes'}.get(token)
                if field:
                    starts[field] = word.x0
            if 'description' in starts and len(starts) >= 3:
                # Units and link icons are discarded separately, not catalog columns.
                if 'qty' not in starts:
                    starts['qty'] = min(ln.bbox[0], starts['description'] - 30)
                return Schema(starts, True, .97, 'explicit_headers')
    rows = []
    for ln in lines:
        ws = ln.words
        if len(ws) >= 2 and QTY.fullmatch(ws[0].text) and ws[0].x0 < width * .32 and not NOTE.match(ln.text):
            if COMPONENT_WORDS.search(ln.text):
                rows.append(ln)
    if not rows:
        return previous
    mfr_positions, finish_positions, catalog_positions, descriptions, quantities = [], [], [], [], []
    for ln in rows:
        ws = ln.words
        quantities.append(ws[0].x0)
        start = 1
        if len(ws) > 2 and UNIT.fullmatch(ws[1].text):
            start = 2
        descriptions.append(ws[start].x0)
        for j, w in enumerate(ws[start + 1:], start + 1):
            gap = w.x0 - ws[j - 1].x1
            if w.x0 > width * .62 and is_manufacturer(w.text, legend):
                mfr_positions.append(w.x0)
            if (w.x0 > width * .68 or (j == len(ws)-1 and w.x0 > ws[start].x0 + 70 and gap > 9)) and is_finish(w.text):
                finish_positions.append(w.x0)
            if gap >= 10 and width * .26 < w.x0 < width * .80:
                catalog_positions.append(w.x0)
    starts = {'qty': median(quantities), 'description': median(descriptions)}
    # Explicit local headers from prior sets are useful when the next page has few rows.
    if previous and previous.explicit and abs(previous.starts.get('description', 0) - starts['description']) < 12:
        return previous
    for field, positions in [('mfr', mfr_positions), ('finish', finish_positions)]:
        groups = clusters(positions)
        if groups and (len(groups[0]) >= 2 or len(rows) <= 2):
            starts[field] = median(groups[0])
    if 'mfr' not in starts and 'finish' in starts:
        short_codes = [ln.words[-1].x0 for ln in rows if
                       ln.words[-1].x0 > starts['finish'] + 15 and
                       re.fullmatch(r'[A-Za-z][A-Za-z0-9/\-]{0,6}', ln.words[-1].text) and
                       not is_finish(ln.words[-1].text)]
        groups = clusters(short_codes)
        if groups and len(groups[0]) >= 3:
            starts['mfr'] = median(groups[0])
    groups = clusters(catalog_positions, 9)
    groups = [g for g in groups if median(g) > starts['description'] + 35 and
              all(abs(median(g) - pos) > 15 for name, pos in starts.items() if name in {'mfr', 'finish'})]
    if groups:
        starts['catalog_number'] = median(groups[0])
    if previous and abs(starts['description'] - previous.starts.get('description', 0)) < 6:
        same_catalog = abs(starts.get('catalog_number', -100) - previous.starts.get('catalog_number', -200)) < 9
        if same_catalog:
            for role in ('mfr', 'finish'):
                if role not in starts and role in previous.starts:
                    starts[role] = previous.starts[role]
    if 'catalog_number' not in starts and previous and abs(starts['description'] - previous.starts.get('description', 0)) < 12:
        return previous
    # Full manufacturer names and centered quantities occur in the four-column family.
    centered = bool('mfr' in starts and 'finish' not in starts and any(
        len(w.text) > 4 and is_manufacturer(w.text, legend) and w.x0 > width * .60 for ln in rows for w in ln.words))
    return Schema(starts, False, .87 if len(rows) >= 3 else .68, 'column_consensus', centered)


def is_column_header(line: Line):
    text = line.text.upper()
    return (len(text.split()) < 14 and 'DESCRIPTION' in text and
            bool(re.search(r'\b(?:QTY|QT|QUANTITY|FINISH|MFR|MANF|MANUFACTURER)\b', text))) or text in {'Y', 'QT', 'QTY'}


def is_furniture(line: Line, page: Page):
    y = line.bbox[1]
    if y < 30 or line.bbox[3] > page.height - 29:
        return True
    text = line.text
    if y > page.height * .89 and (re.search(r'\b(?:HARDWARE|Page\s+\d|Copyright|\d{4}|08\s*71)\b', text, re.I) or len(text) < 80):
        return True
    return y < page.height * .10 and not (identify_header(text) or is_column_header(line) or
                                          re.match(r'^\d+\s+(?:EA|PR)\b', text, re.I)) and not COMPONENT_WORDS.search(text)


def struck(line: Line, page: Page):
    # A strike traverses word mid-height; table rules are at cell boundaries.
    hits = sum(any(a <= w.x0 + 2 and b >= w.x1 - 2 and abs(y - (w.y0 + (w.y1-w.y0)*.56)) < 2
                   for a, b, y in page.strikes) for w in line.words)
    return hits >= max(2, len(line.words) * .35)


def component_candidate(line: Line, schema: Schema):
    text = line.text
    if re.match(r'^\*\s*(?:Provide|Coordinate|Upon|Always|Built|Access\s+Control|Door\s+normally)\b', text, re.I):
        return False
    if is_column_header(line) or (NOTE.match(text) and not QTY.fullmatch(line.words[0].text)) or re.match(r'^(?:Doors?\s*:|Description\s*:|END OF|SECTION\s+\d|PART\s+[123])', text, re.I):
        return False
    if re.match(r'^\d+\s+(?:Pair\s+Doors|Single\s+Door)', text, re.I):
        return False
    cells = schema.cells(line)
    q = cells.get('qty', '').split()
    has_qty = bool(q and QTY.fullmatch(q[0]))
    desc = cells.get('description', '')
    # Genuine blank quantities still produce rows when description/catalog align.
    if has_qty:
        return bool(re.search('[A-Za-z]', desc) or cells.get('catalog_number') or (schema.centered_rows and cells.get('mfr')))
    if re.search(r'\b(?:shall|normally|please|not shown|to be|both doors|door opens|required to|allows|activate|upon|optional|to unlock|to sequence)\b', text, re.I):
        return False
    desc_words = [w for w in line.words if schema.starts['description'] - 4 <= w.x0 < schema.starts.get('catalog_number', 999) - 4]
    aligned = bool(desc_words and abs(desc_words[0].x0 - schema.starts['description']) < 5)
    return aligned and bool(COMPONENT_WORDS.search(desc)) and bool(cells.get('catalog_number') or cells.get('mfr'))


def join_cell(old: str | None, new: str | None):
    if not new:
        return old
    if not old:
        return new
    return old + ('' if old.endswith('-') and not old.endswith(' -') else ' ') + new


def parse_region(page: Page, lines: list[Line], schema: Schema | None, set_id: str):
    for index, line in enumerate(lines):
        if re.match(r'^END\s+OF\s+SECTION\b', line.text, re.I):
            lines = lines[:index]
            break
    if not schema:
        return [], [ln.text for ln in lines if ln.text], ['No stable column layout detected.']
    header_indexes = [i for i, ln in enumerate(lines) if is_column_header(ln)]
    # Door assignment lists appear above the column header, sometimes all numeric.
    prefix = lines[:header_indexes[0]] if header_indexes else []
    body_lines = lines[header_indexes[0]+1:] if header_indexes else lines
    useful = [ln for ln in body_lines if not is_furniture(ln, page) and not is_column_header(ln)]
    centered = schema.centered_rows or any(
        not schema.cells(a).get('description') and schema.cells(a).get('catalog_number') and
        schema.cells(b).get('description') and schema.cells(b).get('mfr') and 0 < b.cy-a.cy < 10
        for a, b in zip(useful, useful[1:]))
    components, notes, warnings = [], [], []
    notes.extend(ln.text for ln in prefix if not is_furniture(ln, page))
    anchors = []
    in_notes = False
    for i, ln in enumerate(useful):
        cells = schema.cells(ln)
        qparts = cells.get('qty', '').split()
        quantity_anchor = bool(qparts and QTY.fullmatch(qparts[0]))
        unit_anchor = any(UNIT.fullmatch(t) for t in qparts)
        if NOTE.match(ln.text) and ln.bbox[0] < schema.starts.get('catalog_number', 999):
            in_notes = True
        if not component_candidate(ln, schema):
            continue
        if in_notes and not quantity_anchor and not unit_anchor:
            continue
        if anchors and not quantity_anchor and not unit_anchor:
            previous = useful[anchors[-1]]
            previous_cells = schema.cells(previous)
            delta = ln.cy - previous.cy
            previous_desc = previous_cells.get('description', '')
            # A second line of a wrapped row has no quantity/unit. In aligned
            # tables new blank-quantity rows have a row gap or an EA unit.
            if delta < 1.35 * (ln.bbox[3] - ln.bbox[1]) and (
                previous_desc.endswith((' -', ' IN', ' TO', ' WITH')) or
                cells.get('mfr') is None and cells.get('finish') is None and
                not re.match(r'^(?:SEALS?|DIAGRAMS?|ALL HARDWARE)\b', cells.get('description', ''), re.I)):
                continue
        anchors.append(i)
        in_notes = False
    # Center-aligned multiline cells can start before their quantity baseline.
    anchored = set(anchors)
    row_lines: dict[int, list[Line]] = {i: [useful[i]] for i in anchors}
    row_notes: dict[int, list[str]] = defaultdict(list)
    note_mode = False
    note_target = None
    for index, ln in enumerate(useful):
        if index in anchored:
            note_mode = False
            note_target = None
            continue
        text = ln.text
        if not text:
            continue
        if (NOTE.match(text) and ln.bbox[0] < schema.starts.get('catalog_number', 999)) or text.startswith(('Doors:', 'Description:', 'Properties:')):
            previous_anchor = next((a for a in reversed(anchors) if a < index), None)
            next_anchor = next((a for a in anchors if a > index), None)
            if re.match(r'^(?:Note\s*:|Properties\s*:)', text, re.I) and previous_anchor is not None and next_anchor is not None:
                note_target = previous_anchor
                row_notes[note_target].append(text)
            else:
                notes.append(text)
                note_target = None
            note_mode = True
            continue
        if note_mode and note_target is not None:
            row_notes[note_target].append(text)
            continue
        before = next((a for a in reversed(anchors) if a < index), None)
        after = next((a for a in anchors if a > index), None)
        target = before
        if centered and after is not None and (before is None or abs(useful[after].cy-ln.cy) < abs(ln.cy-useful[before].cy)):
            target = after
        cells = schema.cells(ln)
        in_columns = ln.bbox[0] >= schema.starts['description'] - 4
        delta = abs(ln.cy - useful[target].cy) if target is not None else 999
        nearby = index > 0 and ln.cy - useful[index-1].cy < 25
        if target is not None and in_columns and (delta < 52 or nearby) and (not note_mode or centered and target == after) and len(text) < 180:
            row_lines[target].append(ln)
        else:
            notes.append(text)
    for anchor, group in row_lines.items():
        group.sort(key=lambda ln: ln.cy)
        if struck(useful[anchor], page):
            warnings.append(f'Excluded struck-through component on page {page.number}, line {useful[anchor].number}: {useful[anchor].text}')
            continue
        fields = {k: None for k in ('description', 'catalog_number', 'mfr', 'finish', 'notes')}
        raw_qty = None
        unit = None
        for ln in group:
            cells = schema.cells(ln)
            qparts = cells.get('qty', '').split()
            if qparts and QTY.fullmatch(qparts[0]):
                raw_qty = qparts[0]
                qparts = qparts[1:]
            if qparts and UNIT.fullmatch(qparts[0]):
                unit = qparts[0]
                qparts = qparts[1:]
            # Units can lie in the description band in some layouts.
            desc = cells.get('description', '')
            desc_parts = desc.split()
            if desc_parts and UNIT.fullmatch(desc_parts[0]) and len(desc_parts) > 1:
                unit = desc_parts.pop(0)
                cells['description'] = ' '.join(desc_parts)
            for k in fields:
                fields[k] = join_cell(fields[k], cells.get(k))
        promoted = False
        if not fields['description']:
            if not fields['catalog_number']:
                continue
            fields['description'], fields['catalog_number'] = fields['catalog_number'], None
            promoted = True
        if row_notes[anchor]:
            fields['notes'] = join_cell(fields['notes'], '\n'.join(row_notes[anchor]))
        component_warnings = []
        if promoted:
            component_warnings.append('Description cell is empty; retained the printed free-text item from the product column as description.')
        if raw_qty is None or parse_qty(raw_qty) is None:
            component_warnings.append('Quantity is absent or unspecified; retained as null.')
        if 'catalog_number' not in schema.starts and 'finish' not in schema.starts:
            component_warnings.append('List layout: catalog, manufacturer and finish not independently identified.')
        confidence = {k: (schema.score if fields[k] else .6) for k in fields}
        confidence['qty'] = .98 if raw_qty and parse_qty(raw_qty) is not None else .75
        raw_text = '\n'.join(ln.text for ln in group)
        comp_id = hashlib.sha256(f'{set_id}:{page.number}:{useful[anchor].number}'.encode()).hexdigest()[:16]
        component = Component(id=comp_id, qty=parse_qty(raw_qty), **fields, raw_text=raw_text,
            confidence=confidence, locations=[Location(**line_location(page, group))], warnings=component_warnings,
            qty_raw=raw_qty, unit=unit, mapping_reason=schema.reason, ocr=page.ocr)
        components.append(component)
    return components, notes, warnings


def merge_location(target: HardwareSet, location: Location):
    existing = next((loc for loc in target.locations if loc.page == location.page), None)
    if existing is None:
        target.locations.append(location)
    else:
        existing.bbox = [min(existing.bbox[0], location.bbox[0]), min(existing.bbox[1], location.bbox[1]),
                         max(existing.bbox[2], location.bbox[2]), max(existing.bbox[3], location.bbox[3])]
        existing.line_start = min(existing.line_start or 1, location.line_start or 1)
        existing.line_end = max(existing.line_end or 1, location.line_end or 1)


def extract_pdf(path: str | Path, pages: list[int] | None = None, ocr: bool = False) -> ExtractionResult:
    start = time.perf_counter()
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sets: list[HardwareSet] = []
    warnings: list[str] = []
    legend: set[str] = set()
    active: HardwareSet | None = None
    schema: Schema | None = None
    text_poor, inspected, candidate_pages = [], [], []
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError('The PDF is password protected.')
        selected = set(pages) if pages is not None else set(range(1, len(doc) + 1))
        if not selected or min(selected) < 1 or max(selected) > len(doc):
            raise ValueError('Page selection is outside the PDF range (pages are one-based).')
        # Page routing uses all text, keeping continuation state until a section boundary.
        for page_number in sorted(selected):
            pdf_page = doc[page_number - 1]
            text = pdf_page.get_text('text', sort=True)
            inspected.append(page_number)
            if len(text.strip()) < 60:
                text_poor.append(page_number)
            # Gather manufacturer legend entries; ambiguous entries only help via columns.
            for ln in text.splitlines():
                bits = ln.strip().split()
                if 2 <= len(bits) <= 7 and len(bits[0]) <= 5 and any(w.upper().strip(',.') in MANUFACTURERS for w in bits[1:]):
                    legend.add(bits[0].upper())
            possible = any(identify_header(ln.strip()) for ln in text.splitlines())
            if 'HARDWARE TYPE' in text.upper() and 'MANUFACTURER' in text.upper():
                table_sets = extract_table_page(pdf_page, page_number, digest)
                if table_sets:
                    sets.extend(table_sets)
                    candidate_pages.append(page_number)
                    active = None
                    continue
            continuation = active is not None and active.locations and page_number == active.locations[-1].page + 1
            if continuation:
                section_codes = re.findall(r'\b08\s?\d{2}\s?\d{2}\b', text[:650])
                new_section = any(re.sub(r'\s', '', code) not in {'087100', '087000', '087110'} for code in section_codes)
                general_start = re.search(r'(?im)^\s*(?:PART\s+1\s*[-–:]?\s*GENERAL|1(?:\.0)?\s+GENERAL|1\.1\s+SUMMARY)\b', text[:1800])
                if new_section or general_start:
                    continuation = False
                    active = None
            if not possible and not continuation and not (ocr and len(text.strip()) < 60):
                active = None
                continue
            try:
                page = read_page(pdf_page, page_number, ocr)
            except RuntimeError as exc:
                if ocr and len(text.strip()) < 60:
                    warnings.append(f'OCR unavailable on page {page_number}: {exc}')
                    continue
                raise
            headers = [(i, identify_header(ln.text)) for i, ln in enumerate(page.lines) if identify_header(ln.text)]
            if not headers and not continuation:
                continue
            # Suppress references inside indexes or specification prose by requiring body evidence.
            filtered_headers = []
            for index, header in headers:
                next_lines = page.lines[index+1:index+18]
                tail = ' '.join(ln.text for ln in next_lines)
                near_bottom = page.lines[index].cy > page.height * .72
                strong = re.match(r'^(?:(?:PART\s+\d+\s*-\s*)?(?:HARDWARE\s+(?:GROUP|SET)|HEADING\s*#)|SET\s*[:#]|HW\s+\w)', page.lines[index].text, re.I)
                if strong or UNUSED.search((header[1] or '') + ' ' + tail[:70]) or (near_bottom and header[1] is None) or any(
                    re.match(r'^(?:\d+(?:\.\d+)?|AR|\*)\s+', ln.text) and COMPONENT_WORDS.search(ln.text)
                    for ln in next_lines) or any(is_column_header(ln) for ln in next_lines):
                    filtered_headers.append((index, header))
            headers = filtered_headers
            if not headers and not continuation:
                continue
            candidate_pages.append(page_number)
            page_schema = infer_schema([ln for ln in page.lines if not is_furniture(ln, page)], page.width, legend, schema)
            boundaries = [(i, h) for i, h in headers] + [(len(page.lines), None)]
            begin = 0
            if active and continuation:
                initial_end = headers[0][0] if headers else len(page.lines)
                region = page.lines[:initial_end]
                comps, notes, issues = parse_region(page, region, page_schema, active.id)
                if comps:
                    active.components.extend(comps)
                    active.notes.extend(notes)
                    active.warnings.extend(issues)
                    src_lines = [ln for ln in region if not is_furniture(ln, page)]
                    if src_lines:
                        merge_location(active, Location(**line_location(page, src_lines)))
                    active.warnings.append('Set continues across PDF pages.')
                elif not headers:
                    active = None
            for position in range(len(headers)):
                idx, (number, description) = headers[position]
                end = boundaries[position + 1][0]
                label_words = page.lines[idx].words[:2] if re.match(r'^HW\s', page.lines[idx].text, re.I) else page.lines[idx].words[:4]
                if struck(Line(label_words), page):
                    warnings.append(f'Excluded struck-through set header {number} on page {page_number}.')
                    active = None
                    continue
                region = page.lines[idx + 1:end]
                # A new specification section is a hard boundary, even on the same page.
                for n, ln in enumerate(region):
                    if re.match(r'^(?:END\s+OF\s+SECTION|SECTION\s+\d{2}\s?\d{2}|PART\s+1\s)', ln.text, re.I):
                        region = region[:n]
                        break
                is_continued = bool(description and re.search('continu', description, re.I))
                if is_continued and active and active.set_number == number:
                    current = active
                else:
                    sid = hashlib.sha256(f'{digest}:{page_number}:{idx}:{number}'.encode()).hexdigest()[:16]
                    current = HardwareSet(id=sid, set_number=number, description=description, confidence=.88)
                    sets.append(current)
                body = ' '.join(ln.text for ln in region[:4])
                if UNUSED.search(description or '') or re.match(r'^\s*(?:NOT USED|N/A|UNUSED|OMITTED)\b', body, re.I):
                    current.status = 'not_used'
                desc_line = next((ln.text for ln in region[:5] if re.match(r'^Description\s*:', ln.text, re.I)), None)
                if desc_line:
                    current.description = re.sub(r'^Description\s*:\s*', '', desc_line, flags=re.I)
                current_schema = infer_schema(region, page.width, legend, page_schema or schema)
                comps, notes, issues = parse_region(page, region, current_schema, current.id)
                if current.status != 'not_used':
                    current.components.extend(comps)
                current.notes.extend(notes)
                current.warnings.extend(issues)
                source_lines = [page.lines[idx]] + [ln for ln in region if not is_furniture(ln, page)]
                merge_location(current, Location(**line_location(page, source_lines)))
                if not comps and current.status != 'not_used':
                    current.warnings.append('No components detected in this page region; inspect source or continuation.')
                current.confidence = current_schema.score if current_schema else .45
                schema = current_schema or schema
                active = current
            if headers and page_schema:
                schema = page_schema
        page_count = len(doc)
    for hardware_set in sets:
        hardware_set.notes = list(dict.fromkeys(re.sub(r'^Notes?\s*:\s*', '', note, flags=re.I)
            for note in hardware_set.notes if not re.match(r'^Description\s*:', note, re.I)))
        hardware_set.warnings = list(dict.fromkeys(hardware_set.warnings))
        if hardware_set.components:
            hardware_set.warnings = [w for w in hardware_set.warnings if not w.startswith('No components detected')]
    aliases = []
    for hardware_set in sets:
        if hardware_set.description and re.match(r'^and\s+#?[A-Z0-9]', hardware_set.description, re.I):
            shared = re.match(r'^and\s+#?([A-Z0-9.\-]+)\s*[-–—:]?\s*(.*)', hardware_set.description, re.I)
            if shared:
                hardware_set.description = shared[2] or None
                other = hardware_set.model_copy(deep=True)
                other.set_number = shared[1]
                other.id = hashlib.sha256((hardware_set.id + ':' + shared[1]).encode()).hexdigest()[:16]
                other.notes.append(f'Shares the printed schedule with set {hardware_set.set_number}.')
                for component in other.components:
                    component.id = hashlib.sha256((other.id + ':' + component.id).encode()).hexdigest()[:16]
                aliases.append(other)
    sets.extend(aliases)
    if text_poor:
        warnings.append(f'{len(text_poor)} text-poor pages detected; ' + ('OCR requested.' if ocr else 'OCR was not requested. See stats.text_poor_pages; these pages are not verified empty.'))
    if not sets:
        warnings.append('No hardware set definitions detected. This may be a supporting section, door index, unsupported layout, or scanned content; review the source.')
    return ExtractionResult(id=digest[:32], name=path.name, project=path.parent.name, page_count=page_count,
        sets=sets, warnings=warnings, stats={'engine': 'geometry-context-v1', 'elapsed_seconds': round(time.perf_counter()-start, 3),
        'pages_inspected': len(inspected), 'selected_pages': sorted(selected) if pages else None,
        'schedule_pages': candidate_pages, 'text_poor_pages': text_poor, 'set_count': len(sets),
        'component_count': sum(len(s.components) for s in sets), 'unused_set_count': sum(s.status == 'not_used' for s in sets),
        'multi_page_set_count': sum(len(s.locations) > 1 for s in sets), 'source_sha256': digest,
        'confidence_kind': 'heuristic; not calibrated probabilities'})
