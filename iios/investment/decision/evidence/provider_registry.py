"""iios/investment/decision/evidence/provider_registry.py
ProviderRegistry — thread-safe registry of BaseEvidenceProvider instances.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider


class DuplicateProviderError(Exception): ...
class UnknownProviderError(Exception): ...


class ProviderRegistry:
    """Maps EvidenceSourceType → BaseEvidenceProvider."""

    def __init__(self) -> None:
        self._lock:      threading.RLock = threading.RLock()
        self._providers: Dict[EvidenceSourceType, BaseEvidenceProvider] = {}

    def register(
        self,
        provider:    BaseEvidenceProvider,
        overwrite:   bool = False,
    ) -> None:
        with self._lock:
            key = provider.source_type
            if key in self._providers and not overwrite:
                raise DuplicateProviderError(
                    f"Provider for {key.value!r} already registered. Use overwrite=True."
                )
            self._providers[key] = provider

    def unregister(self, source_type: EvidenceSourceType) -> None:
        with self._lock:
            self._providers.pop(source_type, None)

    def get(self, source_type: EvidenceSourceType) -> BaseEvidenceProvider:
        with self._lock:
            if source_type not in self._providers:
                raise UnknownProviderError(f"No provider registered for {source_type.value!r}.")
            return self._providers[source_type]

    def get_optional(self, source_type: EvidenceSourceType) -> Optional[BaseEvidenceProvider]:
        with self._lock:
            return self._providers.get(source_type)

    def all_providers(self) -> List[BaseEvidenceProvider]:
        with self._lock:
            return list(self._providers.values())

    def registered_types(self) -> List[EvidenceSourceType]:
        with self._lock:
            return list(self._providers.keys())

    def has(self, source_type: EvidenceSourceType) -> bool:
        with self._lock:
            return source_type in self._providers

    def count(self) -> int:
        with self._lock:
            return len(self._providers)

    def required_providers_present(self) -> bool:
        with self._lock:
            return all(
                st in self._providers
                for st in EvidenceSourceType
                if st.is_required
            )

    def missing_required(self) -> List[EvidenceSourceType]:
        with self._lock:
            return [st for st in EvidenceSourceType if st.is_required and st not in self._providers]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "registered_count": len(self._providers),
                "providers": [p.to_dict() for p in self._providers.values()],
                "required_present": self.required_providers_present(),
                "missing_required": [s.value for s in self.missing_required()],
            }
