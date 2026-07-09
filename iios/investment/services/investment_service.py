"""iios/investment/services/investment_service.py
InvestmentService — CRUD + lifecycle operations over InvestmentResults.
"""
from __future__ import annotations

import threading

from iios.investment.investment_exceptions import InvestmentNotFoundError
from iios.investment.models.investment_history import InvestmentHistory
from iios.investment.models.investment_metadata import InvestmentMetadata
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_result import InvestmentResult


class InvestmentService:
    """
    High-level service facade for investment result management.

    Works on top of InvestmentHistory. Does NOT run new analyses —
    that is the responsibility of InvestmentManager.
    """

    def __init__(self, history: InvestmentHistory | None = None) -> None:
        self._lock:     threading.RLock            = threading.RLock()
        self._history   = history or InvestmentHistory()
        self._metadata: dict[str, InvestmentMetadata] = {}  # result_id → metadata
        self._archived: set[str]                   = set()

    # ── create (store a result that was already produced by the manager) ──────

    def store(self, result: InvestmentResult) -> None:
        self._history.store(result)

    # ── lookup ────────────────────────────────────────────────────────────────

    def get(self, result_id: str) -> InvestmentResult:
        return self._history.get(result_id)  # type: ignore[return-value]

    def recent(self, n: int = 10) -> list[InvestmentResult]:
        return self._history.recent(n)  # type: ignore[return-value]

    def by_request(self, request_id: str) -> list[InvestmentResult]:
        return self._history.by_request(request_id)  # type: ignore[return-value]

    def by_session(self, session_id: str) -> list[InvestmentResult]:
        return self._history.by_session(session_id)  # type: ignore[return-value]

    # ── metadata update ───────────────────────────────────────────────────────

    def set_metadata(
        self,
        result_id:  str,
        source:     str = "",
        tags:       list[str] | None = None,
        attributes: dict | None = None,
    ) -> InvestmentMetadata:
        # Verify result exists
        self._history.get(result_id)
        m = InvestmentMetadata(
            result_id=result_id,
            source=source,
            tags=tags or [],
            attributes=attributes or {},
        )
        with self._lock:
            self._metadata[result_id] = m
        return m

    def get_metadata(self, result_id: str) -> InvestmentMetadata | None:
        with self._lock:
            return self._metadata.get(result_id)

    # ── archive ───────────────────────────────────────────────────────────────

    def archive(self, result_id: str) -> None:
        self._history.get(result_id)   # ensure it exists
        with self._lock:
            self._archived.add(result_id)

    def is_archived(self, result_id: str) -> bool:
        with self._lock:
            return result_id in self._archived

    # ── replay ────────────────────────────────────────────────────────────────

    def replay(self, result_id: str) -> dict:
        """
        Return a replay summary for a stored result.
        Actual re-execution is delegated back to InvestmentManager by the caller.
        """
        result: InvestmentResult = self._history.get(result_id)  # type: ignore[assignment]
        return {
            "original_result_id": result_id,
            "request_id":         result.request_id,
            "session_id":         result.session_id,
            "analyses_count":     len(result.analyses),
            "status":             result.status.value,
            "can_replay":         not self.is_archived(result_id),
        }

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        asset_class: str | None = None,
        status:      str | None = None,
        n:           int        = 100,
    ) -> list[InvestmentResult]:
        all_results = self._history.recent(n)
        if asset_class:
            all_results = [
                r for r in all_results
                if r.summary.get("asset_class") == asset_class
            ]
        if status:
            all_results = [
                r for r in all_results
                if r.status.value == status
            ]
        return all_results

    # ── statistics ────────────────────────────────────────────────────────────

    def count(self) -> int:
        return self._history.count()
