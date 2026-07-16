"""iios/execution/brokers/broker_factory.py
==================================================
BrokerFactory — builds BrokerMetadata and registers brokers.

IIOS v1.0: logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from typing import Any

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_FACTORY,
    FACTORY_SYSTEM_ID,
    VERSION,
    BrokerCapabilityCode,
    BrokerMode,
    Exchange,
    ProductType,
    TimeInForce,
)
from .exceptions import BrokerFactoryError
from .broker_metadata import BrokerMetadata, RateLimitSpec

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="BrokerFactory")


class BrokerFactory:
    """
    Constructs BrokerMetadata objects for broker registration.

    Stateless — no mutable state beyond an optional catalogue for quick
    lookup by broker_id.
    """

    def __init__(self) -> None:
        self._catalogue: dict[str, BrokerMetadata] = {}

    # ── Creation ──────────────────────────────────────────────────────────────

    def create_metadata(
        self,
        *,
        broker_id:           str,
        broker_name:         str,
        broker_version:      str = "1.0.0",
        supported_modes:     frozenset[BrokerMode]           | None = None,
        supported_exchanges: frozenset[Exchange]             | None = None,
        supported_products:  frozenset[ProductType]          | None = None,
        supported_tif:       frozenset[TimeInForce]          | None = None,
        capabilities:        frozenset[BrokerCapabilityCode] | None = None,
        rate_limit:          RateLimitSpec | None = None,
        description:         str = "",
        homepage:            str = "",
        contact:             str = "",
        metadata:            dict[str, Any] | None = None,
    ) -> BrokerMetadata:
        """Build and return a BrokerMetadata object."""
        if not broker_id or not broker_id.strip():
            raise BrokerFactoryError("broker_id must not be empty.")
        if not broker_name or not broker_name.strip():
            raise BrokerFactoryError("broker_name must not be empty.")

        bm = BrokerMetadata(
            broker_id           = broker_id,
            broker_name         = broker_name,
            broker_version      = broker_version,
            supported_modes     = supported_modes     or frozenset({BrokerMode.PAPER}),
            supported_exchanges = supported_exchanges or frozenset(),
            supported_products  = supported_products  or frozenset(),
            supported_tif       = supported_tif       or frozenset(),
            capabilities        = capabilities        or frozenset(),
            rate_limit          = rate_limit          or RateLimitSpec(),
            description         = description,
            homepage            = homepage,
            contact             = contact,
            metadata            = metadata or {},
        )
        self._catalogue[broker_id] = bm
        _log.info("BrokerFactory: metadata created.", broker_id=broker_id)
        _audit.log_workflow_event(
            FACTORY_SYSTEM_ID, "create_metadata", "METADATA_CREATED",
            actor=ACTOR_FACTORY, broker_id=broker_id,
        )
        return bm

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def get(self, broker_id: str) -> BrokerMetadata | None:
        return self._catalogue.get(broker_id)

    def has(self, broker_id: str) -> bool:
        return broker_id in self._catalogue

    def all_metadata(self) -> list[BrokerMetadata]:
        return list(self._catalogue.values())

    def registered_broker_ids(self) -> list[str]:
        return list(self._catalogue.keys())

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def gen_broker_id(prefix: str = "broker") -> str:
        """Generate a unique broker ID."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
