"""Base parser interface for PDF extraction backends.

Defines the abstract interface that all extraction backends (Docling, MinerU, etc.)
must implement. The ExtractionResult dataclass is the normalized output format
consumed by the ingest pipeline.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    markdown: str                         # full markdown text — central complete representation (§18 D20)
    structured_json: dict                 # normalized structured output from parser
    equations: list[dict] = field(default_factory=list)   # extracted equations with source coords
    sections: list[dict] = field(default_factory=list)    # section hierarchy with content
    tables: list[dict] = field(default_factory=list)      # extracted tables
    metadata: dict = field(default_factory=dict)          # extraction metadata (backend, version, timing)

    def to_dict(self) -> dict:
        return {
            "markdown": self.markdown,
            "structured_json": self.structured_json,
            "equations": self.equations,
            "sections": self.sections,
            "tables": self.tables,
            "metadata": self.metadata,
        }


class BaseParser(ABC):
    """Abstract base for PDF extraction backends."""

    @property
    @abstractmethod
    def backend_name(self) -> str: ...

    @abstractmethod
    def parse(self, pdf_path: str, keep_debug: bool = False) -> ExtractionResult:
        """Parse a PDF and return normalized extraction result.
        Args:
            pdf_path: absolute path to PDF file
            keep_debug: if True, save raw parser debug output to logs/debug/
        Returns:
            ExtractionResult with markdown, structured_json, equations, sections, tables
        """
        ...
