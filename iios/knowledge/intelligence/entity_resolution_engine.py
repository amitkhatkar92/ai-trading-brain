"""
entity_resolution_engine.py — iios.knowledge.intelligence
----------------------------------------------------------
Extracts KnowledgeEntity objects from knowledge artifacts (stub mode).

In stub mode:
  - Scans artifact dict fields for string/numeric values
  - Classifies each as a domain entity type via a simple keyword map
  - Returns a deduplicated list of KnowledgeEntity objects

A pluggable EntityExtractionAdapter Protocol allows injection of an NLP
or ML-based extraction backend.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import EntityType
from .knowledge_graph_engine import KnowledgeEntity

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Classification heuristic (stub)
# ---------------------------------------------------------------------------

_KEYWORD_MAP: Dict[str, EntityType] = {
    # Metrics
    "price":    EntityType.METRIC, "return":  EntityType.METRIC,
    "volume":   EntityType.METRIC, "pnl":     EntityType.METRIC,
    "profit":   EntityType.METRIC, "loss":    EntityType.METRIC,
    "rate":     EntityType.METRIC, "ratio":   EntityType.METRIC,
    "sharpe":   EntityType.METRIC, "drawdown": EntityType.METRIC,
    # Assets
    "stock":    EntityType.ASSET,  "equity":   EntityType.ASSET,
    "option":   EntityType.ASSET,  "future":   EntityType.ASSET,
    "bond":     EntityType.ASSET,  "currency": EntityType.ASSET,
    "symbol":   EntityType.ASSET,  "ticker":   EntityType.ASSET,
    # Events
    "event":    EntityType.EVENT,  "news":     EntityType.EVENT,
    "earnings": EntityType.EVENT,  "announcement": EntityType.EVENT,
    # Signals
    "signal":   EntityType.SIGNAL, "indicator": EntityType.SIGNAL,
    "trigger":  EntityType.SIGNAL, "alert":    EntityType.SIGNAL,
    # Risks
    "risk":     EntityType.RISK,   "exposure": EntityType.RISK,
    "vix":      EntityType.RISK,
    # Decisions
    "decision": EntityType.DECISION, "action": EntityType.DECISION,
    "strategy": EntityType.DECISION,
    # Patterns
    "pattern":  EntityType.PATTERN, "trend":  EntityType.PATTERN,
    "cycle":    EntityType.PATTERN,
    # Anomalies
    "anomaly":  EntityType.ANOMALY, "outlier": EntityType.ANOMALY,
    "spike":    EntityType.ANOMALY,
}


def _classify(field_name: str, _value: Any) -> EntityType:
    """Heuristic: return entity type based on field name keywords."""
    name_lower = field_name.lower()
    for kw, etype in _KEYWORD_MAP.items():
        if kw in name_lower:
            return etype
    return EntityType.CONCEPT


# ---------------------------------------------------------------------------
# Pluggable Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EntityExtractionAdapter(Protocol):
    """Protocol for injecting ML-based entity extraction."""
    def extract(
        self,
        artifact_id: str,
        artifact:    Dict[str, Any],
    ) -> List[KnowledgeEntity]: ...


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class EntityResolutionEngine:
    """
    Extracts and deduplicates knowledge entities from artifacts.

    In stub mode: keyword-based field classification.
    With adapter: delegates to an injected EntityExtractionAdapter.
    """

    def __init__(
        self,
        adapter:          Optional[EntityExtractionAdapter] = None,
        min_confidence:   float                             = 0.5,
    ) -> None:
        self._adapter       = adapter
        self._min_confidence = min_confidence

    def extract(
        self,
        artifact_id: str,
        artifact:    Dict[str, Any],
    ) -> List[KnowledgeEntity]:
        """Return list of extracted entities. Never raises."""
        try:
            if self._adapter:
                return self._adapter.extract(artifact_id, artifact)
            return self._stub_extract(artifact_id, artifact)
        except Exception as exc:
            _log.warning(
                f"Entity extraction failed: artifact_id={artifact_id!r} {exc!r}"
            )
            return []

    def extract_batch(
        self,
        artifacts: List[Dict[str, Any]],
    ) -> List[KnowledgeEntity]:
        """Extract entities from multiple artifacts; deduplicate by name."""
        all_entities: List[KnowledgeEntity] = []
        seen_names = set()
        for artifact in artifacts:
            aid = artifact.get("artifact_id", f"art-{uuid.uuid4().hex[:8]}")
            for entity in self.extract(aid, artifact):
                if entity.name not in seen_names:
                    seen_names.add(entity.name)
                    all_entities.append(entity)
        return all_entities

    # ------------------------------------------------------------------
    # Stub extraction
    # ------------------------------------------------------------------

    def _stub_extract(
        self,
        artifact_id: str,
        artifact:    Dict[str, Any],
    ) -> List[KnowledgeEntity]:
        entities: List[KnowledgeEntity] = []
        seen: set = set()
        for field, value in artifact.items():
            if field == "artifact_id":
                continue
            # Only extract string or numeric scalars
            if isinstance(value, (str, int, float)) and str(value).strip():
                name = f"{field}:{value}"
                if name in seen:
                    continue
                seen.add(name)
                entity_type = _classify(field, value)
                entity = KnowledgeEntity.create(
                    name               = name,
                    entity_type        = entity_type,
                    source_artifact_id = artifact_id,
                    confidence         = 0.85,
                    attributes         = {"field": field, "raw_value": str(value)},
                )
                if entity.confidence >= self._min_confidence:
                    entities.append(entity)
        return entities

    def set_adapter(self, adapter: EntityExtractionAdapter) -> None:
        self._adapter = adapter
        _log.info("EntityExtractionAdapter registered")
