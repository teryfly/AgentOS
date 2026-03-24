"""Data models for Coding Task Document parsing."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ParseResult:
    """Result of parsing a Coding Task Document."""
    
    estimate_n: int                                   # Total estimate (files + shell steps)
    sub_phases: list['SubPhase'] | None              # None for architect, list for engineer JSON
    raw_document: str                                 # Document text without termination line
    source_type: Literal["architect", "engineer"]    # Auto-detected source
    parse_warnings: list[str]                        # Non-fatal warnings


@dataclass
class SubPhase:
    """Engineer sub-phase document metadata."""
    
    phase: str          # "1.1", "2.3"
    title: str          # Sub-phase title from heading
    document: str       # Full sub-phase Markdown (includes termination line)
    estimate_n: int     # Per-phase estimate