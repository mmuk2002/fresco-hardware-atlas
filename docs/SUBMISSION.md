# Submission checklist

## Deliverables

- Repository: submit this repository or `output/submission/fresco-hardware-atlas-repository.zip`.
- Local deployment: follow the setup and run commands in the root `README.md`.
- Demo: upload `output/demo/hardware-atlas-demo.mp4` to Loom (or submit the MP4 directly if accepted).
- Validation evidence: `docs/VALIDATION.md`, `docs/CORPUS_AUDIT.md`, and `docs/validation/`.

## Before sending

1. Replace the repository URL in the application form with the final GitHub URL.
2. Upload the demo MP4 and paste its share link into the application form.
3. Confirm the repository is accessible in a clean environment with:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev,ocr]"
   python -m pytest -q --basetemp=tmp/pytest-submission
   hardware-sets serve
   ```

4. In the live walkthrough, show one section-style page, one table-style page, a missing quantity, a manufacturer/finish ambiguity, a correction, and both exports.

The source PDFs, generated corpus output, runtime database, and temporary files are intentionally ignored by Git. The corpus report captures the supplied-PDF run without redistributing project documents.
