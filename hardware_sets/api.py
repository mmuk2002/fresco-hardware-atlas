"""Local review API. Run with uvicorn hardware_sets.api:app --host 127.0.0.1."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import pymupdf
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .models import ExtractionResult, HardwareSet
from .storage import (
    DocumentNotFoundError,
    DocumentStore,
    ExtractionNotFoundError,
    InvalidPDFError,
    export_csv,
)

logger = logging.getLogger(__name__)


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pages: list[int] | None = Field(default=None, min_length=1)
    ocr: bool = False


def extract_pdf(path: str | Path, pages: list[int] | None = None, ocr: bool = False) -> ExtractionResult:
    """Lazy import keeps the review API independently testable."""
    from .extract import extract_pdf as run_extraction

    return run_extraction(path, pages=pages, ocr=ocr)


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Fresco Hardware Sets", version="0.1.0")
    store = DocumentStore(data_dir)
    app.state.store = store
    max_upload_bytes = int(os.getenv("FRESCO_MAX_UPLOAD_MB", "250")) * 1024 * 1024

    @app.middleware("http")
    async def local_write_origin(request: Request, call_next):
        # A local app has no cross-origin callers. Reject browser writes from
        # unrelated websites, including simple multipart/form-data requests.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            expected_origin = f"{request.url.scheme}://{request.url.netloc}"
            if origin and origin.rstrip("/") != expected_origin:
                return JSONResponse({"detail": "Cross-origin writes are not permitted"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(DocumentNotFoundError)
    async def missing_document(request: Request, exc: DocumentNotFoundError):
        return JSONResponse({"detail": "Document not found"}, status_code=404)

    @app.exception_handler(ExtractionNotFoundError)
    async def missing_extraction(request: Request, exc: ExtractionNotFoundError):
        return JSONResponse({"detail": "Document has not been extracted yet"}, status_code=404)

    @app.exception_handler(FileNotFoundError)
    async def missing_source(request: Request, exc: FileNotFoundError):
        return JSONResponse({"detail": "The registered source PDF is no longer available"}, status_code=410)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "schema_version": "1.0"}

    @app.get("/api/documents")
    def documents():
        return store.list_documents()

    @app.post("/api/documents", status_code=201)
    def upload_document(file: UploadFile = File(...)):
        name = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
        if not name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Upload a PDF file")
        # Streams to local disk with a limit; contents never leave this machine.
        with tempfile.TemporaryDirectory(prefix="upload-", dir=store.data_dir) as temporary:
            path = Path(temporary) / "upload.pdf"
            size = 0
            with path.open("wb") as destination:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_upload_bytes:
                        raise HTTPException(status_code=413, detail="PDF exceeds the configured upload limit")
                    destination.write(chunk)
            if not size:
                raise HTTPException(status_code=400, detail="The uploaded file is empty")
            try:
                return store.import_pdf(path, copy=True, name=name)
            except InvalidPDFError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/documents/{document_id}/extract", response_model=ExtractionResult)
    def extract_document(document_id: str, options: ExtractRequest | None = None):
        options = options or ExtractRequest()
        metadata = store.get_document(document_id)
        if options.pages is not None and any(page < 1 or page > metadata["page_count"] for page in options.pages):
            raise HTTPException(status_code=422, detail="Page numbers must be within the document's one-based page range")
        source = store.pdf_path(document_id)
        try:
            result = extract_pdf(source, pages=sorted(set(options.pages)) if options.pages else None, ocr=options.ocr)
            return store.save_result(document_id, result)
        except (InvalidPDFError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Extraction failed for document %s", document_id)
            raise HTTPException(status_code=500, detail="Extraction failed; see the local server log for details") from exc

    @app.get("/api/documents/{document_id}", response_model=ExtractionResult)
    def document_result(document_id: str):
        return store.get_result(document_id)

    @app.get("/api/documents/{document_id}/pages/{page}.png")
    def page_image(document_id: str, page: int):
        metadata = store.get_document(document_id)
        if page < 1 or page > metadata["page_count"]:
            raise HTTPException(status_code=404, detail="Page not found")
        with pymupdf.open(store.pdf_path(document_id)) as pdf:
            source = pdf[page - 1]
            scale = min(2.0, 2000 / max(source.rect.width, source.rect.height))
            pixmap = source.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return Response(content=pixmap.tobytes("png"), media_type="image/png", headers={"Cache-Control": "private, max-age=300"})

    @app.put("/api/documents/{document_id}/sets/{set_id}", response_model=HardwareSet)
    def correct_set(document_id: str, set_id: str, replacement: HardwareSet):
        try:
            return store.correct_set(document_id, set_id, replacement)
        except (DocumentNotFoundError, ExtractionNotFoundError):
            raise
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Set not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/documents/{document_id}/corrections")
    def correction_audit(document_id: str):
        return store.correction_audit(document_id)

    @app.get("/api/documents/{document_id}/export")
    def export_document(document_id: str, format: Literal["json", "csv"] = Query(default="json")):
        result = store.get_result(document_id)
        filename = f"{Path(result.name).stem}.hardware-sets.{format}"
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}"}
        if format == "csv":
            return Response(content=export_csv(result), media_type="text/csv", headers=headers)
        return Response(content=result.model_dump_json(indent=2), media_type="application/json", headers=headers)

    static_directory = Path(__file__).parent / "static"
    if static_directory.is_dir():
        app.mount("/static", StaticFiles(directory=static_directory), name="review-assets")

        @app.get("/", include_in_schema=False)
        def review_ui():
            return FileResponse(static_directory / "index.html")
    return app


app = create_app()
