"""iios/investment/investment_engine.py
InvestmentIntelligenceEngine — top-level singleton authority.
"""
from __future__ import annotations

import asyncio
import threading

from iios.investment.investment_constants import (
    AssetClass,
    IntelligenceType,
    INVESTMENT_ENGINE_VERSION,
    INVESTMENT_ENGINE_SYSTEM_ID,
)
from iios.investment.investment_exceptions import (
    EngineAlreadyRunningError,
    EngineNotInitializedError,
)
from iios.investment.investment_manager import (
    InvestmentManager,
    get_investment_manager,
)
from iios.investment.investment_registry import (
    InvestmentRegistry,
    get_investment_registry,
    reset_investment_registry,
)
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_result import InvestmentResult
from iios.investment.models.investment_session import InvestmentSession
from iios.investment.workflow.investment_workflow import InvestmentWorkflow


class InvestmentIntelligenceEngine:
    """
    Central authority of the Investment Intelligence Layer.

    Lifecycle:
    - ``initialize()`` — must be called before any analysis
    - ``shutdown()``   — releases resources

    Core operations:
    - ``analyze(request)``         → InvestmentResult
    - ``analyze_async(request)``   → awaitable InvestmentResult
    - ``certify_session(name)``    → InvestmentSession
    """

    VERSION   = INVESTMENT_ENGINE_VERSION
    SYSTEM_ID = INVESTMENT_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.Lock          = threading.Lock()
        self._running:  bool                    = False
        self._manager:  InvestmentManager | None = None
        self._registry: InvestmentRegistry | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  InvestmentManager  | None = None,
        registry: InvestmentRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._registry = registry or get_investment_registry()
            self._manager  = manager  or get_investment_manager()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── workflow + domain-engine registration ─────────────────────────────────

    def register_workflow(
        self,
        workflow:  InvestmentWorkflow,
        *,
        overwrite: bool = False,
    ) -> None:
        self._get_registry().register_workflow(workflow, overwrite=overwrite)
        self._get_manager().register_workflow(workflow, overwrite=overwrite)

    def register_domain_engine(
        self,
        intelligence_type: IntelligenceType,
        engine: object,
        *,
        overwrite: bool = False,
    ) -> None:
        self._get_registry().register_domain_engine(
            intelligence_type, engine, overwrite=overwrite
        )

    def register_asset_class(
        self,
        asset_class: AssetClass,
        handler: object = None,
    ) -> None:
        self._get_registry().register_asset_class(asset_class, handler=handler)

    # ── core analysis ─────────────────────────────────────────────────────────

    def analyze(
        self,
        request:    InvestmentRequest,
        session_id: str  = "",
        parallel:   bool = False,
    ) -> InvestmentResult:
        self._assert_running()
        return self._manager.analyze(request, session_id=session_id, parallel=parallel)  # type: ignore[union-attr]

    async def analyze_async(
        self,
        request:    InvestmentRequest,
        session_id: str  = "",
        parallel:   bool = False,
    ) -> InvestmentResult:
        self._assert_running()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._manager.analyze(request, session_id=session_id, parallel=parallel),  # type: ignore[union-attr]
        )

    # ── session management ────────────────────────────────────────────────────

    def create_session(self, name: str = "", source_id: str = "") -> InvestmentSession:
        self._assert_running()
        return self._manager.create_session(name=name, source_id=source_id)  # type: ignore[union-attr]

    def get_session(self, session_id: str) -> InvestmentSession:
        self._assert_running()
        return self._manager.get_session(session_id)  # type: ignore[union-attr]

    # ── result retrieval ──────────────────────────────────────────────────────

    def get(self, result_id: str) -> InvestmentResult:
        self._assert_running()
        return self._manager.get(result_id)  # type: ignore[union-attr]

    def recent(self, n: int = 10) -> list[InvestmentResult]:
        self._assert_running()
        return self._manager.recent(n)  # type: ignore[union-attr]

    # ── health / stats ────────────────────────────────────────────────────────

    def health(self) -> dict:
        reg_stats = self._get_registry().statistics() if self._registry else {}
        return {
            "running":    self._running,
            "version":    self.VERSION,
            "system_id":  self.SYSTEM_ID,
            "registry":   reg_stats,
        }

    def stats(self) -> dict:
        self._assert_running()
        s = self._manager.statistics()  # type: ignore[union-attr]
        s["version"]   = self.VERSION
        s["system_id"] = self.SYSTEM_ID
        return s

    # ── internals ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if not self._running:
            raise EngineNotInitializedError()

    def _get_registry(self) -> InvestmentRegistry:
        return self._registry or get_investment_registry()

    def _get_manager(self) -> InvestmentManager:
        return self._manager or get_investment_manager()


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock                  = threading.Lock()
_instance:       InvestmentIntelligenceEngine | None = None


def get_investment_engine() -> InvestmentIntelligenceEngine:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = InvestmentIntelligenceEngine()
    return _instance


def reset_investment_engine() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        if _instance is not None:
            try:
                _instance.shutdown()
            except Exception:  # noqa: BLE001
                pass
        _instance = None
