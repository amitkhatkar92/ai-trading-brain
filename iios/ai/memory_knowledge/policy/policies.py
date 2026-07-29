"""
policies.py -- iios.ai.memory_knowledge.policy
===============================================
A4 policy framework — interfaces and default implementations for:

* RetentionPolicy    — how long memory entries are kept
* RetrievalPolicy    — who/what may retrieve which entries
* RankingPolicy      — which ranking strategy to apply
* PrivacyPolicy      — access-control rules for scoped memory
* ExpirationPolicy   — when individual entries expire
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from ..core.memory_entry    import MemoryEntry
from ..core.memory_scope    import MemoryScope
from ..core.knowledge_item  import KnowledgeItem
from ..exceptions            import AIMemoryPolicyViolationError


# ─────────────────────────────────────────────────────────────────────────────
# Retention Policy
# ─────────────────────────────────────────────────────────────────────────────

class RetentionPolicy(ABC):
    """Governs whether an entry should be retained."""
    POLICY_NAME: str = "retention_base"

    @abstractmethod
    def should_retain(self, entry: MemoryEntry) -> bool:
        """Return True if the entry should be kept."""


class NeverExpireRetentionPolicy(RetentionPolicy):
    """Retain all entries indefinitely."""
    POLICY_NAME = "never_expire"

    def should_retain(self, entry: MemoryEntry) -> bool:
        return True


class TTLRetentionPolicy(RetentionPolicy):
    """Retain entries that have not yet expired."""
    POLICY_NAME = "ttl"

    def should_retain(self, entry: MemoryEntry) -> bool:
        return not entry.is_expired()


class ScopeRetentionPolicy(RetentionPolicy):
    """Retain only entries belonging to a specific scope."""
    POLICY_NAME = "scope_retain"

    def __init__(self, scope: MemoryScope) -> None:
        self._scope = scope

    def should_retain(self, entry: MemoryEntry) -> bool:
        return entry.scope == self._scope and not entry.is_expired()


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval Policy
# ─────────────────────────────────────────────────────────────────────────────

class RetrievalPolicy(ABC):
    """Governs which entries may be retrieved."""
    POLICY_NAME: str = "retrieval_base"

    @abstractmethod
    def is_retrievable(self, entry: MemoryEntry, requestor_id: str) -> bool:
        """Return True if ``requestor_id`` may retrieve ``entry``."""


class UnrestrictedRetrievalPolicy(RetrievalPolicy):
    """Allow retrieval of any non-expired entry by anyone."""
    POLICY_NAME = "unrestricted"

    def is_retrievable(self, entry: MemoryEntry, requestor_id: str) -> bool:
        return not entry.is_expired()


class OwnerOnlyRetrievalPolicy(RetrievalPolicy):
    """Allow retrieval only by the entry's owner."""
    POLICY_NAME = "owner_only"

    def is_retrievable(self, entry: MemoryEntry, requestor_id: str) -> bool:
        return entry.owner_id == requestor_id and not entry.is_expired()


# ─────────────────────────────────────────────────────────────────────────────
# Ranking Policy
# ─────────────────────────────────────────────────────────────────────────────

class RankingPolicy(ABC):
    """Governs which ranking strategy should be applied."""
    POLICY_NAME: str = "ranking_base"

    @abstractmethod
    def preferred_strategy(self) -> str:
        """Return the STRATEGY_NAME of the preferred ranking strategy."""


class DefaultRankingPolicy(RankingPolicy):
    """Always prefer keyword ranking (safe default, no external deps)."""
    POLICY_NAME = "default_ranking"

    def preferred_strategy(self) -> str:
        return "keyword"


class SemanticRankingPolicy(RankingPolicy):
    """Prefer semantic ranking when an embedding service is available."""
    POLICY_NAME = "semantic_ranking"

    def preferred_strategy(self) -> str:
        return "semantic"


class HybridRankingPolicy(RankingPolicy):
    """Prefer hybrid (keyword + semantic) ranking."""
    POLICY_NAME = "hybrid_ranking"

    def preferred_strategy(self) -> str:
        return "hybrid"


# ─────────────────────────────────────────────────────────────────────────────
# Privacy Policy
# ─────────────────────────────────────────────────────────────────────────────

class PrivacyPolicy(ABC):
    """Governs access based on scope and identity."""
    POLICY_NAME: str = "privacy_base"

    @abstractmethod
    def is_accessible(
        self, entry: MemoryEntry, requestor_id: str, scope: Optional[MemoryScope] = None
    ) -> bool:
        """Return True if the requestor may access the entry."""


class PermissivePrivacyPolicy(PrivacyPolicy):
    """Allow all access — suitable for single-agent or fully-trusted environments."""
    POLICY_NAME = "permissive"

    def is_accessible(
        self, entry: MemoryEntry, requestor_id: str, scope: Optional[MemoryScope] = None
    ) -> bool:
        return True


class ScopeRestrictedPrivacyPolicy(PrivacyPolicy):
    """
    Enforce scope-based access:
    * WORKING  — only the owner
    * SESSION  — only the owner
    * LONG_TERM — any authenticated component (non-empty requestor_id)
    * SHARED   — everyone
    """
    POLICY_NAME = "scope_restricted"

    def is_accessible(
        self, entry: MemoryEntry, requestor_id: str, scope: Optional[MemoryScope] = None
    ) -> bool:
        s = entry.scope
        if s == MemoryScope.SHARED:
            return True
        if s == MemoryScope.LONG_TERM:
            return bool(requestor_id)
        return entry.owner_id == requestor_id


# ─────────────────────────────────────────────────────────────────────────────
# Expiration Policy
# ─────────────────────────────────────────────────────────────────────────────

class ExpirationPolicy(ABC):
    """Computes or validates expiry timestamps for new memory entries."""
    POLICY_NAME: str = "expiration_base"

    @abstractmethod
    def expires_at(self, scope: MemoryScope) -> Optional[float]:
        """Return an absolute expiry timestamp or None (no expiry)."""


class NoExpirationPolicy(ExpirationPolicy):
    """Memory entries never expire."""
    POLICY_NAME = "no_expiration"

    def expires_at(self, scope: MemoryScope) -> Optional[float]:
        return None


class TTLExpirationPolicy(ExpirationPolicy):
    """
    Assign TTLs based on memory scope.

    Defaults (seconds)::

        WORKING   →  300   (5 min)
        SESSION   →  3600  (1 hour)
        LONG_TERM →  None  (no expiry)
        SHARED    →  None  (no expiry)
    """
    POLICY_NAME = "ttl_expiration"

    _DEFAULTS = {
        MemoryScope.WORKING:   300,
        MemoryScope.SESSION:   3600,
        MemoryScope.LONG_TERM: None,
        MemoryScope.SHARED:    None,
    }

    def __init__(self, overrides: Optional[dict] = None) -> None:
        self._ttls = dict(self._DEFAULTS)
        if overrides:
            self._ttls.update(overrides)

    def expires_at(self, scope: MemoryScope) -> Optional[float]:
        ttl = self._ttls.get(scope)
        return (time.time() + ttl) if ttl is not None else None
