"""
coding_task_document_parser

Pure Python parsing library for Coding Task Documents.
Zero external dependencies (stdlib only).
"""

from .models import ParseResult, SubPhase
from .parser import CodingTaskDocumentParser

__version__ = "1.0.0"

__all__ = [
    "CodingTaskDocumentParser",
    "ParseResult",
    "SubPhase",
]