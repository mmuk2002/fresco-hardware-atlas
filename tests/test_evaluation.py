"""Regression tests for honest scoring, scope, and one-to-one matching."""

from __future__ import annotations

import copy
import json

import pytest

from hardware_sets.cli import main, output_name, parse_pages
from hardware_sets.evaluation import evaluate, load_gold, match_components, normalize
from hardware_sets.models import ExtractionResult


def component(**updates):
    row = {"qty": 1, "description": "Surface closer", "catalog_number": "4040XP EDA",
           "mfr": "LCN", "finish": "US26D", "notes": None}
    row.update(updates)
    return row


def gold_set(components=None, **updates):
    item = {"source_path": "Project/spec.pdf", "page": 2, "set_number": "1",
            "components": [component()] if components is None else components}
    item.update(updates)
    return item


def prediction(components=None, **updates):
    item = {"set_number": "1", "locations": [{"page": 2}],
            "components": [component()] if components is None else components}
    item.update(updates)
    return [{"source_path": "C:/downloads/Project/spec.pdf", "sets": [item]}]


def test_perfect_prediction_normalizes_numeric_qty_case_and_whitespace():
    predicted = component(qty="1.0", description=" SURFACE   closer ", mfr="lcn")
    report = evaluate([gold_set()], prediction([predicted]))
    assert report["set_detection"]["recall"] == 1
    assert report["set_detection"]["precision"] is None
    assert report["whole_row"]["accuracy"] == 1
    assert all(field["accuracy"] == 1 for field in report["fields"].values())


def test_one_predicted_row_cannot_satisfy_two_gold_components():
    report = evaluate([gold_set([component(), component()])], prediction())
    assert report["components"]["matched"] == 1
    assert report["components"]["recall"] == 0.5
    assert report["whole_row"]["accuracy"] == 0.5
    assert report["fields"]["notes"] == {"correct": 1, "total": 2, "accuracy": 0.5}


def test_extra_duplicate_prediction_reduces_precision():
    report = evaluate([gold_set()], prediction([component(), component()]))
    assert report["components"]["recall"] == 1
    assert report["components"]["precision"] == 0.5
    assert len(report["details"][0]["extra_predicted_rows"]) == 1


def test_no_match_gets_zero_including_null_fields():
    report = evaluate([gold_set()], [])
    assert report["set_detection"]["matched"] == 0
    assert report["whole_row"]["accuracy"] == 0
    assert all(field["accuracy"] == 0 for field in report["fields"].values())
    assert report["components"]["precision"] is None


def test_unrelated_row_is_unmatched_despite_same_finish_qty_manufacturer():
    wrong = component(description="Weatherstrip", catalog_number="XYZ789")
    report = evaluate([gold_set()], prediction([wrong]))
    assert report["components"]["matched"] == 0
    assert report["fields"]["mfr"]["correct"] == 0


def test_mfr_finish_swap_is_reported_separately():
    report = evaluate([gold_set()], prediction([component(mfr="US26D", finish="LCN")]))
    assert report["mfr_finish_swaps"] == 1
    assert report["fields"]["mfr"]["accuracy"] == 0
    assert report["fields"]["finish"]["accuracy"] == 0
    assert report["fields"]["description"]["accuracy"] == 1


def test_page_scope_excludes_unannotated_sets_and_continuation_rows():
    predicted = prediction([component(locations=[{"page": 2}]),
                            component(description="Wall stop", locations=[{"page": 3}])])
    predicted[0]["sets"][0]["locations"].append({"page": 3})
    predicted[0]["sets"].append({"set_number": "99", "locations": [{"page": 2}], "components": [component()]})
    report = evaluate([gold_set()], predicted)
    assert report["components"]["predicted_in_annotated_sets"] == 1
    assert report["components"]["precision"] == 1
    assert report["set_detection"]["gold"] == 1


def test_set_on_wrong_page_does_not_match():
    report = evaluate([gold_set()], prediction(locations=[{"page": 1}]))
    assert report["set_detection"]["matched"] == 0


def test_not_used_set_with_no_components_still_scores_detection():
    expected = gold_set([], set_number="5", status="not_used")
    report = evaluate([expected], prediction([], set_number="5", status="not_used"))
    assert report["set_detection"]["matched"] == 1
    assert report["set_fields"]["status"]["accuracy"] == 1
    assert report["whole_row"]["accuracy"] is None


def test_matching_is_one_to_one_and_uses_catalog_to_resolve_same_descriptions():
    expected = [component(catalog_number="A100"), component(catalog_number="B200")]
    predicted = list(reversed(copy.deepcopy(expected)))
    assert match_components(expected, predicted) == {1: 0, 0: 1}


def test_same_predicted_set_cannot_satisfy_duplicate_gold_annotations():
    report = evaluate([gold_set(), gold_set()], prediction())
    assert report["set_detection"]["matched"] == 1


def test_duplicate_gold_file_rejected(tmp_path):
    path = tmp_path / "gold.json"
    path.write_text(json.dumps([gold_set(), gold_set()]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate gold"):
        load_gold(path)


def test_ambiguous_source_files_rejected():
    values = prediction() + prediction()
    with pytest.raises(ValueError, match="Multiple result documents"):
        evaluate([gold_set()], values)


def test_pages_and_stable_output_names():
    assert parse_pages("1-3, 5,2") == [1, 2, 3, 5]
    with pytest.raises(Exception):
        parse_pages("3-1")
    with pytest.raises(Exception):
        parse_pages("0")
    assert output_name("A/spec.pdf") != output_name("B/spec.pdf")
    assert output_name("A/spec.pdf") == output_name("A\\spec.pdf")
    assert normalize("RC 4\u201d x 4\u201d") == normalize('RC 4" x 4"')


def test_extract_stdout_is_machine_readable_despite_library_messages(tmp_path, monkeypatch, capsys):
    source = tmp_path / "spec.pdf"
    source.write_bytes(b"fixture")

    def fake_extract(path, **kwargs):
        print("Library diagnostic")
        assert kwargs["pages"] == [1, 3]
        return ExtractionResult(name="spec.pdf", page_count=3)

    monkeypatch.setattr("hardware_sets.extract.extract_pdf", fake_extract)
    assert main(["extract", str(source), "--pages", "1,3"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["page_count"] == 3
    assert "Library diagnostic" in output.err


def test_corpus_saves_every_success_and_error_without_basename_collision(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source"
    destination = tmp_path / "output"
    for project in ("A", "B", "C"):
        folder = source / project
        folder.mkdir(parents=True)
        (folder / "spec.pdf").write_bytes(b"fixture")

    def fake_extract(path, **kwargs):
        if path.parent.name == "B":
            raise ValueError("Broken PDF")
        return ExtractionResult(name="spec.pdf", page_count=3)

    monkeypatch.setattr("hardware_sets.extract.extract_pdf", fake_extract)
    assert main(["corpus", str(source), "--output", str(destination)]) == 1
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    assert summary["success_count"] == 2
    assert summary["error_count"] == 1
    assert summary["completed_count"] == 3
    assert len({item["output_file"] for item in summary["documents"]}) == 3
    assert all((destination / item["output_file"]).is_file() for item in summary["documents"])
    error = json.loads((destination / summary["documents"][1]["output_file"]).read_text(encoding="utf-8"))
    assert error["error"] == "ValueError: Broken PDF"
