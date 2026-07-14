"""iios/investment/decision/core/decision_catalog.py
DecisionCatalog — stores and queries decision-type descriptors and templates.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from iios.investment.decision.core.decision_constants import DecisionType
from iios.investment.decision.core.decision_types import (
    DecisionTypeDescriptor,
    DECISION_TYPE_DESCRIPTORS,
    get_descriptor,
)


@dataclass(frozen=True)
class CatalogEntry:
    """One registered entry: a descriptor + the class it represents."""
    descriptor:      DecisionTypeDescriptor
    class_name:      str                    # fully-qualified class path
    tags:            tuple
    is_builtin:      bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.descriptor.to_dict(),
            "class_name": self.class_name,
            "tags":       list(self.tags),
            "is_builtin": self.is_builtin,
        }


class DecisionCatalog:
    """
    Thread-safe registry of DecisionTypeDescriptors.
    Ships pre-loaded with the 5 built-in decision types.
    Supports runtime registration of custom types.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock             = threading.RLock()
        self._entries: Dict[str, CatalogEntry]     = {}   # decision_type.value → entry
        self._load_builtins()

    def _load_builtins(self) -> None:
        for dt, desc in DECISION_TYPE_DESCRIPTORS.items():
            self._entries[dt.value] = CatalogEntry(
                descriptor=desc,
                class_name=f"iios.investment.decision.core.base_decision.BaseDecision",
                tags=("builtin",),
                is_builtin=True,
            )

    def register(
        self,
        descriptor:  DecisionTypeDescriptor,
        class_name:  str,
        tags:        tuple = (),
    ) -> None:
        with self._lock:
            self._entries[descriptor.decision_type.value] = CatalogEntry(
                descriptor=descriptor,
                class_name=class_name,
                tags=tags,
                is_builtin=False,
            )

    def unregister(self, decision_type_value: str) -> None:
        with self._lock:
            self._entries.pop(decision_type_value, None)

    def get(self, decision_type: DecisionType) -> Optional[CatalogEntry]:
        with self._lock:
            return self._entries.get(decision_type.value)

    def all(self) -> List[CatalogEntry]:
        with self._lock:
            return list(self._entries.values())

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def supported_types(self) -> List[str]:
        with self._lock:
            return list(self._entries.keys())
