"""Behavioral regression cases generated as small PDFs with real geometry."""
from pathlib import Path

import pymupdf
import pytest

from hardware_sets.extract import extract_pdf, identify_header


def write_pdf(path: Path, pages):
    with pymupdf.open() as doc:
        for rows in pages:
            page = doc.new_page(width=612, height=792)
            for y, cells in rows:
                for x, text in cells:
                    page.insert_text((x, y), text, fontsize=10)
        doc.save(path)
    return path


def table_header(y=120, swapped=False):
    return y, [(60, 'QTY'), (100, 'DESCRIPTION'), (280, 'CATALOG NUMBER'),
               (460, 'MFR' if swapped else 'FINISH'), (525, 'FINISH' if swapped else 'MFR')]


def test_context_overrides_ambiguous_codes_and_column_order(tmp_path):
    path = write_pdf(tmp_path/'context.pdf', [[
        (90, [(60, 'SET #1 - ENTRY')]), table_header(),
        (145, [(60, '1'), (100, 'Door Sweep'), (280, '315CN'), (460, '630'), (525, 'PE')]),
        (160, [(60, '1'), (100, 'Surface Closer'), (280, '7500'), (460, 'PE'), (525, 'NO')]),
        (250, [(60, 'SET #2')]), table_header(280, swapped=True),
        (305, [(60, '1'), (100, 'Surface Closer'), (280, '4040XP'), (460, 'LCN'), (525, 'PE')]),
    ]])
    result = extract_pdf(path)
    first, second = result.sets
    assert [(c.mfr, c.finish) for c in first.components] == [('PE','630'), ('NO','PE')]
    assert (second.components[0].mfr, second.components[0].finish) == ('LCN','PE')
    assert first.description == 'ENTRY'


def test_unused_missing_qty_and_multi_page_location(tmp_path):
    path = write_pdf(tmp_path/'continuation.pdf', [[
        (90, [(60, 'Hardware Group No. 3A')]), table_header(),
        (145, [(100, 'Hinge'), (280, '5BB1'), (460, '630'), (525, 'IVE')]),
    ], [
        table_header(60),
        (85, [(60, '1'), (100, 'Surface Closer'), (280, '4040XP'), (460, '689'), (525, 'LCN')]),
        (150, [(60, 'SET #4 - NOT USED')]),
    ]])
    result = extract_pdf(path)
    assert [s.set_number for s in result.sets] == ['3A','4']
    assert result.sets[0].components[0].qty is None
    assert len(result.sets[0].components) == 2
    assert [loc.page for loc in result.sets[0].locations] == [1,2]
    assert result.sets[1].status == 'not_used'
    assert result.sets[1].components == []
    for hardware_set in result.sets:
        for loc in hardware_set.locations:
            assert 0 <= loc.bbox[0] < loc.bbox[2] <= loc.page_width
            assert 0 <= loc.bbox[1] < loc.bbox[3] <= loc.page_height


def test_header_at_bottom_and_next_section_stop(tmp_path):
    path = write_pdf(tmp_path/'boundary.pdf', [[
        (640, [(60, 'Heading #17')]),
        (665, [(60, 'Item #1'), (150, 'Single door')]),
    ], [
        table_header(100),
        (130, [(60, '3'), (100, 'Hinge'), (280, '5BB1'), (460, '630'), (525, 'IVE')]),
    ], [
        (60, [(60, 'SECTION 08 80 00 - GLAZING')]),
        (100, [(60, 'PART 1 GENERAL')]),
        (150, [(60, '1'), (100, 'Glass Door'), (280, '123'), (460, '630'), (525, 'XX')]),
    ]])
    result = extract_pdf(path)
    assert len(result.sets) == 1
    assert len(result.sets[0].components) == 1
    assert [loc.page for loc in result.sets[0].locations] == [1,2]


def test_door_assignments_are_not_components(tmp_path):
    path = write_pdf(tmp_path/'doors.pdf', [[
        (90, [(60, 'Hardware Group No. 01')]),
        (110, [(60, 'For use on Door #(s):')]),
        (130, [(60, '101'), (100, '102'), (280, '103')]),
        table_header(155),
        (180, [(60, '3'), (100, 'Hinge'), (280, '5BB1'), (460, '630'), (525, 'IVE')]),
    ]])
    assert len(extract_pdf(path).sets[0].components) == 1


def test_qty_after_catalog_explicit_columns(tmp_path):
    path = write_pdf(tmp_path/'reordered.pdf', [[
        (90, [(60, 'SET #9')]),
        (120, [(60,'DESCRIPTION'),(230,'CATALOG NUMBER'),(380,'QTY'),(430,'MFR'),(520,'FINISH')]),
        (145, [(60,'Hinge'),(230,'5BB1'),(380,'3'),(430,'IVE'),(520,'630')]),
    ]])
    component = extract_pdf(path).sets[0].components[0]
    assert component.qty == 3
    assert component.description == 'Hinge'
    assert component.catalog_number == '5BB1'


def test_revision_strike_is_excluded_but_underline_is_retained(tmp_path):
    path = write_pdf(tmp_path/'revision.pdf', [[
        (90, [(60, 'SET #1')]), table_header(),
        (145, [(60, '1'), (100, 'Old Closer'), (280, 'OLD'), (460, '689'), (525, 'LCN')]),
        (170, [(60, '1'), (100, 'New Closer'), (280, '4040XP'), (460, '689'), (525, 'LCN')]),
    ]])
    with pymupdf.open(path) as doc:
        doc[0].draw_rect(pymupdf.Rect(59,141.5,550,142.1), color=None, fill=(0,0,0))
        doc[0].draw_rect(pymupdf.Rect(99,172,155,172.6), color=None, fill=(0,0,0))
        doc.saveIncr()
    result = extract_pdf(path)
    assert [c.description for c in result.sets[0].components] == ['New Closer']
    assert any('struck-through' in warning for warning in result.sets[0].warnings)


def test_unruled_product_prose_can_extend_through_empty_code_columns(tmp_path):
    path = write_pdf(tmp_path/'overflow.pdf', [[
        (90, [(60, 'SET #1')]),
        (120, [(60,'3'),(100,'Hinge'),(280,'5BB1'),(460,'630'),(525,'IVE')]),
        (140, [(60,'1'),(100,'Closer'),(280,'4040XP'),(460,'689'),(525,'LCN')]),
        (160, [(60,'1'),(100,'Lockset'),(280,'ND80'),(460,'626'),(525,'SCH')]),
        (180, [(60,'1'),(100,'Threshold'),(280,'Provided to suit the opening by the frame manufacturer')]),
    ]])
    row = extract_pdf(path).sets[0].components[-1]
    assert row.catalog_number == 'Provided to suit the opening by the frame manufacturer'
    assert row.mfr is None
    assert row.finish is None


@pytest.mark.parametrize('text,expected', [
    ('Hardware Group/Set #B1 and #B2 - Bedrooms','B1'),
    ('PART 63 - HARDWARE GROUP NO. C200C','C200C'),
    ('HW 04A Interior Single','04A'),
    ('Set: MISC','MISC'),
    ('Group 1 stainless-steel bolts, ASTM F 593',None),
    ('Set of 12-inch samples',None),
    ('Door# HwSet#',None),
])
def test_heading_conventions_and_prose(text, expected):
    found = identify_header(text)
    assert (found[0] if found else None) == expected
