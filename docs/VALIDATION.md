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

The development sample covers explicit and implicit columns, a merged landscape table, centered wrapping, null quantity, absent catalog/manufacturer columns, an unused set and a two-page set. Labels were transcribed from source text and targeted rendered pages, not copied from extractor output. These examples were used during debugging, so they are regression evidence.

The additional project sample uses Market View, National Doors and Hardware, and Shubie Center. Its labels were written before inspecting predictions for those selected pages. However, the projects had already been included in the corpus audit and share vendor templates with the development material. **It is not a blind, template-disjoint benchmark.** Notes were not annotated in that second sample; their accuracy is reported as undefined, not 100%.

Both evaluations matched all annotated sets and components, with exact normalized matches on every annotated component field and **zero observed manufacturer/finish swaps**. See the complete [development report](validation/evaluation-development.json) and [additional sample report](validation/evaluation-project-sample.json). These finite samples do not justify a claim of 90%+ accuracy across all supplied or unseen documents.

### Scoring rules

- Match set number with physical page overlap; preserve string IDs and repeated occurrences.
- Use maximum-weight one-to-one component assignment based on description/catalog identity. One predicted hinge row cannot satisfy two expected hinge rows.
- Score exact fields after Unicode, case, whitespace, typographic quote/dash and numeric-quantity normalization. Manufacturer synonyms and catalog-code expansions are not normalized away.
- Missing components count as wrong on every annotated field, including null fields.
- Count extra rows only inside annotated set/page regions. Unannotated sets are outside the sample, not assumed false positives.
- Report set precision as undefined: exhaustive set labels are needed to calculate it.
- Annotation notes omit the structural `Notes:` label and preserve source wording; no punctuation is invented between wrapped lines. Source boxes were visually checked on representative pages, but no corpus-wide IoU metric is claimed.

Reproduce either sample from a full corpus run using the README commands. The CLI can also extract only labeled pages with `evaluate --source` for a faster check.

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

A defensible general accuracy estimate needs substantially more independent labels, including all active sets and unused placeholders on each chosen page, OCR schedules, changed/struck text, and unfamiliar vendor layouts. Split by template family as well as project. Measure complete-set correctness, set precision/recall, field accuracy, manufacturer/finish swaps, quantity-null correctness and page/bounding-box agreement. Calibrate heuristic scores only against independently judged correctness.
