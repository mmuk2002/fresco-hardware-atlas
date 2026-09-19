"""PDF evidence in unrotated, top-left page coordinates (points)."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata


def clean(text: str) -> str:
    # Link/electrification glyphs occupy separate cells in several schedules.
    text = ''.join(c for c in text if unicodedata.category(c) != 'Co')
    return re.sub(r'\s+', ' ', text.replace('\u00a0', ' ')).strip()


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2


@dataclass
class Line:
    words: list[Word]
    number: int = 0

    @property
    def text(self):
        return clean(' '.join(w.text for w in self.words))

    @property
    def bbox(self):
        return [min(w.x0 for w in self.words), min(w.y0 for w in self.words),
                max(w.x1 for w in self.words), max(w.y1 for w in self.words)]

    @property
    def cy(self):
        return sum(w.cy for w in self.words) / len(self.words)


@dataclass
class Page:
    number: int
    width: float
    height: float
    lines: list[Line]
    ocr: bool = False
    strikes: list[tuple[float, float, float]] = field(default_factory=list)


def read_page(pdf_page, number: int, ocr: bool = False) -> Page:
    native = pdf_page.get_text('words')
    rotated = [line['bbox'] for block in pdf_page.get_text('dict')['blocks'] if 'lines' in block
               for line in block['lines'] if abs(line['dir'][0] - 1) > .1]
    if rotated:
        native = [w for w in native if not any(b[0] <= (w[0]+w[2])/2 <= b[2] and b[1] <= (w[1]+w[3])/2 <= b[3] for b in rotated)]
    used_ocr = False
    if len(native) < 8 and ocr:
        textpage = pdf_page.get_textpage_ocr(language='eng', dpi=300, full=True)
        native = pdf_page.get_text('words', textpage=textpage)
        used_ocr = True
    words = []
    chars = None
    for w in native:
        value = clean(w[4])
        if not value:
            continue
        box = list(map(float, w[:4]))
        # A link/lightning symbol may be fused to a finish token with no space.
        # Dropping its character alone leaves its box in the catalog column.
        if any(unicodedata.category(c) == 'Co' for c in w[4]) and not used_ocr:
            if chars is None:
                chars = [ch for block in pdf_page.get_text('rawdict')['blocks'] if 'lines' in block
                         for line in block['lines'] for span in line['spans'] for ch in span['chars']]
            kept = [ch['bbox'] for ch in chars if clean(ch['c']) and
                    box[0] - .5 <= ch['bbox'][0] <= box[2] and abs(ch['bbox'][1] - box[1]) < 3]
            if kept:
                box = [min(b[0] for b in kept), min(b[1] for b in kept),
                       max(b[2] for b in kept), max(b[3] for b in kept)]
        words.append(Word(*box, value))
    words.sort(key=lambda w: (w.cy, w.x0))
    lines: list[Line] = []
    for word in words:
        match = next((ln for ln in reversed(lines[-4:]) if abs(ln.cy - word.cy) < 2.6), None)
        if match is None:
            lines.append(Line([word]))
        else:
            match.words.append(word)
    lines.sort(key=lambda ln: ln.cy)
    for index, line in enumerate(lines):
        line.words.sort(key=lambda w: w.x0)
        line.number = index + 1
    strikes = []
    for drawing in pdf_page.get_drawings():
        for item in drawing['items']:
            if item[0] == 'l':
                a, b = item[1:3]
                if abs(a.y - b.y) < .6 and abs(a.x - b.x) > 12:
                    strikes.append((min(a.x, b.x), max(a.x, b.x), a.y))
            elif item[0] == 're':
                rect = item[1]
                if rect.height <= 1.2 and rect.width > 4:
                    strikes.append((rect.x0, rect.x1, (rect.y0 + rect.y1) / 2))
    return Page(number, pdf_page.rect.width, pdf_page.rect.height, lines, used_ocr, strikes)


def line_location(page: Page, lines: list[Line]) -> dict:
    boxes = [ln.bbox for ln in lines]
    return {'page': page.number, 'bbox': [round(min(b[0] for b in boxes), 2),
            round(min(b[1] for b in boxes), 2), round(max(b[2] for b in boxes), 2),
            round(max(b[3] for b in boxes), 2)], 'page_width': page.width,
            'page_height': page.height, 'line_start': min(ln.number for ln in lines),
            'line_end': max(ln.number for ln in lines)}
