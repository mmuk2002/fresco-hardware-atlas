# Third-party notices

| Dependency | Role | License |
|---|---|---|
| PyMuPDF / MuPDF | PDF text, geometry, tables, rendering, optional OCR bridge | AGPL-3.0 / commercial licensing |
| Pydantic | Output validation | MIT |
| FastAPI | Local HTTP API | MIT |
| Starlette | ASGI framework underneath FastAPI | BSD-3-Clause |
| Uvicorn | Local server | BSD-3-Clause |
| python-multipart | Upload parsing | Apache-2.0 |
| pytest / HTTPX / Playwright | Development verification | MIT / BSD-3-Clause / Apache-2.0 |
| Tesseract (optional, separately installed) | OCR | Apache-2.0 |

The project deliberately uses PyMuPDF for fast text/geometry access across the supplied 17,637-page corpus. Its licensing is part of the implementation choice, not hidden behind an MIT project label. See the dependency distributions for complete notices and [PyMuPDF licensing](https://pymupdf.readthedocs.io/en/latest/about.html).

Input PDFs, extracted project facts and demo source pages retain their original ownership. The repository does not grant rights to redistribute those documents. The frontend makes no external font or analytics requests.
