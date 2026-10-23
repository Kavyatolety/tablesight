# Before and after: one table page

Source: `ragas-2023.pdf`, page 5, Table 1 (agreement with human annotators).
This is a real table from a published research paper, extracted on 2026-10-22
with TableSight v0.1. Nothing below is edited by hand.

## Before: naive text extraction

What a plain `page.get_text("text")` call on the table region produces.
Each value lands on its own line, the header for the first column is
missing, and no value is tied to its row or column. A retriever chunking
this text has no way to know that 0.95 is the Ragas score for faithfulness.

```text
Faith.
Ans. Rel.
Cont. Rel.
Ragas
0.95
0.78
0.70
GPT Score
0.72
0.52
0.63
GPT Ranking
0.54
0.40
0.52
```

## After: the TableSight chunk for the same table

The same region as one structured chunk. Rows and columns are preserved,
each value sits in its cell, and the caption found below the table is
linked to the chunk.

Markdown rendering (`content_markdown`):

```markdown
Table 1: Agreement with human annotators in pairwise comparisons of faithfulness, answer relevance and con- text relevance, using the WikEval dataset (accuracy).

|  | Faith. | Ans. Rel. | Cont. Rel. |
| --- | --- | --- | --- |
| Ragas | 0.95 | 0.78 | 0.70 |
| GPT Score | 0.72 | 0.52 | 0.63 |
| GPT Ranking | 0.54 | 0.40 | 0.52 |
```

Structured rows (`rows`):

```json
[
  [
    "",
    "Faith.",
    "Ans. Rel.",
    "Cont. Rel."
  ],
  [
    "Ragas",
    "0.95",
    "0.78",
    "0.70"
  ],
  [
    "GPT Score",
    "0.72",
    "0.52",
    "0.63"
  ],
  [
    "GPT Ranking",
    "0.54",
    "0.40",
    "0.52"
  ]
]
```

Full JSONL record:

```json
{
  "source_file": "ragas-2023.pdf",
  "page": 5,
  "type": "table",
  "content_markdown": "Table 1: Agreement with human annotators in pairwise comparisons of faithfulness, answer relevance and con- text relevance, using the WikEval dataset (accuracy).\n\n|  | Faith. | Ans. Rel. | Cont. Rel. |\n| --- | --- | --- | --- |\n| Ragas | 0.95 | 0.78 | 0.70 |\n| GPT Score | 0.72 | 0.52 | 0.63 |\n| GPT Ranking | 0.54 | 0.40 | 0.52 |",
  "rows": [
    [
      "",
      "Faith.",
      "Ans. Rel.",
      "Cont. Rel."
    ],
    [
      "Ragas",
      "0.95",
      "0.78",
      "0.70"
    ],
    [
      "GPT Score",
      "0.72",
      "0.52",
      "0.63"
    ],
    [
      "GPT Ranking",
      "0.54",
      "0.40",
      "0.52"
    ]
  ],
  "caption": "Table 1: Agreement with human annotators in pairwise comparisons of faithfulness, answer relevance and con- text relevance, using the WikEval dataset (accuracy).",
  "source_text_span": "Faith. Ans. Rel. Cont. Rel. Ragas 0.95 0.78 0.70 GPT Score 0.72 0.52 0.63 GPT Ranking 0.54 0.40 0.52",
  "bbox": [
    76.84,
    76.88,
    283.42,
    133.14
  ]
}
```

## What changed

- Before, the table was a flat list of fragments. After, it is four rows
  with a header, and a question about Ragas faithfulness agreement can be
  answered from the row directly: Ragas, 0.95.
- The caption, which naive extraction leaves as loose text elsewhere on
  the page, is attached to the chunk it describes.
- Page provenance is explicit (source file, page 5), so a RAG pipeline
  can cite the table it retrieved.
