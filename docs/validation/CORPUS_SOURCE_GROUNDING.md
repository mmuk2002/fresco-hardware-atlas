# Exhaustive corpus source-grounding audit

The saved corpus output was checked against the original PDFs row by row. This
is a source-grounding audit, not an independently transcribed gold set: it
proves that extracted values and locations point back to printed source text,
but it cannot by itself decide whether a nearby printed value belongs in the
semantic field chosen by the parser.

The audit covered all 43 PDFs, 1,304 set occurrences and 11,622 components.
Every component location was a valid, non-empty box inside its physical PDF
page. Every component description had sufficient normalized token overlap with
the words inside its saved source box: **11,622/11,622**. The raw printed row
text was grounded for **11,620/11,622** rows; two rows are formatting edge cases
where the saved raw string does not fit the row box's tokenization, although
their descriptions and fields remain grounded. Every non-null catalog number,
manufacturer and finish value was found inside its source box:

| Field | Grounded | Null or absent | Total |
|---|---:|---:|---:|
| Catalog number | 11,284 | 338 | 11,622 |
| Manufacturer | 8,567 | 3,055 | 11,622 |
| Finish | 8,240 | 3,382 | 11,622 |

The machine-readable result is [corpus-source-grounding.json](corpus-source-grounding.json).
Reproduce it with:

```powershell
.venv\Scripts\python.exe scripts\corpus_source_grounding_audit.py
```

This exhaustive check complements the independently labeled frozen holdout;
it does not replace one. A corpus-wide accuracy percentage still requires an
independent transcription of the expected semantic fields.
