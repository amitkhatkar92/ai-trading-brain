"""
iios/knowledge/knowledge_factory.py
=====================================
Factory helpers for creating correctly-typed KnowledgeRecord objects.
"""

from __future__ import annotations

from typing import Any, Optional

from .knowledge_constants import (
    KnowledgeDomain,
    KnowledgePriority,
    KnowledgeSource,
    KnowledgeStatus,
    KnowledgeType,
    DEFAULT_CONFIDENCE,
    KNOWLEDGE_NAMESPACE,
    SYSTEM_OWNER,
)
from .models.knowledge_identifier import generate_id
from .models.knowledge_metadata import KnowledgeMetadata
from .models.knowledge_record import KnowledgeRecord

__all__ = ["KnowledgeFactory", "get_knowledge_factory"]


class KnowledgeFactory:
    """Creates pre-configured KnowledgeRecord objects.

    Usage::

        factory = get_knowledge_factory()
        rec = factory.create_fact(
            title="NIFTY 50 close",
            content={"close": 24350.0},
            domain=KnowledgeDomain.MARKET,
        )
        rec = factory.create_rule(
            title="Max position size rule",
            content={"max_pct": 0.05},
        )
    """

    def __init__(self, default_owner: str = SYSTEM_OWNER, namespace: str = KNOWLEDGE_NAMESPACE) -> None:
        self._owner = default_owner
        self._namespace = namespace

    def _base_metadata(
        self,
        domain: KnowledgeDomain,
        source: KnowledgeSource,
        priority: KnowledgePriority,
        description: str,
        tags: Optional[list[str]],
        confidence: float,
        owner_id: Optional[str],
    ) -> KnowledgeMetadata:
        return KnowledgeMetadata(
            owner_id    = owner_id or self._owner,
            created_by  = owner_id or self._owner,
            updated_by  = owner_id or self._owner,
            domain      = domain,
            source      = source,
            priority    = priority,
            description = description,
            tags        = list(tags or []),
            confidence  = confidence,
        )

    def create(
        self,
        knowledge_type: KnowledgeType,
        title: str,
        content: Any = None,
        domain: KnowledgeDomain = KnowledgeDomain.GENERAL,
        source: KnowledgeSource = KnowledgeSource.SYSTEM,
        priority: KnowledgePriority = KnowledgePriority.MEDIUM,
        status: KnowledgeStatus = KnowledgeStatus.DRAFT,
        description: str = "",
        tags: Optional[list[str]] = None,
        confidence: float = DEFAULT_CONFIDENCE,
        owner_id: Optional[str] = None,
        attributes: Optional[dict[str, Any]] = None,
    ) -> KnowledgeRecord:
        metadata = self._base_metadata(domain, source, priority, description, tags, confidence, owner_id)
        if attributes:
            metadata.attributes.update(attributes)
        rec = KnowledgeRecord(
            knowledge_id   = generate_id(self._namespace),
            knowledge_type = knowledge_type,
            status         = status,
            title          = title,
            content        = content,
            metadata       = metadata,
        )
        return rec

    # ── Type-specific factories ───────────────────────────────────────────────

    def create_fact(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.FACT, title, content, **kwargs)

    def create_rule(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.RULE, title, content, **kwargs)

    def create_concept(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.CONCEPT, title, content, **kwargs)

    def create_pattern(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.PATTERN, title, content, **kwargs)

    def create_strategy(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.STRATEGY, title, content, **kwargs)

    def create_signal(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.SIGNAL, title, content, **kwargs)

    def create_observation(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.OBSERVATION, title, content, **kwargs)

    def create_inference(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.INFERENCE, title, content, **kwargs)

    def create_metric(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.METRIC, title, content, **kwargs)

    def create_event(self, title: str, content: Any = None, **kwargs: Any) -> KnowledgeRecord:
        return self.create(KnowledgeType.EVENT, title, content, **kwargs)


_factory: Optional[KnowledgeFactory] = None


def get_knowledge_factory(owner: str = SYSTEM_OWNER) -> KnowledgeFactory:
    global _factory
    if _factory is None:
        _factory = KnowledgeFactory(default_owner=owner)
    return _factory
