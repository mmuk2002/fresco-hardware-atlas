"""Command-line extraction, corpus processing, evaluation, and local review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from .storage import _atomic_json


def parse_pages(value: str) -> list[int]:
    """Parse one-based page selections, rejecting ambiguous or reversed ranges."""
    pages: set[int] = set()
    for part in value.split(","):
        match = re.fullmatch(r"\s*([1-9]\d*)(?:\s*-\s*([1-9]\d*))?\s*", part)
        if not match:
            raise argparse.ArgumentTypeError("Pages must look like 1-3,5 (one-based)")
        start, end = int(match[1]), int(match[2] or match[1])
        if end < start or end - start > 100_000:
            raise argparse.ArgumentTypeError("Page ranges must be ascending and at most 100,001 pages")
        pages.update(range(start, end + 1))
    return sorted(pages)


def output_name(relative_path: str) -> str:
    """Readable, stable names that cannot collide for repeated PDF basenames."""
    normalized = relative_path.replace("\\", "/")
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", str(Path(normalized).with_suffix(""))).strip("-.")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{label[:100] or 'document'}-{digest}.json"


def _extract(args: argparse.Namespace) -> int:
    from .extract import extract_pdf

    source = args.pdf.resolve(strict=True)
    with redirect_stdout(sys.stderr):
        result = extract_pdf(source, pages=args.pages, ocr=args.ocr)
    value = result.model_dump(mode="json")
    value["source_path"] = str(source)
    if args.output:
        _atomic_json(args.output, value)
        print(f"Extracted {len(result.sets)} sets to {args.output}", file=sys.stderr, flush=True)
    else:
        print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


def _corpus(args: argparse.Namespace) -> int:
    from .extract import extract_pdf
    from .storage import DocumentStore

    source = args.source.resolve(strict=True)
    if source.is_file():
        paths, root = [source], source.parent
    else:
        paths = sorted((path for path in source.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"),
                       key=lambda path: str(path.relative_to(source)).casefold())
        root = source
    if not paths:
        raise ValueError(f"No PDF files found in {source}")
    args.output.mkdir(parents=True, exist_ok=True)
    store = DocumentStore(args.data_dir) if args.register else None
    started = time.monotonic()
    documents: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"source_root": str(root), "document_count": len(paths), "documents": documents}
    for index, path in enumerate(paths, 1):
        relative = path.relative_to(root).as_posix()
        result_path = args.output / output_name(relative)
        item: dict[str, Any] = {"source_path": relative, "output_file": result_path.name}
        item_started = time.monotonic()
        print(f"[{index}/{len(paths)}] {relative}", file=sys.stderr, flush=True)
        try:
            with redirect_stdout(sys.stderr):
                result = extract_pdf(path, ocr=args.ocr)
            result.project = path.parent.name if path.parent != root else None
            value = result.model_dump(mode="json")
            value.update(source_path=relative, source_root=str(root))
            _atomic_json(result_path, value)
            item.update(status="ok", page_count=result.page_count, set_count=len(result.sets),
                        component_count=sum(len(item.components) for item in result.sets),
                        warning_count=len(result.warnings))
            if store is not None:
                document = store.import_pdf(path, project=result.project)
                store.save_result(document["id"], result)
                item["document_id"] = document["id"]
            print(f"  {item['set_count']} sets, {item['component_count']} components", file=sys.stderr, flush=True)
        except Exception as exc:
            # A broken PDF must not prevent the remaining corpus from running.
            item.update(status="error", error=f"{type(exc).__name__}: {exc}")
            # Replace any stale successful result for this path with an error artifact.
            _atomic_json(result_path, {"source_path": relative, "source_root": str(root), "error": item["error"]})
            print(f"  ERROR: {item['error']}", file=sys.stderr, flush=True)
        item["elapsed_seconds"] = round(time.monotonic() - item_started, 3)
        documents.append(item)
        summary.update(completed_count=len(documents),
                       success_count=sum(doc["status"] == "ok" for doc in documents),
                       error_count=sum(doc["status"] == "error" for doc in documents),
                       set_count=sum(doc.get("set_count", 0) for doc in documents),
                       component_count=sum(doc.get("component_count", 0) for doc in documents),
                       elapsed_seconds=round(time.monotonic() - started, 3))
        _atomic_json(args.output / "summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "documents"}, indent=2))
    return 1 if summary["error_count"] else 0


def _evaluate(args: argparse.Namespace) -> int:
    from .evaluation import evaluate, load_corpus, load_gold

    gold = load_gold(args.gold)
    if args.corpus:
        predictions = load_corpus(args.corpus)
    else:
        from .extract import extract_pdf

        selected: dict[str, set[int]] = {}
        for item in gold:
            selected.setdefault(item["source_path"], set()).update(item.get("pages", [item.get("page")]))
        predictions = []
        for relative, pages in selected.items():
            path = args.source / relative
            print(f"Extracting annotated pages {sorted(pages)}: {relative}", file=sys.stderr, flush=True)
            with redirect_stdout(sys.stderr):
                result = extract_pdf(path, pages=sorted(pages), ocr=args.ocr)
            value = result.model_dump(mode="json")
            value["source_path"] = relative
            predictions.append(value)
    report = evaluate(gold, predictions)
    if args.output:
        _atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn
    from .api import create_app

    uvicorn.run(create_app(args.data_dir), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hardware-sets", description="Extract door hardware sets with PDF evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="Extract a PDF into structured JSON")
    extract.add_argument("pdf", type=Path)
    extract.add_argument("--output", "-o", type=Path, help="JSON destination; default is stdout")
    extract.add_argument("--pages", type=parse_pages, help="One-based PDF pages, e.g. 1-3,5")
    extract.add_argument("--ocr", action="store_true", help="Use local Tesseract OCR on pages lacking text")
    extract.set_defaults(handler=_extract)

    corpus = commands.add_parser("corpus", help="Recursively extract every PDF, keeping an error/progress report")
    corpus.add_argument("source", type=Path)
    corpus.add_argument("--output", "-o", type=Path, default=Path("output/corpus"))
    corpus.add_argument("--register", action="store_true", help="Also register PDFs and results in the review UI")
    corpus.add_argument("--data-dir", type=Path, help="Review storage directory (default: data/app or FRESCO_DATA_DIR)")
    corpus.add_argument("--ocr", action="store_true")
    corpus.set_defaults(handler=_corpus)

    evaluate = commands.add_parser("evaluate", help="Score annotated sets and components against reviewed gold data")
    evaluate.add_argument("--gold", type=Path, default=Path("tests/fixtures/gold_sets.json"))
    prediction_source = evaluate.add_mutually_exclusive_group(required=True)
    prediction_source.add_argument("--corpus", type=Path, help="Directory of corpus result JSON files")
    prediction_source.add_argument("--source", type=Path, help="PDF corpus root; extract only gold-selected pages")
    evaluate.add_argument("--output", "-o", type=Path)
    evaluate.add_argument("--ocr", action="store_true")
    evaluate.set_defaults(handler=_evaluate)

    serve = commands.add_parser("serve", help="Launch the local PDF review and correction UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--data-dir", type=Path)
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Completed corpus documents remain saved.", file=sys.stderr)
        return 130
