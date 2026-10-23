# TableSight

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

TableSight v0.1 focuses on born-digital PDFs. See the roadmap for scanned page support.

## Install

```bash
pip install -e .
```

TableSight depends on PyMuPDF, the same PDF engine used in the research system it grew out of. That choice keeps the dependency list to one library.

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

## Output schema

Each line of the JSONL output is one chunk:

| Field | Type | Meaning |
| --- | --- | --- |
| `source_file` | string | Base name of the source PDF |
| `page` | int | 1-based page number |
| `type` | string | `table` or `figure` |
| `content_markdown` | string | Markdown rendering. A Markdown table for tables, caption plus image metadata for figures |
| `rows` | array or null | For tables, a list of rows, each a list of cell strings. Null for figures |
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

## Demo

See `examples/` for real output on research papers, including a before and after comparison for one table page: what naive text extraction produces on that page, side by side with the structured TableSight chunk for the same table.

Regenerate the demo outputs with the commands listed in `examples/README.md`.

## Tests

```bash
pip install -e ".[dev]"
python scripts/make_fixture.py
pytest
```

The test fixture is a small generated PDF with a known table and a known figure. The tests assert that the extracted rows and cells match exactly, that captions are linked, and that the CLI writes valid JSONL end to end.

## Roadmap

- Scanned page OCR support, so image-only pages are handled instead of skipped.
- Better figure caption linking, including multi-line captions and captions placed above a figure.
- Table header detection and merged cell handling.
- LangChain and LlamaIndex loader wrappers, so TableSight chunks drop into those pipelines directly.
- Optional output of extracted figure images to disk.

## Limitations in v0.1

- Table detection works best on tables with ruled lines or a clear grid layout. Borderless tables with irregular spacing may be missed or split.
- Figures are reported with caption and image metadata. The image bytes are not written out in v0.1.
- Scanned, image-only pages produce no chunks in v0.1. OCR is on the roadmap.

## License

MIT. See `LICENSE`.

## Author

Kavya Tolety, AI/ML Software Engineer, Arlington, VA.
GitHub: https://github.com/Kavyatolety
