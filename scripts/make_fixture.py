"""Generate the small fixture PDF used by the tests.

The fixture has one known table and one embedded image with a figure
caption, so tests can assert the exact rows, cells, and caption that
TableSight should recover. Run with: python scripts/make_fixture.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pymupdf


def _png_bytes(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    raw = b""
    row = bytes(rgb) * width
    for _ in range(height):
        raw += b"\x00" + row

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_table.pdf"

ROWS = [
    ["Product", "Quarter", "Revenue"],
    ["Alpha", "Q1", "120"],
    ["Beta", "Q2", "245"],
    ["Gamma", "Q3", "310"],
]

COL_X = [72, 228, 384, 540]
ROW_Y = [150, 180, 210, 240, 270]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 90), "TableSight Fixture Document", fontsize=16, fontname="hebo")
    page.insert_text(
        (72, 115),
        "This page holds one table and one figure for testing.",
        fontsize=11,
        fontname="helv",
    )
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
            x = COL_X[c] + 10
            y = ROW_Y[r] + 20
            page.insert_text((x, y), value, fontsize=11, fontname="helv")

    img_bytes = _png_bytes(160, 110, (70, 120, 200))
    img_rect = pymupdf.Rect(72, 330, 232, 440)
    page.insert_image(img_rect, stream=img_bytes)
    page.insert_text(
        (72, 465),
        "Figure 1: A simple chart of quarterly revenue.",
        fontsize=11,
        fontname="helv",
    )
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
