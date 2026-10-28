# TableSight

[![Tests](https://github.com/Kavyatolety/tablesight/actions/workflows/tests.yml/badge.svg)](https://github.com/Kavyatolety/tablesight/actions/workflows/tests.yml)

Extract tables and figures from PDFs as clean, structured chunks that any RAG pipeline can ingest.

By [Kavya Tolety](https://github.com/Kavyatolety)

## The problem

Text-only RAG goes blind on real documents.

A typical ingestion step reads a PDF as a flat stream of text. Tables lose their rows and columns in that stream, figures become invisible or arrive as a stray caption with no link to the image, and scanned pages may produce no text at all. The question that depends on a table is then unanswerable from the retrieved chunks, even when the answer is sitting in the document. In practice this shows up as a model abstaining on, or guessing at, a question whose evidence is in a table it never really saw.

TableSight is the fix, packaged as a small library: pull the tables and figures out first, preserve their structure, and hand your retriever chunks it can actually use.

This project grew out of research on multimodal RAG, where a fresh document system was built and evaluated on table, figure, and scanned page questions, and where generation-stage table blindness was a concrete failure mode: an answerable table question that the system abstained on because the table evidence was not usable.

## What it does

- Extracts tables with their row and cell structure intact.
- Extracts embedded figures and links a nearby figure caption where one is present.
- Emits one JSONL record per table or figure, with page provenance.
- Renders each table as Markdown, so it can be embedded and searched as text while the structured rows stay available for exact lookup.
- Optional OCR fallback for scanned, image-only pages (v0.2): tables are rebuilt from OCR text box positions, and a scanned page that holds no table still yields a text chunk instead of being dropped.

## Install

```bash
pip install -e .
```

TableSight depends on PyMuPDF, the same PDF engine used in the research system it grew out of. That choice keeps the base dependency list to one library. For scanned page support, install the OCR extra:

```bash
pip install -e ".[ocr]"
```

## Quickstart

Command line:

```bash
tablesight extract paper.pdf --out chunks.jsonl
```

Python:

```python
from tablesight import extract_pdf, write_jsonl

chunks = extract_pdf("paper.pdf")
write_jsonl(chunks, "chunks.jsonl")

for chunk in chunks:
    print(chunk.page, chunk.type, chunk.caption)
```

## Scanned pages (OCR)

Born-digital pages carry a text layer. Scanned pages are pictures, so there is nothing to extract and v0.1 skipped them. With the OCR extra installed, pass the flag and TableSight routes any page that has no usable text layer and no detected table through RapidOCR, the same engine the research system used:

```bash
tablesight extract scanned.pdf --out chunks.jsonl --ocr
```

```python
chunks = extract_pdf("scanned.pdf", ocr=True)
```

OCR returns text boxes with positions. If the boxes on a page line up as a grid, the chunk is a table with rows rebuilt from box positions, exactly like a born-digital table, and a nearby Table caption is linked. If they do not form a grid, the page yields one chunk of type `text` holding the OCR text in reading order. The scan itself is never reported as a figure. OCR is off by default, so existing behavior is unchanged.

## Output schema

Each line of the JSONL output is one chunk:

| Field | Type | Meaning |
| --- | --- | --- |
| `source_file` | string | Base name of the source PDF |
| `page` | int | 1-based page number |
| `type` | string | `table`, `figure`, or `text` (text only from the OCR fallback) |
| `content_markdown` | string | Markdown rendering. A Markdown table for tables, caption plus image metadata for figures, the OCR text for text chunks |
| `rows` | array or null | For tables, a list of rows, each a list of cell strings. Null for figures and text chunks |
| `caption` | string or null | Caption text found near the table or figure, or null |
| `source_text_span` | string or null | Raw text from the chunk region where available |
| `bbox` | array or null | Bounding box in PDF points, `[x0, y0, x1, y1]`, where available |

Example table chunk (rows shortened for readability):

```json
{"source_file": "sample_table.pdf", "page": 1, "type": "table", "content_markdown": "Table 1: Quarterly revenue by product.\n\n| Product | Quarter | Revenue |\n| --- | --- | --- |\n| Alpha | Q1 | 120 |", "rows": [["Product", "Quarter", "Revenue"], ["Alpha", "Q1", "120"]], "caption": "Table 1: Quarterly revenue by product.", "source_text_span": "Product Quarter Revenue Alpha Q1 120", "bbox": [72.0, 150.0, 540.0, 270.0]}
```

## Design choices

- PDF engine: PyMuPDF. The research system this grew out of already used PyMuPDF for ingestion, so TableSight keeps that engine and its one-dependency footprint instead of adding a second PDF library.
- Cell text: table cells are rebuilt from word-level extraction inside each cell rectangle, rather than using the raw cell text order. In typeset PDFs the raw order can scramble a value, while word-level text keeps each word, number, and decimal point intact.
- Captions: a caption is linked only when a block starting with Table, Figure, or Fig. sits close above or below the table or figure and overlaps it horizontally. Otherwise the caption field is null rather than a guess.
- OCR: scanned pages are rendered at 200 DPI and read with RapidOCR, mirroring the research system. Table structure is claimed only when at least three OCR lines place text in the same two or more columns; anything else degrades to a text chunk rather than a guessed table.

## Demo

See `examples/` for real output on research papers, including a before and after comparison for one table page: what naive text extraction produces on that page, side by side with the structured TableSight chunk for the same table.

Regenerate the demo outputs with the commands listed in `examples/README.md`.

## Tests

```bash
pip install -e ".[dev]"
python scripts/make_fixture.py
python scripts/make_scanned_fixture.py
pytest
```

Two fixtures are used: a born-digital PDF with a known table and figure, and a scanned, image-only version of the same table plus a paragraph page. The tests assert exact rows and cells on the born-digital fixture, token-level recovery of the table on the scanned fixture (OCR output varies slightly by platform), the text chunk fallback, and the CLI end to end, with and without OCR.

## Roadmap

- Better figure caption linking, including multi-line captions and captions placed above a figure.
- Table header detection and merged cell handling.
- LangChain and LlamaIndex loader wrappers, so TableSight chunks drop into those pipelines directly.
- Optional output of extracted figure images to disk.

## Limitations in v0.2

- Table detection works best on tables with ruled lines or a clear grid layout. Borderless tables with irregular spacing may be missed or split.
- Figures are reported with caption and image metadata. The image bytes are not written out yet.
- OCR quality is bounded by the scan and the engine: low-resolution or skewed scans can merge lines, drop a space, or misread a character. Scanned tables without a clear column layout come back as text chunks rather than structured rows.

## License

MIT. See `LICENSE`.

## Author

Kavya Tolety, AI/ML Software Engineer, Arlington, VA.
GitHub: https://github.com/Kavyatolety
