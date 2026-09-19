# Hardware set extraction: implementation and validation plan

## Acceptance criteria

1. Inventory every supplied PDF, including supporting sections and specbooks without hardware schedules.
2. Extract set IDs, optional descriptions, components and page-specific source regions.
3. Determine manufacturer and finish roles from column context, not ambiguous tokens alone.
4. Preserve unused sets, missing quantities, wrapped rows and multi-page continuations.
5. Provide a runnable local review application, reproducible CLI and JSON export.
6. Retain raw evidence and explain uncertain mappings. Corrections must survive a restart.
7. Report measured validation separately from corpus processing coverage; do not claim 90% accuracy without sufficient independently labeled evidence.

## Work sequence

- Inventory PDFs and extract text with page boundaries; identify all schedule families and exceptional pages.
- Inspect relevant pages from every project and record findings in a corpus audit.
- Implement typed output, geometric row reconstruction, stateful set segmentation and contextual column inference.
- Add source overlays, review/correction storage and exports.
- Build representative, independently transcribed gold examples and adversarial regression cases.
- Run the entire corpus; investigate missing schedules, false positives and suspicious field mappings.
- Document setup, architecture, evidence, limitations and a 3–5 minute demo script.

## Design principles

- Native PDF text first; OCR is a distinct path and must be reported.
- Preserve printed codes and quantities; normalization does not fabricate missing data.
- PDF pages are one-based; rectangles use points from the top-left. Multi-page sets have multiple location spans.
- Component evidence and extraction results remain available after user corrections.
- Confidence scores are heuristic review aids, not calibrated probabilities.
- Input PDFs stay out of the source repository.

## Research sources

- pdfplumber word geometry and table APIs: https://github.com/jsvine/pdfplumber
- pypdfium2 rendering and text APIs: https://pypdfium2.readthedocs.io/en/stable/python_api.html
- Tesseract TSV and word confidence: https://github.com/tesseract-ocr/tesseract/blob/main/doc/tesseract.1.asc
- OCR preprocessing and table limitations: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- PyMuPDF licensing: https://pymupdf.readthedocs.io/en/latest/faq/index.html

The initial research favors deterministic, evidence-preserving extraction. Any optional model fallback should address a measured failure class and never replace source locations with invented coordinates.
