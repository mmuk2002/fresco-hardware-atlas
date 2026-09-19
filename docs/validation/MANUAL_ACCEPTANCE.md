# Manual acceptance pass

This is the final review pass performed after the frozen holdout evaluation. It
is evidence for submission review, not a claim that every printed component in
the corpus was independently transcribed.

## What was checked

- The corpus contains 43 PDFs. The saved corpus run completed all 43 without an
  extraction error: 1,304 set occurrences and 11,622 component rows.
- A structural sweep checked every saved result for page-count, set-count and
  component-count consistency with `output/corpus/summary.json`; non-empty set
  IDs and descriptions; locations on valid pages; boxes inside page bounds;
  component locations inside their parent set pages; unique IDs; valid
  confidence ranges; and empty components for `not_used` sets. Result:
  **0 issues** across 1,304 sets, 11,622 components and 13,116 locations.
- The audit manifest supplied a stratified visual sample: first, middle and
  last candidate schedule pages (plus an adjacent midpoint page where
  available) from 25 schedule-bearing PDFs. This produced 99 rendered pages.
  Three additional Roselle schedule pages (physical pages 15–17) were rendered
  because the ruled schedule begins after the document's introductory pages.
  All 102 renders were screened against the corresponding source PDF and JSON
  for schedule presence, set boundaries, continuation behavior, column layout,
  and coarse source-box alignment.
- The direct difficult cases were inspected at full resolution: Roselle's
  merged ruled table; Livelle's `PE`/`NO` manufacturer-column usage; Vantage's
  wrapped continuation rows and operation prose; StarHardware's watermarked
  unruled table; and the Bridgeport, Valor, Gerrard and Village of Oswego
  table families. No visual discrepancy was found in this pass.
- The real-PDF browser smoke test passed source overlays, editing, null
  quantities, correction persistence, JSON/CSV export, filtering, navigation,
  mobile layout and API recovery with no browser errors.

## Acceptance result

The manual pass supports submission of the implementation. The measured frozen
holdout remains the accuracy gate: 14/14 annotated sets, 126/126 components,
97.6% exact annotated rows, 100% quantity/catalog/manufacturer/finish accuracy
where those fields were unambiguous, zero observed manufacturer/finish swaps,
17/17 set-heading locations and 126/126 component locations.

The pass does not turn the holdout into a corpus-wide ground truth set. A true
corpus-wide 90% claim would still require independent transcription of every
active and unused schedule row, including OCR-only pages and all revision
variants. The correct submission wording is therefore “97.6% on the frozen
cross-format holdout; full corpus processed and structurally audited,” rather
than a guarantee about every one of the 11,622 rows.

## Reproduce the render-backed sample

From the repository root, after placing the supplied PDFs beside the project:

```powershell
.venv\Scripts\python.exe scripts\manual_acceptance_audit.py
.venv\Scripts\python.exe scripts\make_audit_contact_sheets.py
```

The generated manifest and renders are intentionally temporary and ignored by
Git. The source-page labels and numerical evaluation reports remain checked in
under `tests/fixtures/` and `docs/validation/`.
