"""Generate the scanned (image-only) fixture PDF used by the OCR tests.

Each page of a source document is rendered to an image and embedded as
a full-page picture with no text layer, which is exactly what a scanner
produces. Page 1 holds the same known table as the main fixture, so the
OCR tests can check the recovered rows against known values. Page 2
holds a plain paragraph, which should come back as one text chunk.
Run with: python scripts/make_scanned_fixture.py
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "scanned_sample.pdf"

ROWS = [
    ["Product", "Quarter", "Revenue"],
    ["Alpha", "Q1", "120"],
    ["Beta", "Q2", "245"],
    ["Gamma", "Q3", "310"],
]

COL_X = [72, 228, 384, 540]
ROW_Y = [150, 180, 210, 240, 270]

PARAGRAPH_LINES = [
    "Scanned documents arrive as pictures of pages. There is no text",
    "layer to select or copy, so ordinary extraction finds nothing at",
    "all on a page like this one. Optical character recognition reads",
    "the picture and gives the words back, one page at a time.",
]
PARAGRAPH = " ".join(PARAGRAPH_LINES)


def _source_doc() -> "pymupdf.Document":
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 90), "Scanned Fixture Document", fontsize=16, fontname="hebo")
    page.insert_text((72, 138), "Table 1: Quarterly revenue by product.", fontsize=11, fontname="helv")
    shape = page.new_shape()
    for y in ROW_Y:
        shape.draw_line(pymupdf.Point(COL_X[0], y), pymupdf.Point(COL_X[-1], y))
    for x in COL_X:
        shape.draw_line(pymupdf.Point(x, ROW_Y[0]), pymupdf.Point(x, ROW_Y[-1]))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()
    for r, row in enumerate(ROWS):
        for c, value in enumerate(row):
            page.insert_text((COL_X[c] + 10, ROW_Y[r] + 20), value, fontsize=11, fontname="helv")

    page2 = doc.new_page(width=612, height=792)
    for i, line in enumerate(PARAGRAPH_LINES):
        page2.insert_text((72, 110 + i * 18), line, fontsize=12, fontname="helv")
    return doc


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    source = _source_doc()
    scanned = pymupdf.open()
    for page in source:
        pix = page.get_pixmap(dpi=200)
        new_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=pix.tobytes("jpeg", jpg_quality=85))
    scanned.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
