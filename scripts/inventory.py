"""Create a full, page-addressable corpus inventory (local research utility)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

HEADER = re.compile(r"(?:hardware\s+(?:set|group)|(?:hw|hdw)\.?\s*(?:set|group)|\bset\s*(?:no\.?|number|#|:)\s*\w|^\s*(?:set|group)\s+\d)", re.I | re.M)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/audit"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for number, path in enumerate(sorted(args.source.rglob("*.pdf")), 1):
        rel = path.relative_to(args.source).as_posix()
        key = hashlib.sha256(rel.encode()).hexdigest()[:12]
        folder = args.output / key
        folder.mkdir(exist_ok=True)
        pages, candidates, text_poor = [], [], []
        with pymupdf.open(path) as doc:
            for index, page in enumerate(doc):
                text = page.get_text("text", sort=True)
                hits = [line.strip() for line in text.splitlines() if HEADER.search(line)]
                if hits:
                    candidates.append(index + 1)
                if len(text.strip()) < 60:
                    text_poor.append(index + 1)
                pages.append({"page": index + 1, "width": page.rect.width, "height": page.rect.height,
                              "characters": len(text), "headers": hits, "text": text})
        (folder / "pages.json").write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        selected = set(candidates)
        for p in candidates:
            selected.update(n for n in range(p - 1, p + 3) if 1 <= n <= len(pages))
        (folder / "candidate_pages.txt").write_text("\n\n".join(f"===== PDF PAGE {p['page']} =====\n{p['text']}" for p in pages if p["page"] in selected), encoding="utf-8")
        row = {"id": key, "path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "page_count": len(pages),
               "candidate_pages": candidates, "text_poor_pages": text_poor,
               "header_examples": [h for p in pages for h in p["headers"]][:20]}
        manifest.append(row)
        print(f"{number:02}: {rel}: {len(pages)} pages, {len(candidates)} candidate, {len(text_poor)} text-poor", flush=True)
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Inventoried {len(manifest)} PDFs / {sum(x['page_count'] for x in manifest)} pages.")


if __name__ == "__main__":
    main()
