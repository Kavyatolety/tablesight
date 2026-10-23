"""Chunk schema emitted by TableSight.

Every extracted table or figure becomes one Chunk. The fields are kept
flat and JSON friendly so any RAG pipeline can ingest the JSONL output
without a custom parser.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Chunk:
    """One structured chunk for a single table or figure.

    Attributes:
        source_file: Base name of the source PDF, for example paper.pdf.
        page: 1-based page number in the source PDF.
        type: Either table or figure.
        content_markdown: Markdown rendering of the chunk. For a table
            this is a Markdown table built from the extracted rows.
            For a figure this is the caption plus basic image metadata.
        rows: Structured cell data for tables, as a list of rows where
            each row is a list of cell strings. None for figures.
        caption: Caption text linked to the chunk where one was found
            near it on the page. None when no caption was found.
        source_text_span: Raw text recovered from the chunk region
            where available. For a table this is the text inside the
            table bounding box. For a figure this is the caption block.
        bbox: Bounding box in PDF points as [x0, y0, x1, y1], where
            available. Extra provenance beyond the core schema.
    """

    source_file: str
    page: int
    type: str
    content_markdown: str
    rows: Optional[list[list[str]]] = None
    caption: Optional[str] = None
    source_text_span: Optional[str] = None
    bbox: Optional[list[float]] = field(default=None)

    def to_dict(self) -> dict:
        data = asdict(self)
        if data.get("bbox") is not None:
            data["bbox"] = [round(float(v), 2) for v in data["bbox"]]
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
