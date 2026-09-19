# Validation: scope, results and reproducibility

## Corpus coverage

The supplied download contains **43 PDFs, 21 project folders and 17,637 physical pages**. Every file was scanned and processed. The final source-relative [corpus report](validation/corpus-summary.json) records per-document counts, status and runtime. Files with no detected sets retain warnings instead of silently appearing to be successful positive examples.

Schedule repetitions remain separate document occurrences: Gerrard's standalone schedule also appears in its full manual; Bridgeport's revision package repeats its first 49 pages. Thus extracted set totals are not a count of unique project hardware sets.

The [corpus audit](CORPUS_AUDIT.md) records source schedule ranges, layout families, supporting files, page continuations, aliases and revision concerns. It includes source-text inspection and targeted page renders. It is **not a full manual transcription of every row**.

## Source-transcribed evaluation

| Sample | Documents | Pages | Sets | Components | Annotated component fields |
|---|---:|---:|---:|---:|---|
| Development | 8 | 9 | 18 | 91 | Quantity, description, catalog, manufacturer, finish, notes |
| Additional project sample | 3 | 3 | 9 | 51 | Quantity, description, catalog, manufacturer, finish |
| Frozen, template-disjoint holdout | 8 | 10 | 14 | 126 | Quantity and description; catalog, manufacturer, and finish where unambiguous |

The development sample covers explicit and implicit columns, a merged landscape table, centered wrapping, null quantity, absent catalog/manufacturer columns, an unused set and a two-page set. Labels were transcribed from source text and targeted rendered pages, not copied from extractor output. These examples were used during debugging, so they are regression evidence.

The additional project sample uses Market View, National Doors and Hardware, and Shubie Center. Its labels were written before inspecting predictions for those selected pages. However, the projects had already been included in the corpus audit and share vendor templates with the development material. **It is not a blind, template-disjoint benchmark.** Notes were not annotated in that second sample; their accuracy is reported as undefined, not 100%.

Both evaluations matched all annotated sets and components, with exact normalized matches on every annotated component field and **zero observed manufacturer/finish swaps**. See the complete [development report](validation/evaluation-development.json) and [additional sample report](validation/evaluation-project-sample.json). These finite samples do not justify a claim of 90%+ accuracy across all supplied or unseen documents.

### Frozen holdout across new layout families

Eight pages were selected with seed `87100` from previously unannotated Bridgeport, Hospital, Morris, SAT, SJC, Star, Vantage, and Oswego schedule ranges. The [source manifest](validation/heldout-selection.json) preserves their file hashes and physical page numbers. `scripts/build_holdout_sources.py` fixes the page choices and renders source pages **without importing predictions**. The independently transcribed labels in `tests/fixtures/heldout_gold.json` were frozen before consulting the current full-corpus extraction. The primary [first-run holdout report](validation/evaluation-heldout.json) has not been rescored after inspecting errors.

- Set recall: **14/14** annotated set occurrences. Component recall: **126/126** printed rows.
- Component precision inside those sets: **126/129 = 97.7%**. Three extra rows appear, two from split Star rows and one from Vantage instructions.
- Exact annotated whole rows: **123/126 = 97.6%**. Quantity **126/126**; descriptions **123/126**; catalog **116/116**, manufacturer **115/115**, and finish **115/115** for fields that could be read unambiguously. **Zero observed manufacturer/finish swaps.** Notes were not independently scored in this holdout.
- On every printed heading of the eight pages plus the adjacent continuation pages, the [set-location check](validation/evaluation-holdout-locations.json) found **17/17** set headings with no extra set headings in that scope. Each PDF bounding box covers at least 90% of its independently searched printed heading.
- The [component-location check](validation/evaluation-holdout-component-locations.json) places an independently transcribed description word inside **126/126** matched component boxes.

The additional three printed headings beyond the 14 component-labeled sets are real boundary headings on Hospital/Vantage pages; the location check enumerates them. These are the first-pass results for a small cluster of eight page families. They establish measured performance above 90% **on this frozen sample**, not a mathematical guarantee for every row in all 43 PDFs or unknown future templates. Rows on one page are correlated, and scanned/OCR-only layouts are outside this native-text sample.

### Scoring rules

- Match set number with physical page overlap; preserve string IDs and repeated occurrences.
- Use maximum-weight one-to-one component assignment based on description/catalog identity. One predicted hinge row cannot satisfy two expected hinge rows.
- Score exact fields after Unicode, case, whitespace, typographic quote/dash and numeric-quantity normalization. Manufacturer synonyms and catalog-code expansions are not normalized away.
- Missing components count as wrong on every annotated field, including null fields.
- Count extra rows only inside annotated set/page regions. Unannotated sets are outside the sample, not assumed false positives.
- Report set precision as undefined for the component fixtures; the separate exhaustive 17-heading holdout scope measures heading precision and recall.
- Annotation notes omit the structural `Notes:` label and preserve source wording; no punctuation is invented between wrapped lines. Source boxes were visually checked on representative pages, but no corpus-wide IoU metric is claimed.

Reproduce the component samples from a full corpus run using the README commands. The CLI can also extract only labeled pages with `evaluate --source` for a faster check, though a single-page run can lose schema carried from earlier pages and should not replace the recorded full-corpus holdout score.

## Automated and browser checks

The automated suite covers the public extraction contract and failure-prone behavior: PE/NO under explicit reordered columns, genuine blank quantities, unused sets, a page-ending header, list and merged-table cross-page assembly, new-section termination, door assignment lists, quantity-after-catalog schemas, explicit same-page code resolution with source evidence, strikeouts versus underlines, overflowing prose, API error handling, upload limits, correction persistence and evaluation duplicate matching.

The Playwright browser smoke test uses an isolated store and real PDF results. It checks source highlights, editing, null quantities, draft retention, adding/removing rows, saved corrections, both exports, search/filtering, page/zoom controls, error recovery and mobile overflow. The test modifies its store, so do not point it at production review data.

The same-page catalog-resolution bonus is covered by a generated PDF with real word geometry: an explicit `CODE / DESCRIPTION / CATALOG / MFR / FINISH` table defines code `A`, and a component using `A` receives the complete expansion plus the lookup row's page and bounding box. The current supplied-corpus run produced zero such expansions because no detected component used a code from an explicit same-page lookup table. This test proves the behavior without presenting synthetic coverage as corpus accuracy.

```powershell
# Prepare an isolated store with a real extracted PDF first, then:
python -m hardware_sets serve --port 8001 --data-dir tmp/ui-store
python scripts/ui_smoke.py --url http://127.0.0.1:8001
```

## Remaining validation work

For a corpus-wide claim, an independent reviewer would need to transcribe all relevant schedules or a much larger stratified set of pages, including OCR schedules, every active and unused set on those pages, revised/struck material, and repeated template families. The current holdout quantifies eight new families and exact fields/locations but does not exhaust the 11,622 extracted rows. Calibrate heuristic scores only against independently judged correctness.
