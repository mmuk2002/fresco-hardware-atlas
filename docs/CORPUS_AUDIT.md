# Source corpus audit

The downloaded folder contains **43 PDFs, 17,637 physical pages, and 21 project folders**. The challenge description's approximate document count is not the file count in this download. Several projects contain separate door, frame, glazing, or catalog documents; several manuals repeat a hardware schedule. Counting every PDF as an independent positive example would distort evaluation.

Page numbers below are **one-based physical PDF pages**, not the printed specification page labels. For example, Livelle's PDF page 643 is printed `08 71 00 - 27`. Bounding boxes use top-left PDF points, matching these physical page numbers.

## What was inspected

Every PDF was inventoried and its complete text layer scanned, with per-page text, page dimensions, candidate header lines, character counts, and source hashes recorded under `data/audit/`. The schedule ranges below were reviewed in the extracted source text, including neighboring pages and section endings. Targeted visual checks were used for difficult page layouts, including Roselle's merged tables and SJC's revision strikeouts. This is a document and layout audit, **not a complete manual transcription of every component**. Text-poor pages require separate OCR/image triage; they are not evidence of an empty schedule.

The initial keyword index deliberately overselects prose references and also misses important layouts. It is a discovery aid, not ground truth: Roselle pages 15–17 and SJC pages 711–748 do not match its original `Set:`/`Group No.` pattern; Vantage page 396 continues a set without repeating its header. Source boundary inspection corrected these ranges.

## Inventory: all 43 PDFs

IDs correspond to `data/audit/manifest.json`. A count marked “headers” means observed source headings, not a claim of independently verified end-to-end extraction accuracy. Revision duplicates and aliases are called out explicitly.

