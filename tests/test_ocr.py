"""Tests for the OCR fallback on a scanned, image-only fixture.

The scanned fixture renders the known fixture content to images and
embeds them with no text layer, like a real scanner output. OCR output
can vary slightly across platforms, so the table assertions are
token-based rather than exact cell equality; the born-digital fixture
tests already cover exact extraction.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("rapidocr_onnxruntime", reason="OCR extra not installed")

from tablesight import extract_pdf
from tablesight.cli import main as cli_main
import tablesight.ocr as ocr_module

SCANNED = Path(__file__).parent / "fixtures" / "scanned_sample.pdf"

EXPECTED_TOKENS = [
    "Product", "Quarter", "Revenue",
    "Alpha", "Q1", "120",
    "Beta", "Q2", "245",
    "Gamma", "Q3", "310",
]


@pytest.fixture(scope="module")
def chunks():
    assert SCANNED.is_file(), "Scanned fixture missing. Run scripts/make_scanned_fixture.py"
    return extract_pdf(SCANNED, ocr=True)


def test_scanned_table_recovered_by_ocr(chunks):
    tables = [c for c in chunks if c.type == "table" and c.page == 1]
    assert len(tables) == 1, f"Expected 1 OCR table on page 1, got {len(tables)}"
    table = tables[0]
    assert table.rows is not None and len(table.rows) == 4
    flat = " ".join(cell for row in table.rows for cell in row)
    for token in EXPECTED_TOKENS:
        assert token in flat, f"Missing token {token!r} in OCR rows: {flat!r}"
    alpha_row = next(row for row in table.rows if any("Alpha" in cell for cell in row))
    assert any("120" in cell for cell in alpha_row)
    assert table.caption is not None and "Quarterly revenue" in table.caption
    assert "| Product |" in table.content_markdown


def test_scanned_paragraph_becomes_text_chunk(chunks):
    texts = [c for c in chunks if c.type == "text" and c.page == 2]
    assert len(texts) == 1, f"Expected 1 text chunk on page 2, got {len(texts)}"
    assert "Scanned documents arrive" in texts[0].content_markdown
    assert "Optical character recognition" in texts[0].content_markdown
    assert texts[0].rows is None


def test_scanned_pages_are_not_reported_as_figures(chunks):
    figures = [c for c in chunks if c.type == "figure"]
    assert figures == [], "The page scan itself must not become a figure chunk"


def test_without_ocr_scanned_pages_yield_no_table_or_text():
    plain = extract_pdf(SCANNED)
    assert [c for c in plain if c.type in ("table", "text")] == []


def test_ocr_without_extra_raises_install_hint(monkeypatch):
    monkeypatch.setattr(ocr_module, "_engine", None)
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", None)
    with pytest.raises(ImportError, match=r"tablesight\[ocr\]"):
        extract_pdf(SCANNED, ocr=True)


def test_cli_ocr_flag(tmp_path):
    out = tmp_path / "chunks.jsonl"
    code = cli_main(["extract", str(SCANNED), "--out", str(out), "--ocr"])
    assert code == 0
    records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    types = sorted({record["type"] for record in records})
    assert "table" in types and "text" in types
