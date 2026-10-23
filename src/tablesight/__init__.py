"""TableSight: tables and figures from PDFs, as RAG ready chunks."""

from .extract import extract_pdf, write_jsonl
from .schema import Chunk

__version__ = "0.1.0"
__author__ = "Kavya Tolety"
__all__ = ["Chunk", "extract_pdf", "write_jsonl", "__version__"]
