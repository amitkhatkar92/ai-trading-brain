"""iios/investment/company/company_intelligence_engine.py
Top-level facade for the Company Intelligence Engine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from iios.investment.company.company_constants import (
    COMPANY_ENGINE_SYSTEM_ID,
    COMPANY_ENGINE_VERSION,
    SectorClassification,
)
from iios.investment.company.company_exceptions import (
    CompanyEngineAlreadyRunningError,
    CompanyEngineNotInitializedError,
)
from iios.investment.company.company_manager import (
    CompanyManager,
    get_company_manager,
    reset_company_manager,
)
from iios.investment.company.company_registry import (
    CompanyRegistry,
    get_company_registry,
    reset_company_registry,
)
from iios.investment.company.models.company_intelligence import CompanyIntelligence
from iios.investment.company.profile.company_profile import CompanyProfile


class CompanyIntelligenceEngine:
    """
    Top-level facade for the Company Intelligence Engine.

    Provides a stable public API consumed by higher IIOS layers.
    Delegates all heavy lifting to CompanyManager.
    """

    VERSION   = COMPANY_ENGINE_VERSION
    SYSTEM_ID = COMPANY_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:       threading.RLock     = threading.RLock()
        self._running:    bool                = False
        self._manager:    CompanyManager | None = None
        self._registry:   CompanyRegistry | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  CompanyManager  | None = None,
        registry: CompanyRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise CompanyEngineAlreadyRunningError(
                    "CompanyIntelligenceEngine is already running"
                )
            self._registry = registry or get_company_registry()
            self._manager  = manager  or get_company_manager()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._manager = None
            self._registry = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── public API ───────────────────────────────────────────────────────────

    def register_company(
        self,
        company_id: str,
        ticker:     str                  = "",
        name:       str                  = "",
        sector:     SectorClassification = SectorClassification.UNKNOWN,
        exchange:   str                  = "",
    ) -> CompanyProfile:
        self._require_running()
        return self._manager.register_company(
            company_id=company_id,
            ticker=ticker,
            name=name,
            sector=sector,
            exchange=exchange,
        )

    def analyze(self, company_id: str, **data: Any) -> CompanyIntelligence:
        self._require_running()
        return self._manager.analyze(company_id, **data)

    async def analyze_async(self, company_id: str, **data: Any) -> CompanyIntelligence:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.analyze(company_id, **data))

    def get_latest(self, company_id: str) -> CompanyIntelligence:
        self._require_running()
        return self._manager.get_latest(company_id)

    def get_profile(self, company_id: str) -> CompanyProfile:
        self._require_running()
        return self._manager.get_profile(company_id)

    def recent(self, n: int = 10) -> list[CompanyIntelligence]:
        self._require_running()
        return self._manager.recent(n)

    def health(self) -> dict[str, Any]:
        return {
            "status":     "running" if self._running else "stopped",
            "version":    self.VERSION,
            "system_id":  self.SYSTEM_ID,
        }

    def stats(self) -> dict[str, Any]:
        self._require_running()
        return self._manager.statistics()

    # ── internal ─────────────────────────────────────────────────────────────

    def _require_running(self) -> None:
        if not self._running or self._manager is None:
            raise CompanyEngineNotInitializedError(
                "CompanyIntelligenceEngine is not initialized. Call initialize() first."
            )


# ── module-level singleton ────────────────────────────────────────────────────

_engine_lock:     threading.Lock                     = threading.Lock()
_engine_instance: CompanyIntelligenceEngine | None   = None


def get_company_engine() -> CompanyIntelligenceEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = CompanyIntelligenceEngine()
        return _engine_instance


def reset_company_engine() -> None:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None:
            _engine_instance.shutdown()
        _engine_instance = None
