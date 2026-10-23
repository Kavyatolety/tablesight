"""Regenerate the demo outputs in examples/ from the corpus papers.

The corpus PDFs themselves are not shipped with this repo. This script
documents exactly how the committed example JSONL files were produced
and can be rerun by anyone who has the same papers locally. Pass PDF
paths as arguments, or run with no arguments to write the before and
after file for the bundled fixture only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "src"))

from tablesight import extract_pdf, write_jsonl  # noqa: E402


def main(argv: list[str]) -> int:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    for name in argv:
        pdf = Path(name)
        chunks = extract_pdf(pdf)
        out = EXAMPLES / f"{pdf.stem}.chunks.jsonl"
        write_jsonl(chunks, out)
        tables = sum(1 for c in chunks if c.type == "table")
        figures = sum(1 for c in chunks if c.type == "figure")
        print(f"{pdf.name}: {len(chunks)} chunks ({tables} tables, {figures} figures) to {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