| # | Project / PDF | Pages | Schedule pages and source findings |
|---|---|---:|---|
| 1 | Gerrard Shelter — architectural specifications (`e93500e2d0b8`) | 255 | **165–182**. 35 sets: AL01, 01–14, 16–32, U01–U03. Repeated in the standalone hardware PDF. No invented set 15. |
| 2 | Gerrard Shelter — Hdw Spec & Sch-IFT_5 (`f989646d6649`) | 36 | **19–36**. Same 35-set schedule as the architectural manual; a duplicate source, not 35 additional independent examples. |
| 3 | Bridgeport — 08-10-00 Hollow Metal Doors & Frames (`341aef0f4201`) | 3 | No named hardware component sets. Door/frame requirements only. |
| 4 | Bridgeport — 08-20-00 Wood Doors (`658ef942c4c4`) | 3 | No named hardware component sets. Door requirements only. |
| 5 | Bridgeport — 08-70-00 Hardware Schedule (`a5e8f3117ef3`) | 49 | **3–49**. `Heading #` family, 1–90. Heading 17 continues from 11 to 12; heading 59 from 33 to 34. Preserve continuation pages. |
| 6 | Bridgeport — 08-70-00 Hardware Schedule Rev_0 (`bd0d7a84a7f4`) | 238 | **3–49** repeats the preceding schedule. Pages **50–238** are scanned catalog attachments, not an additional 189-page set schedule. OCR warnings must distinguish these from schedule pages. |
| 7 | AMI — ATC renovation volume 1 (`732e25ba567d`) | 611 | **397–419**. 44 groups including 01, 01A and X01–X06. Explicit quantity/unit/description/catalog/finish/manufacturer schema; catalog-link and lightning symbols can touch finish text. |
| 8 | Forest Park School — Project Manual (`62352a83993f`) | 344 | **262–263**. Set #1, five components across a page break. `Group 1` on page 192 is stainless-steel bolt prose, not a hardware-set header. |
| 9 | HFH DG Hospital — 08 71 00 Door Hardware (`76133601338e`) | 184 | **20–183**. Large schedule with repeated numbers, bulletin/revision headings, many page continuations, and strikeouts. Some automatic-operator/seal/diagram rows omit quantity. Raw header count must not be treated as active-set count. |
| 10 | HFH DG Hospital — Door Hardware Index cut up (`b33e77cf35a6`) | 32 | Door-number-to-hardware-set index; no component lists. Preserve as supporting evidence, not empty component sets for each indexed door. |
| 11 | JC Ryan — Hollow Metal Doors & Frames (`e5c107303ea0`) | 13 | No named hardware component sets. |
| 12 | JC Ryan — Flush Wood Doors (`b3f0cd9f2dca`) | 8 | No named hardware component sets. |
| 13 | JC Ryan — 087100 Door Hardware-6 (`5f1daa9454b6`) | 46 | **24–46**. 38 sets including EX1.0–EX4.0 and decimal variants such as 2.5. Centered multiline cells; full manufacturer names and no finish column. Missing hinge quantities remain null. EX2.0 spans 24–25. |
| 14 | Livelle — volume 1 rev1 (`7e0be4776a7d`) | 1,191 | **643–700**. 161 headers, `Set: 1.0` through 151.0 plus decimal variants and MISC. Separate `Description:` line. Quantity/description/catalog/finish/manufacturer columns. PE and NO occur in the manufacturer column; do not interpret as finishes or prose. |
| 15 | Livelle — volume 2 (`13cf517c2bff`) | 530 | No embedded named hardware schedule found. Isolated `hardware set` references are not sets. |
| 16 | Livelle — volume 3 rev1 (`649809bbf720`) | 580 | No named hardware schedule found. Equipment/catalog tables contain unrelated quantities, finishes and N/A values. |
| 17 | Livelle — volume 4 (`152aab1ae1ac`) | 103 | No named hardware schedule found. Furniture/equipment material is not a door hardware schedule. |
| 18 | Lyons Township HS — Project Manual (`397f86f066e3`) | 309 | **285–294**. 29 groups 01–29. **05, 16, 21, 22 explicitly Not Used** and must remain as empty sets with status. Explicit finish then manufacturer columns; nearby link/lightning icons are not codes. |
| 19 | Market View Apartments — preliminary project manual (`1da915a893a2`) | 1,053 | **770–780**. 24 groups 01–24. Long headings, electrical symbols and wrapped catalog numbers. Group 03 says hardware by door manufacturer; lack of itemized components is not Not Used. Group 1 bolt prose on 441 is a false candidate. |
| 20 | Morris Bank — full specifications (`917cb16278fd`) | 722 | **233–263** and **283–290** are two schedules in one file: 31 and 18 headers. 49 occurrences, 48 distinct printed IDs because MISC appears in both. `Set #101`, `Set #101.68`, CR38, etc. N/A in opening dimensions does not mean the set is unused. First schedule includes handing and `Properties:` lines. |
| 21 | National Doors and Hardware — FS17 volume 1 (`2e0d7ccb8963`) | 566 | **406–412**. 15 groups 01–15. Manufacturer abbreviation legend on 406; explicit QTY/DESCRIPTION/CATALOG NUMBER/FINISH/MFR. Group 15 has “ALL HARDWARE / BY GATE MFG” with quantity 1; preserve the source's limited detail. |
| 22 | Roselle — Hollow Metal Doors and Frames (`84434554b3aa`) | 10 | No named hardware component sets. |
| 23 | Roselle — Flush Wood Doors (`1d0bc6720be0`) | 9 | No named hardware component sets. |
| 24 | Roselle — Access Doors and Frames (`f38740b00936`) | 4 | No named hardware component sets. |
| 25 | Roselle — Door Hardware IFB REVISED (`62d5f470fef7`) | 17 | **15–17**. 33 set cells, 196 component rows. Ruled table with merged set-description cells. Columns: SET / HARDWARE TYPE / MANUFACTURER - PRODUCT / QTY. / FINISH / NOTES. Plain 1.1–8.3 identifiers have no “Set #” prefix. `--` quantity means null. |
| 26 | SAT TDP — Project Manual (`2cea3f596788`) | 3,930 | **715–836**. 176 textual group headers, including 001, 005, decimal variants, 101AC, and XCY746. Schedule begins on **715**, not 716. Long operational notes, electrical icons, and groups spread across pages. Other `Group 1` hits in the manual refer to steel fasteners. |
| 27 | Shubie Center — IFT specifications (`39ac6b9aa3f0`) | 201 | **174–175**. Three groups 01–03. QTY/unit/description/catalog/finish/manufacturer; A and AA are finish values in column context. Operational prose follows components. |
| 28 | SJC Be-Well — 85% design update (`da4bfb69de1f`) | 2,320 | **711–748**. Bare `HW 01`, `HW 02A`, `HW E17` headers. Revision strikeouts, renumbered aliases, “Moved to” notices, repeated IDs and explicitly unused groups. **123 textual heading occurrences are not 123 active sets.** Quantity includes As Req.; finish/manufacturer columns are explicit. |
| 29 | StarHardware — Commons Lane Division 8 (`049838ae0b69`) | 113 | **53–113**. 69 printed group-header regions, 71 named identifiers when B1/B2 and 103/104 aliases are expanded. Variants Group/Set, Groups/Set, Group/Sets, Groups/Sets and Set/Group. Group 22 on 95 says “set not utilized at this time.” Watermarks intrude into text order; `__` quantities stay null. |
| 30 | The Door Company — Vantage TX-22 (`7298cd3404d7`) | 470 | **389–421**. 44 headers, including alphanumeric C200C and CY201CZ, plus empty 001/002 headings. `PART n - HARDWARE GROUP NO.` prefixes. **C200C starts on 395 and its component list is on 396**, a page missed by header-only search. |
| 31 | USI — Radnet Building specifications (`31ebc3415b76`) | 1,460 | **563**. Set 1.0 with ten components, in **08 4126 All-Glass Entrances**, not 08 7100. Same-page manufacturer legend includes GS, PE, RU, RO. Missing finish cells must not shift the last manufacturer into finish. |
| 32 | Valor Acres — Hollow Metal Doors and Frames (`a25409f1ddb0`) | 10 | No named hardware component sets. |
| 33 | Valor Acres — Wood Doors (`34a8b18cf9a0`) | 9 | No named hardware component sets. |
| 34 | Valor Acres — Access Doors and Frames (`7b8be439d00d`) | 4 | No named hardware component sets. |
| 35 | Valor Acres — Aluminum-Framed Entrances and Storefronts (`c43f368dce3b`) | 13 | No named hardware component sets. Product and fabrication requirements only. |
| 36 | Valor Acres — All-Glass Entrances (`d8f7570bb06c`) | 7 | No named component sets. “Push-Pull Set” and generic door-hardware references on 6 are product prose, unlike the actual named USI set. |
| 37 | Valor Acres — Residential Windows and Doors (`0581dbc3d6a1`) | 11 | No named hardware component sets. |
| 38 | Valor Acres — Door Hardware Rev_2 (`ce8c8241c01d`) | 18 | **7–18**. 37 groups: 01–20, 21A/21B, 22–36. Only quantity/unit/description/finish are generally supplied; do not fabricate catalog or manufacturer columns. Group 03 starts at the bottom of 7 and continues on 8; group 08 spans 8–9. |
| 39 | Valor Acres — Glazing (`503645da7b4e`) | 14 | No named hardware component sets. |
| 40 | Valor Acres — Mirrors (`7e79395147b0`) | 7 | No named hardware component sets. |
| 41 | Valor Acres — Decorative Window Films (`a3a0358f6551`) | 4 | No named hardware component sets. |
| 42 | Village of Oswego — Specifications Volume 1 (`29a780adbd92`) | 584 | **418–445**. 39 group headers, selected numbers from 02 through 57. Missing numbers are absent, not implicitly Not Used. Wrapped descriptions/catalogs, specification references in catalog cells, missing quantities on seals, and NOTE pseudo-rows. |
| 43 | Woodridge — New Public Works Facility specifications (`39d68ae56380`) | 1,546 | **No embedded named hardware schedule found**. Section 08 71 00 occupies **631–647**, ending with protection/end-of-section; 648 is blank and glazing starts on 649. It requests a submitted hardware schedule but supplies no named component groups. The document's 195 text-poor pages must not alone be classified as missing sets. |

