"""
market_integration_manager.py — iios.market.integration
=========================================================
Internal workflow orchestrator for the Market Integration engine.

NOT a public interface — only :class:`~.market_integration_engine.MarketIntegrationEngine`
calls this class.

Workflow
--------
1. Build :class:`~iios.market.engine.MarketRequest` from the integration request
2. Submit to :class:`~iios.market.engine.MarketEngine`
3. Build :class:`~iios.market.snapshot.MarketSnapshot` from the engine response
4. Register snapshot in the snapshot infrastructure (registry, store, cache)
5. Return :class:`~.market_integration_response.MarketIntegrationResponse`

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_MANAGER,
    COMPONENT_ENGINE,
    COMPONENT_SNAPSHOT_CACHE,
    COMPONENT_SNAPSHOT_HISTORY,
    COMPONENT_SNAPSHOT_REGISTRY,
    COMPONENT_SNAPSHOT_STORE,
    IntegrationRequestType,
    IntegrationStatus,
)
from .market_integration_request import MarketIntegrationRequest
from .market_integration_response import MarketIntegrationResponse

_log = get_logger(__name__)

# Map IntegrationRequestType → MarketWorkflowType value string
_WORKFLOW_TYPE_MAP: Dict[IntegrationRequestType, str] = {
    IntegrationRequestType.MARKET_OVERVIEW:         "market_overview",
    IntegrationRequestType.MARKET_REGIME_ANALYSIS:  "regime_analysis",
    IntegrationRequestType.SECTOR_ANALYSIS:         "sector_analysis",
    IntegrationRequestType.BREADTH_ANALYSIS:        "breadth_analysis",
    IntegrationRequestType.VOLATILITY_ANALYSIS:     "volatility_analysis",
    IntegrationRequestType.LIQUIDITY_ANALYSIS:      "liquidity_analysis",
    IntegrationRequestType.CORRELATION_ANALYSIS:    "correlation_analysis",
    IntegrationRequestType.FORECAST_REQUEST:        "forecast",
    IntegrationRequestType.MARKET_SNAPSHOT_REQUEST: "market_overview",
    IntegrationRequestType.MARKET_HISTORY_REQUEST:  "market_overview",
}


class MarketIntegrationManager:
    """
    Orchestrates the integration workflow.

    Parameters
    ----------
    component_registry : Provides access to subsystem instances.
    listener_fn :        Callable for emitting domain events upstream.
    """

    def __init__(
        self,
        component_registry: Any,          # MarketComponentRegistry (avoid circular)
        listener_fn:        Optional[Callable[[Any], None]] = None,
    ) -> None:
        self._components  = component_registry
        self._dispatch_ev = listener_fn or (lambda ev: None)

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def run(
        self,
        request: MarketIntegrationRequest,
    ) -> MarketIntegrationResponse:
        """
        Execute the full integration workflow for *request*.

        Returns a :class:`~.market_integration_response.MarketIntegrationResponse`
        (success or failure — never raises).
        """
        t0 = time.monotonic()
        try:
            response = self._run_pipeline(request)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            _log.error(
                f"Integration pipeline failed: {exc}",
                exc=exc,
            )
            response = MarketIntegrationResponse.create_failure(
                request_id         = request.request_id,
                integration_id     = request.integration_id,
                exchange           = request.exchange,
                request_type       = request.request_type,
                market_analysis_id = request.market_analysis_id,
                error_message      = str(exc),
                elapsed_s          = elapsed,
            )
        return response

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(
        self,
        request: MarketIntegrationRequest,
    ) -> MarketIntegrationResponse:
        t0 = time.monotonic()

        engine = self._components.get(COMPONENT_ENGINE)

        # ── Step 1: build MarketRequest from integration request ──────
        engine_request = self._build_engine_request(request)

        # ── Step 2: submit to MarketEngine ────────────────────────────
        engine_response = None
        snapshot_id     = ""

        if engine is not None:
            try:
                engine_response = engine.submit(engine_request)
            except Exception as exc:
                _log.warning(
                    f"MarketEngine.submit raised: {exc} — proceeding with no snapshot"
                )

        # ── Step 3: build + publish MarketSnapshot ────────────────────
        if engine_response is not None:
            snapshot_id = self._build_and_publish_snapshot(
                request, engine_response
            )

        elapsed = time.monotonic() - t0

        return MarketIntegrationResponse.create_success(
            request_id         = request.request_id,
            integration_id     = request.integration_id,
            exchange           = request.exchange,
            request_type       = request.request_type,
            market_analysis_id = request.market_analysis_id,
            snapshot_id        = snapshot_id,
            elapsed_s          = elapsed,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_engine_request(
        self, request: MarketIntegrationRequest
    ) -> Any:
        """Build a MarketRequest from the integration request."""
        try:
            from iios.market.engine import MarketRequest
            from iios.market.engine.constants import MarketWorkflowType, SchedulerPriority
        except ImportError:
            return None

        wf_str = _WORKFLOW_TYPE_MAP.get(
            request.request_type,
            "market_overview",
        )
        # Map string to enum — fall back to MARKET_OVERVIEW
        try:
            wf = MarketWorkflowType(wf_str)
        except ValueError:
            wf = MarketWorkflowType.MARKET_OVERVIEW

        return MarketRequest.create(
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            workflow_type      = wf,
            inputs             = dict(request.inputs),
            metadata           = dict(request.metadata),
        )

    def _build_and_publish_snapshot(
        self,
        request:         MarketIntegrationRequest,
        engine_response: Any,
    ) -> str:
        """
        Build a MarketSnapshot from the engine response, register it in
        all snapshot infrastructure, and return its snapshot_id.
        """
        try:
            from iios.market.snapshot import (
                MarketSnapshotFactory,
                SnapshotStatus,
                SnapshotMetadata,
            )
        except ImportError:
            return ""

        # Extract outputs from engine response snapshot (if available)
        outputs: Dict[str, Any] = {}
        if hasattr(engine_response, "snapshot") and engine_response.snapshot:
            outputs = dict(engine_response.snapshot.outputs or {})

        metadata = SnapshotMetadata.create(
            environment       = "production",
            source_components = [
                "market_lifecycle", "market_engine",
                "market_policy_framework", "market_analytics_framework",
            ],
        )

        market_snapshot = MarketSnapshotFactory.create(
            snapshot_id        = str(uuid.uuid4()),
            market_analysis_id = request.market_analysis_id,
            exchange           = request.exchange,
            status             = SnapshotStatus.PUBLISHED,
            is_valid           = engine_response.is_success
                                 if hasattr(engine_response, "is_success")
                                 else True,
            metadata           = metadata,
            # Pass through any analytics outputs keyed in engine response
            regime_data        = outputs.get("regime"),
            trend_data         = outputs.get("trend"),
            scores_data        = outputs.get("scores"),
            breadth_data       = outputs.get("breadth"),
            volatility_data    = outputs.get("volatility"),
            liquidity_data     = outputs.get("liquidity"),
            correlation_data   = outputs.get("correlation"),
            forecast_data      = outputs.get("forecast"),
        )

        # Register in snapshot registry
        snap_registry = self._components.get(COMPONENT_SNAPSHOT_REGISTRY)
        if snap_registry is not None:
            try:
                snap_registry.register(market_snapshot)
            except Exception as exc:
                _log.warning(f"Snapshot registry error: {exc}")

        # Save in store
        snap_store = self._components.get(COMPONENT_SNAPSHOT_STORE)
        if snap_store is not None:
            try:
                snap_store.save(market_snapshot)
            except Exception as exc:
                _log.warning(f"Snapshot store error: {exc}")

        # Cache for fast retrieval
        snap_cache = self._components.get(COMPONENT_SNAPSHOT_CACHE)
        if snap_cache is not None:
            try:
                snap_cache.put(market_snapshot)
            except Exception as exc:
                _log.warning(f"Snapshot cache error: {exc}")

        # History
        snap_history = self._components.get(COMPONENT_SNAPSHOT_HISTORY)
        if snap_history is not None:
            try:
                snap_history.record_snapshot(market_snapshot.snapshot_id)
            except Exception as exc:
                _log.warning(f"Snapshot history error: {exc}")

        return market_snapshot.snapshot_id
