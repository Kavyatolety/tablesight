"""Command line interface for TableSight."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .extract import extract_pdf, write_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tablesight",
        description="Extract tables and figures from a PDF as structured chunks for RAG.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_parser = subparsers.add_parser(
        "extract", help="Extract tables and figures from a PDF to JSONL."
    )
    extract_parser.add_argument("pdf", help="Path to the input PDF file.")
    extract_parser.add_argument(
        "--out",
        required=True,
        help="Path to the output JSONL file, for example chunks.jsonl.",
    )
    extract_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Also print a short summary of each chunk to stdout.",
    )
    extract_parser.add_argument(
        "--ocr",
        action="store_true",
        help="Run OCR on scanned, image-only pages (needs: pip install tablesight[ocr]).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "extract":
        pdf_path = Path(args.pdf)
        if not pdf_path.is_file():
            print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
            return 2
        try:
            chunks = extract_pdf(pdf_path, ocr=args.ocr)
        except ImportError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        count = write_jsonl(chunks, args.out)
        tables = sum(1 for c in chunks if c.type == "table")
        figures = sum(1 for c in chunks if c.type == "figure")
        texts = sum(1 for c in chunks if c.type == "text")
        print(
            f"Wrote {count} chunks ({tables} tables, {figures} figures, "
            f"{texts} text) from {pdf_path.name} to {args.out}"
        )
        if args.pretty:
            for chunk in chunks:
                preview = {
                    "source_file": chunk.source_file,
                    "page": chunk.page,
                    "type": chunk.type,
                    "caption": chunk.caption,
                    "rows": len(chunk.rows) if chunk.rows else None,
                }
                print(json.dumps(preview, ensure_ascii=False))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
