"""iios/investment/portfolio/portfolio_manager.py
Orchestrates portfolio lifecycle and full analysis pipeline.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from iios.investment.portfolio.portfolio_constants import (
    DrawdownSeverity,
    PortfolioHealthStatus,
    PortfolioObjective,
    PortfolioStatus,
    PortfolioType,
    RiskLevel,
)
from iios.investment.portfolio.portfolio_exceptions import (
    PortfolioNotFoundError,
    PortfolioAlreadyExistsError,
    PositionNotFoundError,
)
from iios.investment.portfolio.portfolio_factory import PortfolioFactory
from iios.investment.portfolio.portfolio_registry import (
    PortfolioRegistry,
    get_portfolio_registry,
)
from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.core.portfolio_history import PortfolioHistory
from iios.investment.portfolio.core.portfolio_intelligence import PortfolioIntelligence
from iios.investment.portfolio.core.portfolio_profile import PortfolioProfile
from iios.investment.portfolio.core.portfolio_snapshot import PortfolioSnapshot
from iios.investment.portfolio.core.portfolio_statistics import PortfolioStatistics
from iios.investment.portfolio.core.position import Position
from iios.investment.portfolio.risk.drawdown_engine import DrawdownEngine
from iios.investment.portfolio.risk.risk_engine import RiskEngine
from iios.investment.portfolio.exposure.exposure_engine import ExposureEngine
from iios.investment.portfolio.allocation.allocation_engine import AllocationEngine
from iios.investment.portfolio.analytics.portfolio_analyzer import PortfolioAnalyzer


class PortfolioManager:
    """
    Central coordinator for all portfolio operations.

    Thread-safe; designed as a long-lived singleton.
    Responsibilities:
    - Portfolio lifecycle (create / activate / close)
    - Position management (add / remove / update price)
    - Full analytics pipeline (analyze → PortfolioIntelligence)
    """

    def __init__(
        self,
        registry:          PortfolioRegistry | None = None,
        history:           PortfolioHistory  | None = None,
        drawdown_engine:   DrawdownEngine    | None = None,
        risk_engine:       RiskEngine        | None = None,
        exposure_engine:   ExposureEngine    | None = None,
        allocation_engine: AllocationEngine  | None = None,
        portfolio_analyzer: PortfolioAnalyzer | None = None,
        max_recent:        int               = 1_000,
    ) -> None:
        self._lock              = threading.RLock()
        self._registry          = registry           or get_portfolio_registry()
        self._history_store     = history            or PortfolioHistory()
        self._drawdown          = drawdown_engine    or DrawdownEngine()
        self._risk              = risk_engine        or RiskEngine()
        self._exposure          = exposure_engine    or ExposureEngine()
        self._allocation        = allocation_engine  or AllocationEngine()
        self._analyzer          = portfolio_analyzer or PortfolioAnalyzer()

        self._profiles:         dict[str, PortfolioProfile]      = {}
        self._latest:           dict[str, PortfolioIntelligence]  = {}
        self._recent:           deque[PortfolioIntelligence]     = deque(maxlen=max_recent)
        self._stats             = PortfolioStatistics()
        self._started_at        = time.time()
        self._total_duration_ms = 0.0

    # ── portfolio lifecycle ───────────────────────────────────────────────────

    def create_portfolio(
        self,
        name:           str              = "",
        portfolio_type: PortfolioType    = PortfolioType.EQUITY,
        objective:      PortfolioObjective = PortfolioObjective.GROWTH,
        base_currency:  str              = "INR",
        cash:           float            = 0.0,
        **kwargs: Any,
    ) -> PortfolioProfile:
        portfolio = PortfolioFactory.make_portfolio(
            name=name, portfolio_type=portfolio_type,
            objective=objective, base_currency=base_currency, cash=cash, **kwargs,
        )
        profile = PortfolioFactory.make_profile(portfolio, **kwargs)
        profile.inception_nav = cash
        profile.peak_nav      = cash

        with self._lock:
            pid = portfolio.portfolio_id
            if pid in self._profiles:
                raise PortfolioAlreadyExistsError(portfolio_id=pid)
            self._registry.register(pid, name, portfolio_type.value)
            self._profiles[pid] = profile
            self._stats.portfolios_tracked = len(self._profiles)

        return profile

    def get_profile(self, portfolio_id: str) -> PortfolioProfile:
        with self._lock:
            if portfolio_id not in self._profiles:
                raise PortfolioNotFoundError(portfolio_id=portfolio_id)
            return self._profiles[portfolio_id]

    def close_portfolio(self, portfolio_id: str) -> None:
        profile = self.get_profile(portfolio_id)
        profile.portfolio.status = PortfolioStatus.CLOSED

    # ── position management ───────────────────────────────────────────────────

    def add_position(self, portfolio_id: str, position: Position) -> Portfolio:
        profile = self.get_profile(portfolio_id)
        with self._lock:
            portfolio = profile.portfolio
            portfolio.add_position(position)
            return portfolio

    def remove_position(self, portfolio_id: str, position_id: str) -> None:
        profile = self.get_profile(portfolio_id)
        with self._lock:
            if position_id not in profile.portfolio.positions:
                raise PositionNotFoundError(position_id=position_id)
            profile.portfolio.remove_position(position_id)

    def update_position_price(
        self, portfolio_id: str, position_id: str, price: float
    ) -> Position:
        profile = self.get_profile(portfolio_id)
        with self._lock:
            pos = profile.portfolio.get_position(position_id)
            if pos is None:
                raise PositionNotFoundError(position_id=position_id)
            pos.update_price(price)
            profile.portfolio.recompute_weights()
            return pos

    def update_cash(self, portfolio_id: str, amount: float) -> None:
        profile = self.get_profile(portfolio_id)
        with self._lock:
            profile.portfolio.update_cash(amount)

    # ── analysis pipeline ─────────────────────────────────────────────────────

    def analyze(
        self,
        portfolio_id: str,
        *,
        request_id:   str = "",
        **metadata: Any,
    ) -> PortfolioIntelligence:
        t0 = time.time()
        self._stats.analyses_total += 1

        profile   = self.get_profile(portfolio_id)
        portfolio = profile.portfolio

        # 1 – Drawdown
        drawdown = self._drawdown.analyze(portfolio, profile.peak_nav)
        if portfolio.total_nav > profile.peak_nav:
            profile.peak_nav = portfolio.total_nav

        # 2 – Exposure
        exposure = self._exposure.analyze(portfolio)

        # 3 – Allocation
        alloc_report = self._allocation.analyze(portfolio)

        # 4 – Full analytics
        analytics = self._analyzer.analyze(portfolio, drawdown, exposure, alloc_report)

        # 5 – Risk
        nav      = portfolio.total_nav
        cash_pct = portfolio.cash / nav if nav > 0 else 1.0
        risk_profile = self._risk.analyze(
            portfolio,
            drawdown,
            hhi                 = analytics.hhi,
            top_position_weight = analytics.top1_weight,
            cash_pct            = cash_pct,
        )

        # 6 – Build PortfolioIntelligence
        health_score = self._composite_health(analytics, risk_profile.overall_risk_score)
        intel = PortfolioIntelligence(
            portfolio_id         = portfolio_id,
            portfolio_name       = portfolio.name,
            request_id           = request_id,
            health_score         = health_score,
            risk_score           = risk_profile.overall_risk_score,
            diversification_score = analytics.diversification_score,
            concentration_score  = analytics.concentration_score,
            liquidity_score      = analytics.liquidity_score,
            performance_score    = analytics.performance_score,
            allocation_score     = analytics.allocation_score,
            health_status        = PortfolioIntelligence.classify_health(health_score),
            risk_level           = risk_profile.risk_level,
            risk_profile         = risk_profile,
            drawdown             = drawdown,
            exposure_report      = exposure,
            confidence           = min(1.0, 0.5 + portfolio.position_count * 0.02),
            metadata             = dict(metadata),
        )

        # 7 – Generate narrative
        self._generate_intelligence(intel, analytics, drawdown, exposure, risk_profile)

        # 8 – Snapshot + history
        snap = self._build_snapshot(portfolio, intel)
        profile.update_snapshot(snap)
        self._history_store.add(portfolio_id, snap)

        # 9 – Track stats
        duration_ms = (time.time() - t0) * 1_000
        intel.duration_ms = round(duration_ms, 2)

        with self._lock:
            self._latest[portfolio_id] = intel
            self._recent.append(intel)
            self._stats.analyses_successful += 1
            self._total_duration_ms += duration_ms
            total = self._stats.analyses_successful + self._stats.analyses_failed
            if total > 0:
                self._stats.avg_duration_ms = self._total_duration_ms / total

        return intel

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest(self, portfolio_id: str) -> PortfolioIntelligence:
        with self._lock:
            if portfolio_id not in self._latest:
                raise PortfolioNotFoundError(
                    f"No intelligence found for: {portfolio_id}",
                    portfolio_id=portfolio_id,
                )
            return self._latest[portfolio_id]

    def recent(self, n: int = 10) -> list[PortfolioIntelligence]:
        with self._lock:
            items = list(self._recent)
            return items[-n:] if len(items) >= n else items

    def summary(self, portfolio_id: str) -> PortfolioSnapshot:
        snap = self._history_store.get_latest(portfolio_id)
        if snap is None:
            raise PortfolioNotFoundError(
                f"No snapshot found for: {portfolio_id}",
                portfolio_id=portfolio_id,
            )
        return snap

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats.to_dict()

    def stats_object(self) -> PortfolioStatistics:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _composite_health(analytics: Any, risk_score: float) -> float:
        return round(
            (100 - risk_score)           * 0.30
            + analytics.diversification_score * 0.25
            + analytics.concentration_score   * 0.20
            + analytics.liquidity_score       * 0.15
            + analytics.performance_score     * 0.10,
            2,
        )

    @staticmethod
    def _generate_intelligence(
        intel:        PortfolioIntelligence,
        analytics:    Any,
        drawdown:     Any,
        exposure:     Any,
        risk_profile: Any,
    ) -> None:
        # Observations
        intel.add_observation(f"Portfolio risk level: {risk_profile.risk_level.value}")
        intel.add_observation(
            f"Diversification: {analytics.diversification_score:.0f}/100 "
            f"(HHI={analytics.hhi:.3f})"
        )
        if analytics.top1_weight > 0:
            intel.add_observation(
                f"Largest position weight: {analytics.top1_weight:.1%}"
            )

        # Warnings from risk profile
        for w in risk_profile.risk_warnings:
            intel.add_warning(w)

        # Exposure limit breaches
        for breach in exposure.limit_breaches:
            intel.add_warning(breach)

        # Drawdown
        if drawdown.is_in_drawdown:
            intel.add_warning(
                f"Portfolio in drawdown: {drawdown.current_drawdown_pct:.1%} "
                f"({drawdown.drawdown_severity.value})"
            )
            intel.add_risk_factor(
                f"Current drawdown {drawdown.current_drawdown_pct:.1%} requires "
                f"{drawdown.recovery_required_pct:.1%} recovery"
            )

        # Recommendations
        if analytics.liquidity_score < 40:
            intel.add_recommendation("Increase cash reserves to improve liquidity buffer")
        if analytics.diversification_score < 40:
            intel.add_recommendation("Add more positions to improve diversification")
        if analytics.concentration_score < 30:
            intel.add_recommendation("Reduce largest position to below 25% of NAV")

    @staticmethod
    def _build_snapshot(portfolio: Portfolio, intel: PortfolioIntelligence) -> PortfolioSnapshot:
        nav      = portfolio.total_nav
        cash_pct = portfolio.cash / nav if nav > 0 else 1.0
        return PortfolioSnapshot(
            portfolio_id          = portfolio.portfolio_id,
            total_nav             = nav,
            cash                  = portfolio.cash,
            invested_value        = portfolio.invested_value,
            cash_pct              = round(cash_pct, 6),
            unrealized_pnl        = portfolio.unrealized_pnl,
            unrealized_pnl_pct    = portfolio.unrealized_pnl_pct,
            position_count        = portfolio.position_count,
            health_score          = intel.health_score,
            risk_score            = intel.risk_score,
            diversification_score = intel.diversification_score,
            concentration_score   = intel.concentration_score,
            liquidity_score       = intel.liquidity_score,
            performance_score     = intel.performance_score,
            top_position_weight   = intel.drawdown.current_drawdown_pct if intel.drawdown else 0.0,
            drawdown_pct          = intel.drawdown.current_drawdown_pct if intel.drawdown else 0.0,
            drawdown_severity     = intel.drawdown.drawdown_severity if intel.drawdown else DrawdownSeverity.NONE,
            risk_level            = intel.risk_level,
            health_status         = intel.health_status,
        )


# ── module-level singleton ────────────────────────────────────────────────────

_manager_lock:     threading.Lock          = threading.Lock()
_manager_instance: PortfolioManager | None = None


def get_portfolio_manager() -> PortfolioManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = PortfolioManager()
        return _manager_instance


def reset_portfolio_manager() -> None:
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
