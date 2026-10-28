"""OCR fallback for scanned, image-only pages.

Born-digital pages carry a text layer, so PyMuPDF can find their tables
directly. Scanned pages are just pictures: there is no text layer, no
ruled-line grid to detect, and v0.1 skipped them entirely. This module
adds the fallback Kavya Tolety's multimodal RAG research system used:
render the page, run RapidOCR over the image, and work from the OCR
text boxes, each of which carries its own position on the page.

From those boxes TableSight rebuilds what it can, honestly:

- If the boxes form a grid (several lines whose segments line up in
  the same columns), the chunk is a table, with rows rebuilt from box
  positions and the same Markdown rendering as a born-digital table.
- If they do not form a grid, the page still yields one text chunk
  holding the OCR text in reading order, so a scanned page is never
  silently dropped from the corpus.

OCR is an optional dependency. The base install stays at one
dependency, PyMuPDF; install the extra with: pip install tablesight[ocr]
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median
from typing import Optional

import pymupdf

from .schema import Chunk

OCR_DPI = 200
MIN_PAGE_TEXT_CHARS = 20
MIN_CONFIDENCE = 0.5
COLUMN_GAP_PT = 12.0

INSTALL_HINT = (
    "OCR support needs the optional dependencies. "
    'Install them with: pip install "tablesight[ocr]"'
)

_TABLE_CAPTION_RE = re.compile(r"^\s*Table\s*\d+", re.IGNORECASE)

_engine = None


def _load_engine():
    """Create the shared RapidOCR engine, lazily, with a clear error."""
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise ImportError(INSTALL_HINT) from exc
        _engine = RapidOCR()
    return _engine


@dataclass
class Segment:
    """One OCR text box, converted to PDF points."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    score: float

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def ocr_page_segments(page: "pymupdf.Page") -> list[Segment]:
    """Run OCR on one rendered page and return its text boxes."""
    try:
        import numpy as np
    except ImportError as exc:
        raise ImportError(INSTALL_HINT) from exc
    engine = _load_engine()
    pix = page.get_pixmap(dpi=OCR_DPI)
    zoom = OCR_DPI / 72.0
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    if pix.n == 4:
        img = img[:, :, :3]
    result, _elapsed = engine(img)
    segments: list[Segment] = []
    for item in result or []:
        box, text, score = item[0], str(item[1]).strip(), float(item[2])
        if not text or score < MIN_CONFIDENCE:
            continue
        xs = [float(point[0]) / zoom for point in box]
        ys = [float(point[1]) / zoom for point in box]
        segments.append(
            Segment(
                text=text,
                x0=min(xs),
                y0=min(ys),
                x1=max(xs),
                y1=max(ys),
                score=score,
            )
        )
    segments.sort(key=lambda s: (s.cy, s.x0))
    return segments


def _cluster_lines(segments: list[Segment]) -> list[list[Segment]]:
    """Group segments into visual lines by vertical proximity."""
    if not segments:
        return []
    tolerance = max(6.0, 0.6 * median([s.height for s in segments]))
    lines: list[list[Segment]] = []
    for segment in segments:
        if lines and abs(segment.cy - median([s.cy for s in lines[-1]])) <= tolerance:
            lines[-1].append(segment)
        else:
            lines.append([segment])
    for line in lines:
        line.sort(key=lambda s: s.x0)
    return lines


def _line_text(line: list[Segment]) -> str:
    return " ".join(segment.text for segment in line)


def _grid_rows(
    lines: list[list[Segment]],
) -> Optional[tuple[list[list[str]], int, int]]:
    """Rebuild table rows from lines whose segments share columns.

    Column starts are the clustered left edges of all segments. Every
    line is mapped onto those columns, and the table is the longest
    run of consecutive lines that place segments in at least two
    columns. Lines outside the run (a page title above, a footnote
    below) are not table rows. A grid is claimed only when the run has
    at least three lines, so ordinary paragraphs, whose left edges sit
    in one column, never become tables.

    Returns the rows plus the run's [start, end) line indices.
    """
    starts = sorted(segment.x0 for line in lines for segment in line)
    columns: list[float] = []
    for start in starts:
        if not columns or start - columns[-1] > COLUMN_GAP_PT:
            columns.append(start)
    if len(columns) < 2 or len(lines) < 3:
        return None

    def column_of(segment: Segment) -> int:
        index = 0
        for i, start in enumerate(columns):
            if segment.x0 >= start - COLUMN_GAP_PT:
                index = i
        return index

    mapped: list[list[str]] = []
    gridded: list[bool] = []
    for line in lines:
        cells: dict[int, list[str]] = {}
        for segment in line:
            cells.setdefault(column_of(segment), []).append(segment.text)
        mapped.append([" ".join(cells.get(i, [])) for i in range(len(columns))])
        gridded.append(len(cells) >= 2)

    best_start = best_end = -1
    run_start: Optional[int] = None
    for i, is_gridded in enumerate(gridded + [False]):
        if is_gridded and run_start is None:
            run_start = i
        elif not is_gridded and run_start is not None:
            if best_start < 0 or (i - run_start) > (best_end - best_start):
                best_start, best_end = run_start, i
            run_start = None
    if best_start < 0 or (best_end - best_start) < 3:
        return None
    rows = [row for row in mapped[best_start:best_end] if any(cell for cell in row)]
    if not rows:
        return None
    return rows, best_start, best_end


def _union_bbox(segments: list[Segment]) -> list[float]:
    return [
        min(s.x0 for s in segments),
        min(s.y0 for s in segments),
        max(s.x1 for s in segments),
        max(s.y1 for s in segments),
    ]


def ocr_page_chunks(page: "pymupdf.Page", source_file: str) -> list[Chunk]:
    """Extract chunks from one scanned page via OCR."""
    from .extract import _rows_to_markdown

    segments = ocr_page_segments(page)
    if not segments:
        return []
    lines = _cluster_lines(segments)

    grid = _grid_rows(lines)
    if grid is not None:
        rows, start, end = grid
        table_lines = lines[start:end]
        caption: Optional[str] = None
        if start > 0 and _TABLE_CAPTION_RE.match(_line_text(lines[start - 1])):
            caption = _line_text(lines[start - 1])
        elif end < len(lines) and _TABLE_CAPTION_RE.match(_line_text(lines[end])):
            caption = _line_text(lines[end])
        table_segments = [s for line in table_lines for s in line]
        markdown = _rows_to_markdown(rows)
        if caption:
            markdown = caption + "\n\n" + markdown
        return [
            Chunk(
                source_file=source_file,
                page=page.number + 1,
                type="table",
                content_markdown=markdown,
                rows=rows,
                caption=caption,
                source_text_span=" ".join(
                    _line_text(line) for line in table_lines
                ),
                bbox=_union_bbox(table_segments),
            )
        ]

    text = "\n".join(_line_text(line) for line in lines)
    return [
        Chunk(
            source_file=source_file,
            page=page.number + 1,
            type="text",
            content_markdown=text,
            rows=None,
            caption=None,
            source_text_span=re.sub(r"\s+", " ", text),
            bbox=_union_bbox(segments),
        )
    ]
