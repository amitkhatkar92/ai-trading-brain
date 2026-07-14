"""iios/investment/decision/evidence/evidence_provider.py
BaseEvidenceProvider — pluggable ABC every evidence provider must implement.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_item import EvidenceItem


class BaseEvidenceProvider(ABC):
    """
    Abstract base for all evidence providers.

    Providers:
    - Accept an intelligence payload (dict from an upstream engine)
    - Extract and normalise relevant data into EvidenceItems
    - Return a list of items
    - Must NOT perform analysis or scoring of investment opportunities

    The payload is always optional — if None, the provider returns [].
    This ensures the engine can run even when a source is unavailable.
    """

    @property
    @abstractmethod
    def source_type(self) -> EvidenceSourceType: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def is_required(self) -> bool:
        return self.source_type.is_required

    @abstractmethod
    def collect(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payload:      Optional[Dict[str, Any]] = None,
    ) -> List[EvidenceItem]:
        """
        Extract EvidenceItems from the given intelligence payload.
        Always returns a list (empty if payload is None or unusable).
        Must be deterministic for the same payload.
        """

    def health_check(self) -> bool:
        """Override to add provider-specific health checks."""
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "source_type":   self.source_type.value,
            "version":       self.version,
            "is_required":   self.is_required,
        }
