"""iios/integration/market_data/streaming/subscription_manager.py

Tracks active subscriptions across all providers.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from iios.integration.market_data.market_data_constants import (
    DEFAULT_MAX_SUBSCRIPTIONS,
    MarketDataType,
    SubscriptionStatus,
)
from iios.integration.market_data.market_data_exceptions import (
    SubscriptionCapacityError,
    SubscriptionNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionRecord:
    """Stored metadata for one active subscription."""

    sub_id:       str               = ""
    provider_id:  str               = ""
    symbols:      list[str]         = field(default_factory=list)
    data_types:   list[MarketDataType] = field(default_factory=list)
    status:       SubscriptionStatus   = SubscriptionStatus.PENDING
    created_at:   float             = field(default_factory=time.time)
    updated_at:   float             = field(default_factory=time.time)
    event_count:  int               = 0
    error_count:  int               = 0
    metadata:     dict[str, Any]    = field(default_factory=dict)

    def touch_event(self) -> None:
        self.event_count += 1
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_id":      self.sub_id,
            "provider_id": self.provider_id,
            "symbols":     self.symbols,
            "status":      self.status.value,
            "created_at":  self.created_at,
            "event_count": self.event_count,
        }


class SubscriptionManager:
    """
    Thread-safe registry of active market data subscriptions.

    Keyed by sub_id (= SubscriptionHandle.handle_id).
    """

    def __init__(self, max_subscriptions: int = DEFAULT_MAX_SUBSCRIPTIONS) -> None:
        self._max      = max_subscriptions
        self._lock     = threading.RLock()
        self._subs:    dict[str, SubscriptionRecord] = {}
        # symbol → set of sub_ids
        self._sym_idx: dict[str, set[str]] = {}
        # provider_id → set of sub_ids
        self._prov_idx: dict[str, set[str]] = {}

    def register(
        self,
        sub_id:      str,
        provider_id: str,
        symbols:     list[str],
        data_types:  list[MarketDataType],
    ) -> SubscriptionRecord:
        with self._lock:
            if len(self._subs) >= self._max:
                raise SubscriptionCapacityError(
                    f"Subscription capacity ({self._max}) exhausted."
                )
            rec = SubscriptionRecord(
                sub_id=sub_id, provider_id=provider_id,
                symbols=symbols, data_types=data_types,
                status=SubscriptionStatus.ACTIVE,
            )
            self._subs[sub_id] = rec
            for sym in symbols:
                self._sym_idx.setdefault(sym, set()).add(sub_id)
            self._prov_idx.setdefault(provider_id, set()).add(sub_id)
            logger.debug("[SubscriptionManager] Registered %s symbols=%s", sub_id, symbols)
            return rec

    def unregister(self, sub_id: str) -> None:
        with self._lock:
            rec = self._subs.pop(sub_id, None)
            if rec is None:
                raise SubscriptionNotFoundError(f"Subscription '{sub_id}' not found.")
            for sym in rec.symbols:
                self._sym_idx.get(sym, set()).discard(sub_id)
            self._prov_idx.get(rec.provider_id, set()).discard(sub_id)

    def get(self, sub_id: str) -> SubscriptionRecord:
        with self._lock:
            rec = self._subs.get(sub_id)
            if rec is None:
                raise SubscriptionNotFoundError(f"Subscription '{sub_id}' not found.")
            return rec

    def find_by_symbol(self, symbol: str) -> list[SubscriptionRecord]:
        with self._lock:
            ids = self._sym_idx.get(symbol, set())
            return [self._subs[sid] for sid in ids if sid in self._subs]

    def find_by_provider(self, provider_id: str) -> list[SubscriptionRecord]:
        with self._lock:
            ids = self._prov_idx.get(provider_id, set())
            return [self._subs[sid] for sid in ids if sid in self._subs]

    def all_subscriptions(self) -> list[SubscriptionRecord]:
        with self._lock:
            return list(self._subs.values())

    def count(self) -> int:
        with self._lock:
            return len(self._subs)

    def count_by_provider(self, provider_id: str) -> int:
        with self._lock:
            return len(self._prov_idx.get(provider_id, set()))

    def record_event(self, sub_id: str) -> None:
        with self._lock:
            rec = self._subs.get(sub_id)
            if rec:
                rec.touch_event()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total":        len(self._subs),
                "max":          self._max,
                "by_provider":  {
                    pid: len(ids) for pid, ids in self._prov_idx.items()
                },
                "symbol_count": len(self._sym_idx),
            }
