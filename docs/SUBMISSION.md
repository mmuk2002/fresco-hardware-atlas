# Submission checklist

## Deliverables

- Repository: https://github.com/mmuk2002/fresco-hardware-atlas (or `output/submission/fresco-hardware-atlas-repository.zip`).
- Local deployment: follow the setup and run commands in the root `README.md`.
- Demo: attach `output/demo/hardware-atlas-demo.mp4` directly to your email.
- Validation evidence: `docs/VALIDATION.md`, `docs/CORPUS_AUDIT.md`, and `docs/validation/`.

## Before sending

1. Include the repository URL above in your email.
2. Attach the demo MP4 to the same email.
3. Confirm the repository is accessible in a clean environment with:

   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -e ".[dev]"
   .venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=tmp/pytest-submission
   .venv\Scripts\python.exe -m hardware_sets serve --port 8000
   ```

4. The attached walkthrough shows three different spec pages, a missing quantity, a correction, and source-linked results.

The source PDFs, generated corpus output, runtime database, and temporary files are intentionally ignored by Git. The corpus report captures the supplied-PDF run without redistributing project documents.
