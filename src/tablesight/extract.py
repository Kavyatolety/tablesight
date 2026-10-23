"""Table and figure extraction from PDFs.

This module adapts the approach used in Kavya Tolety's multimodal RAG
research system, where ingestion was built on PyMuPDF and recorded
provenance (document, page, modality) for every chunk. TableSight keeps
that engine choice, PyMuPDF, and narrows the focus: instead of general
text chunks, it emits only tables and figures, with structure preserved.

Table detection uses PyMuPDF's find_tables, which looks for ruled lines
and for text arranged in a grid. Figure extraction uses the embedded
image list for each page and links a nearby caption where one is present.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

import pymupdf

from .schema import Chunk

CAPTION_RE = re.compile(
    r"^\s*(Table|Figure|Fig\.)\s*\d+\s*[:.\- ]\s*.+", re.IGNORECASE | re.DOTALL
)
TABLE_CAPTION_RE = re.compile(r"^\s*Table\s*\d+", re.IGNORECASE)
FIGURE_CAPTION_RE = re.compile(r"^\s*(Figure|Fig\.)\s*\d+", re.IGNORECASE)

MIN_FIGURE_WIDTH_PT = 50.0
MIN_FIGURE_HEIGHT_PT = 50.0
CAPTION_SEARCH_PT = 90.0


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def _rows_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]

    def fmt(row: list[str]) -> str:
        cells = [cell.replace("|", "\\|") for cell in row]
        return "| " + " | ".join(cells) + " |"

    lines = [fmt(padded[0])]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    for row in padded[1:]:
        lines.append(fmt(row))
    return "\n".join(lines)


def _text_blocks(page: "pymupdf.Page") -> list[dict]:
    blocks = []
    for item in page.get_text("blocks"):
        x0, y0, x1, y1, text, _block_no, block_type = item[:7]
        if block_type != 0:
            continue
        cleaned = re.sub(r"\s+", " ", text).strip()
        if cleaned:
            blocks.append(
                {"bbox": (float(x0), float(y0), float(x1), float(y1)), "text": cleaned}
            )
    return blocks


def _find_caption(
    blocks: list[dict],
    bbox: tuple[float, float, float, float],
    pattern: re.Pattern,
) -> Optional[str]:
    """Find a caption block close above or below the given bbox."""
    x0, y0, x1, y1 = bbox
    best: Optional[tuple[float, str]] = None
    for block in blocks:
        if not pattern.match(block["text"]):
            continue
        bx0, by0, bx1, by1 = block["bbox"]
        horizontal_overlap = min(x1, bx1) - max(x0, bx0)
        if horizontal_overlap < -20:
            continue
        if by1 <= y0:
            distance = y0 - by1
        elif by0 >= y1:
            distance = by0 - y1
        else:
            distance = 0.0
        if distance <= CAPTION_SEARCH_PT and (best is None or distance < best[0]):
            best = (distance, block["text"])
    return best[1] if best else None


def _cell_text_from_words(
    words: list[tuple], cell_rect: "pymupdf.Rect"
) -> str:
    """Rebuild one cell from page words whose centers fall inside it.

    The built in cell extract can reorder glyphs in typeset PDFs, turning
    for example 0.95 into 095 with the point on another line. Word level
    extraction keeps each word intact, so numbers and names survive.
    Words are grouped by their source line, then joined in reading order.
    """
    lines: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
    for word in words:
        x0, y0, x1, y1, text, block_no, line_no, _word_no = word[:8]
        cx = (float(x0) + float(x1)) / 2.0
        cy = (float(y0) + float(y1)) / 2.0
        if cell_rect.x0 - 1 <= cx <= cell_rect.x1 + 1 and cell_rect.y0 - 1 <= cy <= cell_rect.y1 + 1:
            lines.setdefault((int(block_no), int(line_no)), []).append(
                (float(y0), float(x0), str(text))
            )
    if not lines:
        return ""
    parts = []
    for key in sorted(lines, key=lambda k: min(v[0] for v in lines[k])):
        ordered = [text for _y, _x, text in sorted(lines[key], key=lambda v: v[1])]
        parts.append(" ".join(ordered))
    return _clean_cell(" ".join(parts))


def _extract_rows_word_level(
    page: "pymupdf.Page", table: object
) -> Optional[list[list[str]]]:
    try:
        words = page.get_text("words")
        fallback = table.extract()
    except Exception:
        return None
    rows: list[list[str]] = []
    for row_index, row in enumerate(table.rows):
        cells: list[str] = []
        for col_index, cell in enumerate(row.cells):
            if cell is None:
                cells.append("")
                continue
            text = _cell_text_from_words(words, pymupdf.Rect(cell))
            if not text and fallback and fallback[row_index][col_index]:
                text = _clean_cell(fallback[row_index][col_index])
            cells.append(text)
        rows.append(cells)
    return rows


def extract_tables_from_page(
    page: "pymupdf.Page", source_file: str, blocks: list[dict]
) -> list[Chunk]:
    chunks: list[Chunk] = []
    try:
        finder = page.find_tables()
        tables = list(finder.tables) if finder is not None else []
    except Exception:
        tables = []
    for table in tables:
        rows = _extract_rows_word_level(page, table)
        if rows is None:
            try:
                raw_rows = table.extract()
            except Exception:
                continue
            if not raw_rows:
                continue
            rows = [[_clean_cell(cell) for cell in row] for row in raw_rows]
        rows = [row for row in rows if any(cell for cell in row)]
        if len(rows) < 2 or max(len(row) for row in rows) < 2:
            continue
        bbox = tuple(float(v) for v in table.bbox)
        caption = _find_caption(blocks, bbox, TABLE_CAPTION_RE)
        try:
            span = page.get_text("text", clip=pymupdf.Rect(bbox)).strip()
            span = re.sub(r"\s+", " ", span) or None
        except Exception:
            span = None
        markdown = _rows_to_markdown(rows)
        if caption:
            markdown = caption + "\n\n" + markdown
        chunks.append(
            Chunk(
                source_file=source_file,
                page=page.number + 1,
                type="table",
                content_markdown=markdown,
                rows=rows,
                caption=caption,
                source_text_span=span,
                bbox=list(bbox),
            )
        )
    return chunks


def extract_figures_from_page(
    page: "pymupdf.Page", source_file: str, blocks: list[dict]
) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen_xrefs: set[int] = set()
    for image in page.get_images(full=True):
        xref = int(image[0])
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        rects = []
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            continue
        rect = rects[0]
        bbox = (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
        width_pt = bbox[2] - bbox[0]
        height_pt = bbox[3] - bbox[1]
        if width_pt < MIN_FIGURE_WIDTH_PT or height_pt < MIN_FIGURE_HEIGHT_PT:
            continue
        try:
            info = page.parent.extract_image(xref)
            pixel_size = f"{info.get('width')}x{info.get('height')} px"
            image_format = str(info.get("ext", "")).upper()
        except Exception:
            pixel_size = "unknown size"
            image_format = "unknown format"
        caption = _find_caption(blocks, bbox, FIGURE_CAPTION_RE)
        lines = [f"Figure on page {page.number + 1} of {source_file}."]
        if caption:
            lines.append("")
            lines.append(caption)
        lines.append("")
        lines.append(
            f"[Embedded image: {pixel_size}, {image_format}, "
            f"{width_pt:.0f}x{height_pt:.0f} pt on page]"
        )
        chunks.append(
            Chunk(
                source_file=source_file,
                page=page.number + 1,
                type="figure",
                content_markdown="\n".join(lines),
                rows=None,
                caption=caption,
                source_text_span=caption,
                bbox=list(bbox),
            )
        )
    return chunks


def extract_pdf(path: str | Path) -> list[Chunk]:
    """Extract every table and figure chunk from one PDF."""
    pdf_path = Path(path)
    source_file = pdf_path.name
    chunks: list[Chunk] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            blocks = _text_blocks(page)
            chunks.extend(extract_tables_from_page(page, source_file, blocks))
            chunks.extend(extract_figures_from_page(page, source_file, blocks))
    chunks.sort(key=lambda c: (c.page, 0 if c.type == "table" else 1))
    return chunks


def write_jsonl(chunks: Iterable[Chunk], out_path: str | Path) -> int:
    out = Path(out_path)
    if out.parent and str(out.parent) not in ("", "."):
        out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(chunk.to_json() + "\n")
            count += 1
    return count
