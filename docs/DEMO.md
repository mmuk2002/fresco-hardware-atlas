# 3–5 minute demo walkthrough

Run the corpus import and local app first. Browser: http://127.0.0.1:8000. Zoom so the source and component fields are readable. Avoid claiming whole-corpus 90% accuracy from sampled labels.

| Time | Action and talking point |
|---|---|
| 0:00–0:30 | Introduce Hardware Atlas. It extracts hardware sets and preserves physical PDF locations. Explain that the provided download has 43 PDFs across 21 projects, including supporting documents and repeated schedules. |
| 0:30–1:15 | Open **JC Ryan / Door Hardware**, physical page **28**, sets **1.0 and 2.0**. Show the source highlight, centered multiline catalog text, full manufacturer names, absent finish column and blank hinge quantity. Explain that blank quantity stays null. |
| 1:15–1:50 | Edit a component note, save, switch sets and return. Download JSON. Explain that original extraction and corrections are stored separately, with source evidence retained. Undo the demo correction if using your working store. |
| 1:50–2:30 | Open **Roselle / Door Hardware**, physical page **17**, set **7.1** or **8.3**. Show the merged table and its unusual quantity-after-product layout. Explain compound manufacturer/product splitting and contextual column roles. |
| 2:30–3:05 | Open **Forest Park / Project Manual**, set **1**, physical pages **262 and 263**. Switch between its source spans while showing one set with five components. Explain how a new section stops continuation. |
| 3:05–3:45 | Show the tests/evaluation report and corpus audit. Discuss 18 development sets/91 components plus an additional 9 sets/51 components. Scores are sample-specific; whole-corpus accuracy is not established. Mention OCR and unfamiliar/revision layouts as review cases. |
| 3:45–4:00 | Close with local run steps, JSON/CSV exports, and the practical next step: a larger independent, template-disjoint labeled benchmark. |

For the code-resolution bonus, show a result containing `catalog_resolution`: the printed short code is retained, while the expansion and the code-table bounding box appear in JSON and CSV. The review UI renders the expansion directly under its component row. Explain that only explicit same-page lookup evidence triggers this behavior.

The optional generated MP4 uses actual browser interactions and a clearly synthetic system-voice narration. It is a local video file, not a published Loom link. Upload the MP4 to Loom, or use this script to record your own explanation.
