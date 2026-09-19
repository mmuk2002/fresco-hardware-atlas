"""Exercise real PDFs, HTTP contracts, and persistence independently of parsing."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from hardware_sets import api
from hardware_sets.models import Component, ExtractionResult, HardwareSet, Location
from hardware_sets.storage import DocumentStore


@pytest.fixture
def pdf_bytes() -> bytes:
    with pymupdf.open() as pdf:
        for number in (1, 2):
            page = pdf.new_page(width=612, height=792)
            page.insert_text((60, 80), f"HARDWARE SET {number}")
            page.insert_text((60, 110), "3 Hinge BB1279 630 MK")
        return pdf.tobytes()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(api.create_app(tmp_path / "app"))


def upload(client: TestClient, pdf_bytes: bytes) -> dict:
    response = client.post("/api/documents", files={"file": ("schedule.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 201, response.text
    return response.json()


def example_result() -> ExtractionResult:
    location = Location(page=1, bbox=[60, 65, 330, 120], page_width=612, page_height=792)
    return ExtractionResult(
        name="temporary.pdf", page_count=2,
        sets=[
            HardwareSet(id="set-1", set_number="1", description="ENTRANCE", locations=[location], confidence=0.9,
                        components=[Component(id="component-1", qty=None, description="Hinge", catalog_number="BB1279",
                                              mfr="MK", finish="630", locations=[location], raw_text="Hinge BB1279 630 MK")]),
            HardwareSet(id="set-2", set_number="2", status="not_used", locations=[location]),
        ],
    )


def test_upload_deduplicates_and_does_not_disclose_source_paths(client: TestClient, pdf_bytes: bytes):
    document = upload(client, pdf_bytes)
    assert document["page_count"] == 2
    assert document["status"] == "uploaded"
    assert "source_path" not in document
    assert upload(client, pdf_bytes)["id"] == document["id"]
    listed = client.get("/api/documents").json()
    assert len(listed) == 1
    assert "source_path" not in listed[0]
    assert client.get(f"/api/documents/{document['id']}").status_code == 404


def test_extraction_and_corrections_keep_original_and_survive_reload(client: TestClient, pdf_bytes: bytes, monkeypatch):
    document = upload(client, pdf_bytes)
    document_id = document["id"]
    calls = []

    def stub(path, pages=None, ocr=False):
        calls.append((Path(path).is_file(), pages, ocr))
        return example_result()

    monkeypatch.setattr(api, "extract_pdf", stub)
    response = client.post(f"/api/documents/{document_id}/extract", json={"pages": [2, 1, 2]})
    assert response.status_code == 200, response.text
    assert calls == [(True, [1, 2], False)]
    result = response.json()
    assert result["id"] == document_id
    assert result["name"] == "schedule.pdf"
    assert result["sets"][0]["components"][0]["qty"] is None
    corrected = result["sets"][0]
    corrected["components"][0]["mfr"] = "PE"
    corrected["components"][0]["qty"] = 3
    response = client.put(f"/api/documents/{document_id}/sets/set-1", json=corrected)
    assert response.status_code == 200, response.text
    assert response.json()["corrected"] is True

    store = DocumentStore(client.app.state.store.data_dir)
    assert store.get_result(document_id).sets[0].components[0].mfr == "PE"
    assert store.get_result(document_id, apply_corrections=False).sets[0].components[0].mfr == "MK"
    audit = client.get(f"/api/documents/{document_id}/corrections").json()
    assert len(audit) == 1
    assert audit[0]["before"]["components"][0]["qty"] is None
    assert audit[0]["after"]["components"][0]["qty"] == 3
    assert store.summary(document_id)["corrected_count"] == 1

    # Re-extraction preserves review edits, instead of silently overwriting them.
    assert client.post(f"/api/documents/{document_id}/extract").status_code == 200
    assert store.get_result(document_id).sets[0].components[0].mfr == "PE"
    assert store.get_result(document_id, apply_corrections=False).sets[0].components[0].qty is None


def test_exports_include_unused_sets_and_all_page_spans(client: TestClient, pdf_bytes: bytes):
    document = upload(client, pdf_bytes)
    result = example_result()
    result.sets[0].locations.append(Location(page=2, bbox=[60, 60, 320, 90], page_width=612, page_height=792))
    result.sets[0].components[0].description = "=unsafe spreadsheet formula"
    client.app.state.store.save_result(document["id"], result)
    response = client.get(f"/api/documents/{document['id']}/export?format=csv")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 2
    assert rows[0]["pages"] == "1;2"
    assert len(json.loads(rows[0]["locations"])) == 2
    assert rows[0]["qty"] == ""
    assert rows[0]["description"].startswith("'=")
    assert rows[1]["status"] == "not_used"
    response = client.get(f"/api/documents/{document['id']}/export?format=json")
    assert response.json()["sets"][0]["components"][0]["description"].startswith("=")
    assert "attachment" in response.headers["content-disposition"]


def test_real_page_render_and_page_validation(client: TestClient, pdf_bytes: bytes):
    document = upload(client, pdf_bytes)
    response = client.get(f"/api/documents/{document['id']}/pages/1.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert client.get(f"/api/documents/{document['id']}/pages/0.png").status_code == 404
    assert client.get(f"/api/documents/{document['id']}/pages/3.png").status_code == 404
    assert client.post(f"/api/documents/{document['id']}/extract", json={"pages": [0]}).status_code == 422
    assert client.post(f"/api/documents/{document['id']}/extract", json={"pages": []}).status_code == 422


def test_bad_upload_missing_ids_and_cross_origin_writes(client: TestClient, pdf_bytes: bytes):
    response = client.post("/api/documents", files={"file": ("bad.pdf", b"not a PDF", "application/pdf")})
    assert response.status_code == 400
    assert client.get("/api/documents/not-an-id").status_code == 404
    assert client.get("/api/documents/" + "a" * 32).status_code == 404
    response = client.post("/api/documents", files={"file": ("file.pdf", pdf_bytes)}, headers={"Origin": "https://unrelated.example"})
    assert response.status_code == 403


def test_upload_limit(tmp_path: Path, pdf_bytes: bytes, monkeypatch):
    monkeypatch.setenv("FRESCO_MAX_UPLOAD_MB", "0")
    client = TestClient(api.create_app(tmp_path / "limited"))
    assert client.post("/api/documents", files={"file": ("file.pdf", pdf_bytes)}).status_code == 413
    assert client.get("/api/documents").json() == []


def test_correction_rejects_id_and_location_changes(client: TestClient, pdf_bytes: bytes):
    document = upload(client, pdf_bytes)
    client.app.state.store.save_result(document["id"], example_result())
    correction = example_result().sets[0].model_dump(mode="json")
    correction["id"] = "other-set"
    assert client.put(f"/api/documents/{document['id']}/sets/set-1", json=correction).status_code == 422
    correction["id"] = "set-1"
    correction["locations"][0]["page"] = 3
    assert client.put(f"/api/documents/{document['id']}/sets/set-1", json=correction).status_code == 422
    assert client.get(f"/api/documents/{document['id']}/corrections").json() == []


def test_local_import_references_original_and_restores_missing_source(tmp_path: Path, pdf_bytes: bytes):
    source = tmp_path / "original.pdf"
    source.write_bytes(pdf_bytes)
    store = DocumentStore(tmp_path / "store")
    document = store.import_pdf(source, project="Sample")
    assert store.pdf_path(document["id"]) == source
    source.unlink()
    replacement = tmp_path / "replacement.pdf"
    replacement.write_bytes(pdf_bytes)
    restored = store.import_pdf(replacement, copy=True)
    assert restored["id"] == document["id"]
    assert store.pdf_path(document["id"]).read_bytes() == pdf_bytes

