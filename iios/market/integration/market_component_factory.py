"""
market_component_factory.py — iios.market.integration
=======================================================
Factory that creates and configures Market Intelligence subsystem instances.

All subsystem instances are created here and wired into the
:class:`~.market_component_registry.MarketComponentRegistry`.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Optional

from .constants import (
    COMPONENT_ANALYTICS_ENGINE,
    COMPONENT_ENGINE,
    COMPONENT_LIFECYCLE,
    COMPONENT_POLICY_ENGINE,
    COMPONENT_SNAPSHOT_CACHE,
    COMPONENT_SNAPSHOT_HISTORY,
    COMPONENT_SNAPSHOT_REGISTRY,
    COMPONENT_SNAPSHOT_STORE,
    DEFAULT_CACHE_TTL_S,
    DEFAULT_MAX_CACHE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REGISTRY,
)


class MarketComponentFactory:
    """
    Creates Market Intelligence subsystem instances.

    Each ``create_*`` method returns a fresh, unconfigured (not yet started)
    instance.  The caller is responsible for starting and stopping them.
    """

    # ------------------------------------------------------------------
    # M1 — Market Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def create_lifecycle(**kwargs: Any):
        from iios.market.lifecycle import MarketLifecycle
        return MarketLifecycle(**kwargs)

    # ------------------------------------------------------------------
    # M2 — Market Engine
    # ------------------------------------------------------------------

    @staticmethod
    def create_engine(**kwargs: Any):
        from iios.market.engine import MarketEngine
        return MarketEngine(**kwargs)

    # ------------------------------------------------------------------
    # M3 — Market Policy Engine
    # ------------------------------------------------------------------

    @staticmethod
    def create_policy_engine(**kwargs: Any):
        from iios.market.policies import MarketPolicyEngine
        return MarketPolicyEngine(**kwargs)

    # ------------------------------------------------------------------
    # M4 — Market Analytics Engine
    # ------------------------------------------------------------------

    @staticmethod
    def create_analytics_engine(**kwargs: Any):
        from iios.market.analytics import MarketAnalyticsEngine
        return MarketAnalyticsEngine(**kwargs)

    # ------------------------------------------------------------------
    # M5 — Market Snapshot infrastructure
    # ------------------------------------------------------------------

    @staticmethod
    def create_snapshot_registry(max_entries: int = DEFAULT_MAX_REGISTRY):
        from iios.market.snapshot import MarketSnapshotRegistry
        return MarketSnapshotRegistry(max_snapshots=max_entries)

    @staticmethod
    def create_snapshot_store(max_entries: int = DEFAULT_MAX_REGISTRY):
        from iios.market.snapshot import MarketSnapshotStore
        return MarketSnapshotStore(max_snapshots=max_entries)

    @staticmethod
    def create_snapshot_cache(
        max_entries: int   = DEFAULT_MAX_CACHE,
        ttl_s:       float = DEFAULT_CACHE_TTL_S,
    ):
        from iios.market.snapshot import MarketSnapshotCache
        return MarketSnapshotCache(max_entries=max_entries, ttl_s=ttl_s)

    @staticmethod
    def create_snapshot_history(max_entries: int = DEFAULT_MAX_HISTORY):
        from iios.market.snapshot import MarketSnapshotHistory
        return MarketSnapshotHistory(max_entries=max_entries)

    # ------------------------------------------------------------------
    # Convenience: create all components
    # ------------------------------------------------------------------

    def create_all(self) -> dict:
        """
        Create one instance of every component.

        Returns a dict keyed by ``COMPONENT_*`` constant.
        """
        return {
            COMPONENT_LIFECYCLE:        self.create_lifecycle(),
            COMPONENT_ENGINE:           self.create_engine(),
            COMPONENT_POLICY_ENGINE:    self.create_policy_engine(),
            COMPONENT_ANALYTICS_ENGINE: self.create_analytics_engine(),
            COMPONENT_SNAPSHOT_REGISTRY: self.create_snapshot_registry(),
            COMPONENT_SNAPSHOT_STORE:   self.create_snapshot_store(),
            COMPONENT_SNAPSHOT_CACHE:   self.create_snapshot_cache(),
            COMPONENT_SNAPSHOT_HISTORY: self.create_snapshot_history(),
        }