## Findings that change the extraction design

**Column meaning is contextual.** Livelle's rightmost column contains MK/SA/RO/NO/PE while the adjacent column contains US15/689/US26D. Those positions determine the role of PE and NO. Conversely, Roselle explicitly combines a full manufacturer and product in one cell; splitting at the first spaced dash preserves further dashes inside the catalog string. JC Ryan has full manufacturer names without a finish column, and Valor largely has finishes without catalog/manufacturer fields. A universal six-column positional rule is wrong for this corpus.

**Header detection needs evidence beyond a keyword.** `Group 1` is common steel-fastener prose. Hospital's door index names sets without listing their components. Roselle's table uses bare decimal numbers, SJC uses `HW`, Bridgeport uses `Heading`, and Star contains slash variants and aliases. All are actual schedule patterns, but they require different structural cues.

**A blank quantity is information.** Star's `__`, Roselle's `--`, SJC's “As Req.”, and unnumbered seal rows must not become quantity 1. Units such as EA, PR and SET are not quantities. Blank finishes are also common and must not cause the manufacturer column to shift left.

**Continuation has to survive headerless pages.** Forest Park's only set crosses pages 262–263. Vantage C200C has its header on 395 and the components on 396. Valor 03 and 08 have a heading at the foot of one page and components on the next. Catalog strings and operational notes can continue independently of component rows.

**Repeated numbers do not prove duplicate data.** Morris contains separate schedule blocks and two MISC groups. SJC and Hospital contain revision material. Gerrard and Bridgeport duplicate whole schedules across separate files. Preserve source locations and revision warnings; do not silently merge by set number alone across the corpus.

**Visual revision evidence matters.** SJC PDF 745 visibly strikes out the old HW 14A, an old active HW E17 and its components, and HW 13, while an unstruck `HW E17 Not Used` and renamed `HW E18` remain. Plain text extraction alone cannot determine the current design. Strikeout interpretation should be separately validated; a warning or review requirement is preferable to claiming an active schedule has been definitively resolved.

## Validation boundary and reproducible review

`tests/fixtures/gold_sets.json` contains a small independently transcribed sample: 12 sets and 33 components across three contrasting source families. It is useful for checking field assignment, unused sets, wrapped strings, and missing quantities, but is too small and selected to establish 90% corpus-wide accuracy. The Roselle table parser matched all six component fields for the three transcribed Roselle sets (7.1, 7.2, 8.3; 12 components) during this audit.

A defensible full evaluation should label held-out pages across every layout family, use set-level precision/recall, compare each of the six component fields, measure continuation/location correctness, and report unused/revision subsets separately. Exact duplicate schedules must stay in one split. Keep scanned catalog appendices and genuinely schedule-free PDFs as negative cases. Treat the audit's observed counts as source-discovery checks, not substitutes for component-level gold labels.

Useful source review pages are Lyons **285** (unused sets and explicit columns), Livelle **645** (PE/NO manufacturer context and multiple sets), Roselle **17** (merged table, wrapped products and null quantities), Vantage **395–396** (continuation), Valor **7–9** (sparse schema), and SJC **745** (revision risk). These examples expose real differences in the downloaded corpus and are suitable for an honest demonstration of both strengths and review needs.
