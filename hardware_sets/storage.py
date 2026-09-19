"""Local, atomic storage. Original extractions and human corrections stay separate."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pymupdf

from .models import ExtractionResult, HardwareSet


class DocumentNotFoundError(KeyError):
    pass


class ExtractionNotFoundError(KeyError):
    pass


class InvalidPDFError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _validate_pdf(path: Path) -> int:
    try:
        with path.open("rb") as stream:
            if b"%PDF-" not in stream.read(1024):
                raise InvalidPDFError("File does not have a PDF header")
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass:
                raise InvalidPDFError("Password-protected PDFs are not supported")
            if not pdf.is_pdf or pdf.page_count == 0:
                raise InvalidPDFError("PDF has no readable pages")
            return pdf.page_count
    except InvalidPDFError:
        raise
    except Exception as exc:
        raise InvalidPDFError("File is not a readable PDF") from exc


class DocumentStore:
    """One local application's repository; IDs, never browser paths, select files."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or os.getenv("FRESCO_DATA_DIR", "data/app")).resolve()
        self.documents_dir = self.data_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _directory(self, document_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", document_id):
            raise DocumentNotFoundError(document_id)
        return self.documents_dir / document_id

    def get_document(self, document_id: str) -> dict[str, Any]:
        """Internal metadata, including source_path. Do not return directly to clients."""
        path = self._directory(document_id) / "document.json"
        if not path.is_file():
            raise DocumentNotFoundError(document_id)
        return _read_json(path)

    def pdf_path(self, document_id: str) -> Path:
        path = Path(self.get_document(document_id)["source_path"])
        if not path.is_file():
            raise FileNotFoundError("The registered source PDF is no longer available")
        return path

    def import_pdf(
        self,
        path: str | Path,
        *,
        project: str | None = None,
        copy: bool = False,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Register a local PDF; copy=True keeps an owned copy (used for uploads).

        Identical bytes are deduplicated. CLI imports can reference their original
        local path without duplicating large specification books.
        """
        source = Path(path).resolve(strict=True)
        page_count = _validate_pdf(source)
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        with self._lock:
            for metadata_path in self.documents_dir.glob("*/document.json"):
                metadata = _read_json(metadata_path)
                if metadata.get("sha256") == digest:
                    # An upload can restore a previously registered missing source.
                    if not Path(metadata["source_path"]).is_file():
                        stored = metadata_path.parent / "source.pdf"
                        shutil.copyfile(source, stored)
                        metadata["source_path"] = str(stored)
                        _atomic_json(metadata_path, metadata)
                    return self.summary(metadata["id"])
            document_id = uuid4().hex
            directory = self._directory(document_id)
            directory.mkdir()
            stored = directory / "source.pdf" if copy else source
            if copy:
                shutil.copyfile(source, stored)
            metadata = {
                "id": document_id,
                "name": (name or source.name).replace("\\", "/").rsplit("/", 1)[-1],
                "project": project,
                "page_count": page_count,
                "sha256": digest,
                "source_path": str(stored),
                "created_at": _now(),
                "updated_at": _now(),
                "status": "uploaded",
            }
            _atomic_json(directory / "document.json", metadata)
            return self.summary(document_id)

    def summary(self, document_id: str) -> dict[str, Any]:
        metadata = self.get_document(document_id)
        summary = {key: value for key, value in metadata.items() if key != "source_path"}
        summary.update(set_count=0, component_count=0, warning_count=0, corrected_count=0)
        try:
            result = self.get_result(document_id)
        except ExtractionNotFoundError:
            return summary
        summary.update(
            set_count=len(result.sets),
            component_count=sum(len(item.components) for item in result.sets),
            warning_count=(len(result.warnings) + sum(
                len(item.warnings) + sum(len(component.warnings) for component in item.components)
                for item in result.sets
            )),
            corrected_count=sum(item.corrected for item in result.sets),
        )
        return summary

    def list_documents(self) -> list[dict[str, Any]]:
        summaries = [self.summary(path.parent.name) for path in self.documents_dir.glob("*/document.json")]
        return sorted(summaries, key=lambda item: (item.get("project") or "", item["name"].casefold()))

    def save_result(self, document_id: str, result: ExtractionResult) -> ExtractionResult:
        with self._lock:
            metadata = self.get_document(document_id)
            original = result.model_copy(deep=True)
            original.id = document_id
            original.name = metadata["name"]
            original.project = metadata.get("project") or original.project
            original.page_count = metadata["page_count"]
            for item in original.sets:
                item.corrected = False
            _atomic_json(self._directory(document_id) / "extraction.json", original.model_dump(mode="json"))
            metadata.update(status="extracted", updated_at=_now())
            _atomic_json(self._directory(document_id) / "document.json", metadata)
            return self.get_result(document_id)

    def get_result(self, document_id: str, *, apply_corrections: bool = True) -> ExtractionResult:
        self.get_document(document_id)
        path = self._directory(document_id) / "extraction.json"
        if not path.is_file():
            raise ExtractionNotFoundError(document_id)
        result = ExtractionResult.model_validate(_read_json(path))
        corrections_path = path.parent / "corrections.json"
        if apply_corrections and corrections_path.is_file():
            corrections = _read_json(corrections_path).get("sets", {})
            known_ids = {item.id for item in result.sets}
            result.sets = [
                HardwareSet.model_validate(corrections[item.id]["value"])
                if item.id in corrections else item
                for item in result.sets
            ]
            if set(corrections) - known_ids:
                result.warnings.append("Some saved corrections refer to sets absent from the current extraction; review the correction audit.")
            result.stats["corrected_sets"] = sum(item.corrected for item in result.sets)
        return result

    def correct_set(self, document_id: str, set_id: str, replacement: HardwareSet) -> HardwareSet:
        with self._lock:
            result = self.get_result(document_id)
            previous = next((item for item in result.sets if item.id == set_id), None)
            if previous is None:
                raise KeyError("Set not found")
            if replacement.id != set_id:
                raise ValueError("The correction ID must match the set being corrected")
            corrected = replacement.model_copy(deep=True)
            corrected.corrected = True
            if any(location.page > result.page_count for location in corrected.locations):
                raise ValueError("Correction references a page outside this document")
            if any(location.page > result.page_count for component in corrected.components for location in component.locations):
                raise ValueError("Component references a page outside this document")
            path = self._directory(document_id) / "corrections.json"
            layer = _read_json(path) if path.is_file() else {"sets": {}, "audit": []}
            timestamp = _now()
            value = corrected.model_dump(mode="json")
            layer["sets"][set_id] = {"updated_at": timestamp, "value": value}
            layer["audit"].append({
                "timestamp": timestamp,
                "set_id": set_id,
                "before": previous.model_dump(mode="json"),
                "after": value,
            })
            # Changes and their audit records commit together in one atomic file.
            _atomic_json(path, layer)
            metadata = self.get_document(document_id)
            metadata["updated_at"] = timestamp
            _atomic_json(path.parent / "document.json", metadata)
            return corrected

    def correction_audit(self, document_id: str) -> list[dict[str, Any]]:
        self.get_document(document_id)
        path = self._directory(document_id) / "corrections.json"
        return _read_json(path).get("audit", []) if path.is_file() else []


def export_csv(result: ExtractionResult) -> str:
    """Flatten components while retaining empty sets and multi-page locations."""
    fields = ["document", "project", "set_number", "set_description", "status", "pages", "locations",
              "qty", "description", "catalog_number", "mfr", "finish", "notes",
              "resolved_code", "resolved_description", "resolved_catalog_number", "resolved_mfr",
              "resolved_finish", "resolution_location", "corrected"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for item in result.sets:
        base = {
            "document": result.name, "project": result.project or "", "set_number": item.set_number,
            "set_description": item.description or "", "status": item.status,
            "pages": ";".join(str(page) for page in sorted({loc.page for loc in item.locations})),
            "locations": json.dumps([loc.model_dump(mode="json") for loc in item.locations]),
            "corrected": item.corrected,
        }
        for component in item.components or [None]:
            row = dict(base)
            if component is not None:
                row.update({field: getattr(component, field) for field in
                            ["qty", "description", "catalog_number", "mfr", "finish", "notes"]})
                if component.catalog_resolution:
                    resolution = component.catalog_resolution
                    row.update({
                        "resolved_code": resolution.code,
                        "resolved_description": resolution.description,
                        "resolved_catalog_number": resolution.catalog_number,
                        "resolved_mfr": resolution.mfr,
                        "resolved_finish": resolution.finish,
                        "resolution_location": json.dumps(resolution.location.model_dump(mode="json")),
                    })
            else:
                row["notes"] = "; ".join(item.notes)
            # Exported PDFs can contain arbitrary text. Avoid spreadsheet formulas.
            for key, value in row.items():
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    row[key] = "'" + value
            writer.writerow(row)
    return stream.getvalue()
