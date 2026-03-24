"""Public-facing orchestrator class for Coding Task Document parsing."""

from typing import Literal
from .models import ParseResult, SubPhase
from . import (
    source_detector,
    termination,
    json_parser,
    history_collector,
    content_extractor
)


class CodingTaskDocumentParser:
    """
    Pure Python parsing library for Coding Task Documents.
    All methods are static. Never raises exceptions.
    """

    @staticmethod
    def parse(text: str) -> ParseResult:
        """
        Main entry point. Auto-detects format and delegates to appropriate parser.
        
        Route logic:
          1. detect_source_type(text)
          2. If "json" → json_parser.parse_engineer_json()
          3. If "engineer" → termination extraction (single sub-phase)
          4. If "architect" → termination extraction (full doc)
        
        Never raises. All errors captured in parse_warnings.
        
        Args:
            text: Document text (Markdown or JSON)
        
        Returns:
            ParseResult with:
              - estimate_n: Total estimate from termination line(s)
              - sub_phases: List if JSON format, else None
              - raw_document: Text without termination line
              - source_type: "architect" or "engineer"
              - parse_warnings: List of non-fatal warnings
        """
        warnings = []
        
        try:
            # Empty input guard
            if not text or not text.strip():
                return ParseResult(
                    estimate_n=0,
                    sub_phases=None,
                    raw_document="",
                    source_type="architect",
                    parse_warnings=["Empty input text"]
                )
            
            # Detect format
            source_type_raw = source_detector.detect_source_type(text)
            
            # Route: JSON aggregation
            if source_type_raw == "json":
                sub_phases, total_estimate, json_warnings = json_parser.parse_engineer_json(text)
                warnings.extend(json_warnings)
                return ParseResult(
                    estimate_n=total_estimate,
                    sub_phases=sub_phases if sub_phases else None,
                    raw_document=text,  # JSON doesn't have termination stripping
                    source_type="engineer",
                    parse_warnings=warnings
                )
            
            # Route: Markdown (architect or engineer single sub-phase)
            estimate_n, term_warnings = termination.extract_last_estimate(text)
            warnings.extend(term_warnings)
            raw_document = termination.strip_termination_line(text)
            
            source_type: Literal["architect", "engineer"] = (
                "engineer" if source_type_raw == "engineer" else "architect"
            )
            
            return ParseResult(
                estimate_n=estimate_n,
                sub_phases=None,
                raw_document=raw_document,
                source_type=source_type,
                parse_warnings=warnings
            )
        
        except Exception as e:
            # Catch-all safety net (should never trigger)
            return ParseResult(
                estimate_n=0,
                sub_phases=None,
                raw_document=text if isinstance(text, str) else "",
                source_type="architect",
                parse_warnings=[f"Unexpected error: {str(e)}"]
            )

    @staticmethod
    def extract_from_group_final_content(content: dict) -> str:
        """
        Extract document text from GroupActor FINAL content dict.
        Delegates to content_extractor module.
        
        Args:
            content: GroupActor FINAL content dict
        
        Returns:
            Document text string (JSON or Markdown) or empty string
        """
        try:
            return content_extractor.extract_from_group_final_content(content)
        except Exception:
            return ""

    @staticmethod
    def collect_sub_phases_from_history(
        history: list[dict]
    ) -> list[SubPhase] | None:
        """
        Scan history list to reconstruct sub-phase documents.
        Delegates to history_collector module.
        
        Args:
            history: List of conversation turn dicts
        
        Returns:
            List of SubPhase instances, or None if no valid sub-phases found
        """
        try:
            return history_collector.collect_sub_phases_from_history(history)
        except Exception:
            return None

    @staticmethod
    def parse_estimate_count(text: str) -> int:
        """
        Lightweight entry point: extract estimate_n only.
        
        For JSON format, returns sum of sub-phase estimates.
        For Markdown, returns value from termination line.
        
        Args:
            text: Document text
        
        Returns:
            Estimate N integer (0 if parse fails)
        """
        try:
            # Use full parse to handle JSON properly
            result = CodingTaskDocumentParser.parse(text)
            return result.estimate_n
        except Exception:
            return 0