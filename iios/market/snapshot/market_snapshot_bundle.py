"""
market_snapshot_bundle.py — iios.market.snapshot
=================================================
Bundle — an ordered, immutable collection of related snapshots.

A bundle groups snapshots that belong to the same trading session,
workflow, or analysis run. It is itself immutable and serialisable.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION
from .exceptions import MarketSnapshotBundleError
from .market_snapshot import MarketSnapshot


@dataclass(frozen=True)
class MarketSnapshotBundle:
    """
    Immutable ordered collection of related :class:`~.market_snapshot.MarketSnapshot` objects.

    Fields
    ------
    bundle_id :         Unique bundle identifier.
    workflow_id :       Originating workflow identifier.
    exchange :          Exchange all snapshots in this bundle belong to.
    label :             Human-readable bundle label.
    snapshots :         Ordered tuple of snapshots.
    created_at :        Creation timestamp.
    framework_version : Framework version string.
    metadata :          Supplementary key-value pairs.
    """
    bundle_id:          str
    workflow_id:        str
    exchange:           str
    label:              str
    snapshots:          Tuple[MarketSnapshot, ...]
    created_at:         float
    framework_version:  str
    metadata:           Dict[str, Any]

    @classmethod
    def create(
        cls,
        snapshots: List[MarketSnapshot],
        *,
        bundle_id:  Optional[str]            = None,
        workflow_id: str                     = "",
        exchange:   str                      = "",
        label:      str                      = "",
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> "MarketSnapshotBundle":
        if not snapshots:
            raise MarketSnapshotBundleError("Bundle must contain at least one snapshot")
        return cls(
            bundle_id         = bundle_id or str(uuid.uuid4()),
            workflow_id       = workflow_id,
            exchange          = exchange or snapshots[0].exchange,
            label             = label,
            snapshots         = tuple(snapshots),
            created_at        = time.time(),
            framework_version = VERSION,
            metadata          = dict(metadata or {}),
        )

    @property
    def count(self) -> int:
        return len(self.snapshots)

    @property
    def latest(self) -> Optional[MarketSnapshot]:
        return self.snapshots[-1] if self.snapshots else None

    @property
    def earliest(self) -> Optional[MarketSnapshot]:
        return self.snapshots[0] if self.snapshots else None

    def get_by_id(self, snapshot_id: str) -> Optional[MarketSnapshot]:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def filter_by_exchange(self, exchange: str) -> "MarketSnapshotBundle":
        filtered = [s for s in self.snapshots if s.exchange == exchange]
        if not filtered:
            raise MarketSnapshotBundleError(
                f"No snapshots for exchange {exchange!r} in bundle {self.bundle_id!r}"
            )
        return MarketSnapshotBundle.create(
            filtered,
            bundle_id   = str(uuid.uuid4()),
            workflow_id = self.workflow_id,
            exchange    = exchange,
            label       = f"{self.label}:{exchange}",
            metadata    = dict(self.metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":        self.bundle_id,
            "workflow_id":      self.workflow_id,
            "exchange":         self.exchange,
            "label":            self.label,
            "count":            self.count,
            "snapshots":        [s.to_dict() for s in self.snapshots],
            "created_at":       self.created_at,
            "framework_version": self.framework_version,
        }


class MarketSnapshotBundleBuilder:
    """
    Accumulates snapshots and produces an immutable
    :class:`MarketSnapshotBundle` when :meth:`build` is called.
    """

    def __init__(
        self,
        *,
        bundle_id:  Optional[str]            = None,
        workflow_id: str                     = "",
        exchange:   str                      = "",
        label:      str                      = "",
        metadata:   Optional[Dict[str, Any]] = None,
    ) -> None:
        self._bundle_id  = bundle_id or str(uuid.uuid4())
        self._workflow_id = workflow_id
        self._exchange   = exchange
        self._label      = label
        self._metadata   = dict(metadata or {})
        self._snapshots: List[MarketSnapshot] = []

    def add(self, snapshot: MarketSnapshot) -> "MarketSnapshotBundleBuilder":
        self._snapshots.append(snapshot)
        return self

    def add_many(self, snapshots: List[MarketSnapshot]) -> "MarketSnapshotBundleBuilder":
        self._snapshots.extend(snapshots)
        return self

    def build(self) -> MarketSnapshotBundle:
        return MarketSnapshotBundle.create(
            self._snapshots,
            bundle_id   = self._bundle_id,
            workflow_id = self._workflow_id,
            exchange    = self._exchange,
            label       = self._label,
            metadata    = self._metadata,
        )
