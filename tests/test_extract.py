"""Tests for TableSight extraction on a fixture with known content."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tablesight import extract_pdf, write_jsonl
from tablesight.cli import main as cli_main

FIXTURE = Path(__file__).parent / "fixtures" / "sample_table.pdf"

EXPECTED_ROWS = [
    ["Product", "Quarter", "Revenue"],
    ["Alpha", "Q1", "120"],
    ["Beta", "Q2", "245"],
    ["Gamma", "Q3", "310"],
]


@pytest.fixture(scope="module")
def chunks():
    assert FIXTURE.is_file(), "Fixture PDF is missing. Run scripts/make_fixture.py"
    return extract_pdf(FIXTURE)


def test_extracts_known_table_rows_and_cells(chunks):
    tables = [c for c in chunks if c.type == "table"]
    assert len(tables) == 1, f"Expected 1 table, got {len(tables)}"
    table = tables[0]
    assert table.source_file == "sample_table.pdf"
    assert table.page == 1
    assert table.rows == EXPECTED_ROWS


def test_table_markdown_and_caption(chunks):
    table = [c for c in chunks if c.type == "table"][0]
    assert "| Product | Quarter | Revenue |" in table.content_markdown
    assert "| Alpha | Q1 | 120 |" in table.content_markdown
    assert "| Gamma | Q3 | 310 |" in table.content_markdown
    assert table.caption is not None
    assert "Table 1" in table.caption
    assert table.source_text_span is not None
    assert "Alpha" in table.source_text_span


def test_extracts_figure_with_caption(chunks):
    figures = [c for c in chunks if c.type == "figure"]
    assert len(figures) == 1, f"Expected 1 figure, got {len(figures)}"
    figure = figures[0]
    assert figure.page == 1
    assert figure.rows is None
    assert figure.caption is not None
    assert "Figure 1" in figure.caption


def test_jsonl_schema(tmp_path, chunks):
    out = tmp_path / "chunks.jsonl"
    count = write_jsonl(chunks, out)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert count == len(lines)
    for line in lines:
        record = json.loads(line)
        for key in (
            "source_file",
            "page",
            "type",
            "content_markdown",
            "rows",
            "caption",
            "source_text_span",
        ):
            assert key in record
        assert record["type"] in ("table", "figure")


def test_cli_extract_end_to_end(tmp_path):
    out = tmp_path / "out.jsonl"
    code = cli_main(["extract", str(FIXTURE), "--out", str(out)])
    assert code == 0
    assert out.is_file()
    records = [json.loads(line) for line in out.read_text().strip().splitlines()]
    assert any(r["type"] == "table" and r["rows"] == EXPECTED_ROWS for r in records)
