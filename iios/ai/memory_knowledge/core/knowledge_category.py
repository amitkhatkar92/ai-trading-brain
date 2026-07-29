"""
knowledge_category.py -- iios.ai.memory_knowledge.core
=======================================================
:class:`KnowledgeCategory` — enum classifying knowledge items.
"""
from __future__ import annotations

from enum import Enum


class KnowledgeCategory(str, Enum):
    """Category classification for knowledge items."""
    DOCUMENT   = "document"    # Prose documents, articles, reports
    FACT       = "fact"        # Discrete factual statements
    RESEARCH   = "research"    # Research notes, findings, analyses
    REFERENCE  = "reference"   # External references, citations, URLs
    STRUCTURED = "structured"  # Structured data (tables, JSON records)
    CUSTOM     = "custom"      # User-defined categories
