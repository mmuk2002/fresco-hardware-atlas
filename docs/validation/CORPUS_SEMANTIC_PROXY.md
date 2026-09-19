# Exhaustive semantic proxy audit

To expand beyond a sampled gold set, the source PDFs were independently read by
a geometry-based checker. It uses the original page words and nearby `MFR`,
`MANUFACTURER`, and `FINISH` header positions, separate from the extraction
implementation. It then checks every saved row's manufacturer and finish values
against the source column geometry.

All 11,622 components were examined:

| Check | Rows |
|---|---:|
| Both nonblank values located with explicit nearby column headers | 3,044 |
| Both nonblank values located geometrically where no paired header was available | 3,925 |
| One nonblank value located (the other field is absent or blank) | 3,466 |
| Explicit blank sentinels (`--`, `---`, `__`) | 1,187 |
| Column-role exceptions after review-aware normalization | **0** |

This supports the manufacturer/finish mapping across the complete saved corpus,
including ambiguous short codes. The machine-readable output is
[corpus-semantic-proxy.json](corpus-semantic-proxy.json); rerun it with:

```powershell
.venv\Scripts\python.exe scripts\corpus_semantic_proxy_audit.py
```

This is stronger than parser self-agreement because it reads source geometry
directly, but it is still a proxy rather than a human-typed gold transcription.
It cannot judge every domain-specific interpretation of a value that is printed
near a row. The frozen, independently labeled holdout remains the semantic
accuracy benchmark.
