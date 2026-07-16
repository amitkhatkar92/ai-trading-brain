"""iios/execution/oms/integration/oms_integration_statistics.py
==================================================
IntegrationStatistics — aggregated statistics across all OMS components.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IntegrationStatistics:
    """
    Immutable aggregated statistics across all five OMS components.

    Produced by OMSIntegrationEngine.statistics() and embedded
    in every OMSSnapshot.
    """
    # Orders Managed (from OrderManager)
    orders_managed:        int   = 0
    orders_active:         int   = 0
    orders_completed:      int   = 0
    orders_cancelled:      int   = 0

    # Orders Queued (from OrderQueue)
    orders_queued:         int   = 0
    orders_dispatched:     int   = 0
    orders_failed_queue:   int   = 0

    # Orders Routed (from OrderRouter)
    orders_routed:         int   = 0
    routing_rejected:      int   = 0
    routing_failed:        int   = 0

    # Orders Persisted (from Persistence)
    orders_persisted:      int   = 0
    orders_archived:       int   = 0

    # Orders in Book (from OrderBook)
    book_entries:          int   = 0
    book_active_entries:   int   = 0

    # Integration-level
    snapshots_published:   int   = 0
    validations_run:       int   = 0
    validation_success:    int   = 0
    validation_failure:    int   = 0
    queries_served:        int   = 0
    component_count:       int   = 5

    # Latency
    avg_latency_ms:        float = 0.0

    last_updated_at:       float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            # Manager
            "orders_managed":       self.orders_managed,
            "orders_active":        self.orders_active,
            "orders_completed":     self.orders_completed,
            "orders_cancelled":     self.orders_cancelled,
            # Queue
            "orders_queued":        self.orders_queued,
            "orders_dispatched":    self.orders_dispatched,
            "orders_failed_queue":  self.orders_failed_queue,
            # Router
            "orders_routed":        self.orders_routed,
            "routing_rejected":     self.routing_rejected,
            "routing_failed":       self.routing_failed,
            # Persistence
            "orders_persisted":     self.orders_persisted,
            "orders_archived":      self.orders_archived,
            # Book
            "book_entries":         self.book_entries,
            "book_active_entries":  self.book_active_entries,
            # Integration
            "snapshots_published":  self.snapshots_published,
            "validations_run":      self.validations_run,
            "validation_success":   self.validation_success,
            "validation_failure":   self.validation_failure,
            "queries_served":       self.queries_served,
            "component_count":      self.component_count,
            "avg_latency_ms":       round(self.avg_latency_ms, 3),
            "last_updated_at":      self.last_updated_at,
        }
