# Examples

Demo outputs from TableSight v0.1, run on 2026-10-22 on three research
papers from a multimodal RAG corpus. The source PDFs are published papers
and are not redistributed in this repo. The JSONL files here are the
unmodified output of the commands below.

## Files

- `ragas-2023.chunks.jsonl`: 4 chunks, all tables.
- `attention-2017.chunks.jsonl`: 7 chunks, 4 tables and 3 figures. This is the table-heavy paper in the set, with results tables across pages 6 to 10 and architecture figures.
- `dpr-2020.chunks.jsonl`: 7 chunks, all tables.
- `before-after.md`: one table page (Ragas, page 5, Table 1) shown as naive text extraction and as a TableSight structured chunk, side by side.
- `fixture.chunks.jsonl`: output on the test fixture PDF (1 table, 1 figure), handy as a tiny known-good reference.

Total across the three papers: 18 chunks (15 tables, 3 figures).

## Regenerate

```bash
pip install -e .
tablesight extract /path/to/ragas-2023.pdf --out examples/ragas-2023.chunks.jsonl
tablesight extract /path/to/attention-2017.pdf --out examples/attention-2017.chunks.jsonl
tablesight extract /path/to/dpr-2020.pdf --out examples/dpr-2020.chunks.jsonl
```

Or, with the papers in a local folder:

```bash
python scripts/make_demo.py /path/to/ragas-2023.pdf /path/to/attention-2017.pdf /path/to/dpr-2020.pdf
```

## A note on quality

Extraction quality in v0.1 varies by table layout. Tables with a clear
grid, like the Ragas Table 1 in `before-after.md`, come out clean. Tables
that pack several logical rows into one visual row, or that group
sub-rows under one heading cell, can come out grouped in a single cell.
See the Limitations section of the main README.
