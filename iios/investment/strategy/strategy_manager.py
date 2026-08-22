"""iios/investment/strategy/strategy_manager.py
Orchestrates all strategy intelligence operations.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import (
    DEFAULT_HISTORY_SIZE,
    RegimeCompatibility,
    StrategyCategory,
    StrategyGrade,
    StrategyRecommendation,
    StrategyStatus,
)
from iios.investment.strategy.strategy_exceptions import (
    StrategyNotFoundError,
)
from iios.investment.strategy.strategy_factory import StrategyFactory
from iios.investment.strategy.strategy_intelligence import StrategyIntelligence
from iios.investment.strategy.strategy_registry import StrategyRegistry, get_strategy_registry
from iios.investment.strategy.core.strategy_definition import StrategyDefinition
from iios.investment.strategy.core.strategy_history import StrategyHistory
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot
from iios.investment.strategy.evaluation.strategy_evaluator import StrategyEvaluator
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.adaptation.adaptation_engine import AdaptationEngine
from iios.investment.strategy.adaptation.adaptation_result import AdaptationResult
from iios.investment.strategy.lifecycle.lifecycle_history import LifecycleHistoryEntry
from iios.investment.strategy.lifecycle.lifecycle_manager import LifecycleManager
from iios.investment.strategy.performance.performance_record import PerformanceRecord
from iios.investment.strategy.performance.performance_tracker import (
    PerformanceTracker,
    StrategyStatistics,
)
from iios.investment.strategy.selection.strategy_selector import StrategySelector


@dataclass
class StrategyManagerStatistics:
    strategies_registered: int   = 0
    analyses_total:        int   = 0
    analyses_successful:   int   = 0
    analyses_failed:       int   = 0
    avg_duration_ms:       float = 0.0
    uptime_sec:            float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategies_registered": self.strategies_registered,
            "analyses_total":        self.analyses_total,
            "analyses_successful":   self.analyses_successful,
            "analyses_failed":       self.analyses_failed,
            "avg_duration_ms":       round(self.avg_duration_ms, 2),
            "uptime_sec":            round(self.uptime_sec, 2),
        }


class StrategyManager:
    """
    Central orchestrator for the Strategy Intelligence Engine.

    Manages:
    - Strategy profile CRUD
    - Evaluation and scoring
    - Lifecycle transitions
    - Performance record ingestion
    - Adaptation proposals
    - Intelligence production
    - Strategy selection
    """

    def __init__(
        self,
        registry:         StrategyRegistry    | None = None,
        evaluator:        StrategyEvaluator   | None = None,
        selector:         StrategySelector    | None = None,
        adaptation_engine: AdaptationEngine   | None = None,
        tracker:          PerformanceTracker  | None = None,
        history_store:    StrategyHistory     | None = None,
        max_recent:       int                 = DEFAULT_HISTORY_SIZE,
    ) -> None:
        self._lock         = threading.RLock()
        self._registry     = registry         or get_strategy_registry()
        self._evaluator    = evaluator        or StrategyEvaluator()
        self._selector     = selector         or StrategySelector()
        self._adaptation   = adaptation_engine or AdaptationEngine()
        self._tracker      = tracker          or PerformanceTracker()
        self._history      = history_store    or StrategyHistory()

        self._profiles:    dict[str, StrategyProfile]     = {}
        self._latest_intel: dict[str, StrategyIntelligence] = {}
        self._recent:      deque[StrategyIntelligence]    = deque(maxlen=max_recent)

        # Shared profile dict for lifecycle manager
        self._lifecycle    = LifecycleManager(profiles=self._profiles)

        self._stats        = StrategyManagerStatistics()
        self._started_at   = time.time()
        self._total_dur_ms = 0.0

    # ── registration ─────────────────────────────────────────────────────────

    def register_strategy(
        self,
        definition: StrategyDefinition,
        metadata:   dict[str, Any] | None = None,
    ) -> StrategyProfile:
        """Register a new strategy definition and return its profile."""
        with self._lock:
            sid = definition.strategy_id
            if self._registry.is_registered(sid):
                return self._profiles[sid]   # idempotent

            self._registry.register(definition)
            profile = StrategyFactory.make_profile(definition)
            self._profiles[sid] = profile
            self._lifecycle.register_profile(profile)
            self._stats.strategies_registered = len(self._profiles)
            return profile

    def get_profile(self, strategy_id: str) -> StrategyProfile:
        with self._lock:
            if strategy_id not in self._profiles:
                raise StrategyNotFoundError(
                    f"Strategy profile not found: {strategy_id}",
                    strategy_id=strategy_id,
                )
            return self._profiles[strategy_id]

    # ── analysis ─────────────────────────────────────────────────────────────

    def analyze(
        self,
        strategy_id:    str,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]          | None = None,
        request_id:     str                     = "",
        **metadata: Any,
    ) -> StrategyIntelligence:
        """Produce a StrategyIntelligence report for a strategy."""
        t0 = time.time()
        self._stats.analyses_total += 1

        # Auto-register fallback (the engine handles this at facade level)
        if strategy_id not in self._profiles:
            raise StrategyNotFoundError(
                f"Strategy not found: {strategy_id}",
                strategy_id=strategy_id,
            )

        profile = self._profiles[strategy_id]
        records = records if records is not None else self._tracker.get_records(strategy_id)

        # Evaluate
        score = self._evaluator.evaluate(profile, records, market_context)
        stats = self._tracker.get_stats(strategy_id)

        # Regime compatibility
        regime_compat = self._selector.regime_compatibility(profile, market_context or {})

        # Compile intelligence
        intel = StrategyIntelligence(
            strategy_id          = strategy_id,
            strategy_name        = profile.definition.name,
            version              = profile.current_version,
            request_id           = request_id,
            category             = profile.definition.category,
            status               = profile.lifecycle_status,
            score                = score,
            statistics           = stats,
            regime_compatibility = regime_compat,
            preferred_regimes    = [r.value for r in profile.definition.preferred_regimes],
            active_regime        = (market_context or {}).get("regime", ""),
            recommendation       = score.recommendation,
            grade                = score.grade,
            confidence           = score.confidence_score / 100.0,
            metadata             = dict(metadata),
        )

        # Generate intelligence observations
        self._enrich_intelligence(intel, score, stats, profile)

        # Build & store snapshot
        snap = StrategySnapshot(
            strategy_id   = strategy_id,
            status        = profile.lifecycle_status,
            win_rate      = stats.win_rate,
            sharpe_ratio  = stats.sharpe_ratio,
            max_drawdown  = stats.max_drawdown,
            avg_return    = stats.avg_return,
            profit_factor = stats.profit_factor,
            total_trades  = stats.total_trades,
            overall_score = score.overall_score,
            grade         = score.grade,
            recommendation = score.recommendation,
            active_params = dict(profile.active_params),
        )
        profile.update_snapshot(snap)
        self._history.add(strategy_id, snap)

        duration_ms = (time.time() - t0) * 1_000
        intel.duration_ms = round(duration_ms, 2)

        with self._lock:
            self._latest_intel[strategy_id] = intel
            self._recent.append(intel)
            self._stats.analyses_successful += 1
            total = self._stats.analyses_successful + self._stats.analyses_failed
            if total > 0:
                self._total_dur_ms += duration_ms
                self._stats.avg_duration_ms = self._total_dur_ms / total

        return intel

    # ── evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        strategy_id:    str,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]          | None = None,
    ) -> StrategyScore:
        profile = self.get_profile(strategy_id)
        records = records if records is not None else self._tracker.get_records(strategy_id)
        return self._evaluator.evaluate(profile, records, market_context)

    # ── selection ─────────────────────────────────────────────────────────────

    def select(
        self,
        market_context:  dict[str, Any] | None = None,
        n:               int             = 5,
        min_score:       float           = 40.0,
        require_regime_compat: bool      = False,
    ) -> list[StrategyScore]:
        with self._lock:
            profiles = list(self._profiles.values())
        return self._selector.select(
            profiles        = profiles,
            records_map     = {sid: self._tracker.get_records(sid) for sid in self._profiles},
            market_context  = market_context or {},
            n               = n,
            min_score       = min_score,
            require_regime_compat = require_regime_compat,
        )

    # ── adaptation ────────────────────────────────────────────────────────────

    def adapt(
        self,
        strategy_id:    str,
        market_context: dict[str, Any]          | None = None,
        apply:          bool                    = False,
    ) -> AdaptationResult:
        profile = self.get_profile(strategy_id)
        stats   = self._tracker.get_stats(strategy_id)
        score   = self.evaluate(strategy_id, market_context=market_context)

        result = self._adaptation.adapt(
            profile        = profile,
            market_context = market_context or {},
            stats          = stats,
            score          = score,
        )

        if apply and result.has_changes:
            profile.update_params(result.adapted_params)
            result.applied = True

        return result

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def transition(
        self,
        strategy_id: str,
        to_status:   StrategyStatus,
        reason:      str = "",
        actor:       str = "system",
    ) -> bool:
        return self._lifecycle.transition(strategy_id, to_status, reason, actor)

    def is_valid_transition(
        self,
        from_status: StrategyStatus,
        to_status:   StrategyStatus,
    ) -> bool:
        return self._lifecycle.is_valid_transition(from_status, to_status)

    def get_lifecycle_history(
        self,
        strategy_id: str,
        n: int = 20,
    ) -> list[LifecycleHistoryEntry]:
        return self._lifecycle.get_history(strategy_id, n)

    # ── performance records ───────────────────────────────────────────────────

    def add_performance_record(
        self,
        strategy_id: str,
        record:      PerformanceRecord,
    ) -> None:
        self._tracker.add_record(strategy_id, record)

    def get_performance_stats(self, strategy_id: str) -> StrategyStatistics:
        return self._tracker.get_stats(strategy_id)

    # ── retrieval ─────────────────────────────────────────────────────────────

    def get_latest_intelligence(self, strategy_id: str) -> StrategyIntelligence:
        with self._lock:
            if strategy_id not in self._latest_intel:
                raise StrategyNotFoundError(
                    f"No intelligence found for: {strategy_id}",
                    strategy_id=strategy_id,
                )
            return self._latest_intel[strategy_id]

    def recent(self, n: int = 10) -> list[StrategyIntelligence]:
        with self._lock:
            items = list(self._recent)
            return items[-n:] if len(items) >= n else items

    def all_strategy_ids(self) -> list[str]:
        with self._lock:
            return list(self._profiles.keys())

    # ── statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats.to_dict()

    def stats_object(self) -> StrategyManagerStatistics:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats

    # ── internal enrichment ───────────────────────────────────────────────────

    @staticmethod
    def _enrich_intelligence(
        intel:   StrategyIntelligence,
        score:   StrategyScore,
        stats:   StrategyStatistics,
        profile: StrategyProfile,
    ) -> None:
        # Strengths
        if score.win_rate >= 0.55:
            intel.add_strength(f"High win rate ({score.win_rate:.1%})")
        if score.sharpe_ratio >= 1.0:
            intel.add_strength(f"Strong Sharpe ratio ({score.sharpe_ratio:.2f})")
        if score.max_drawdown <= 0.10:
            intel.add_strength(f"Low max drawdown ({score.max_drawdown:.1%})")
        if score.overall_score >= 75:
            intel.add_strength("Above-average composite score")

        # Weaknesses
        if stats.has_enough_data and score.win_rate < 0.45:
            intel.add_weakness(f"Below-threshold win rate ({score.win_rate:.1%})")
        if score.max_drawdown > 0.20:
            intel.add_weakness(f"High max drawdown ({score.max_drawdown:.1%})")
        if score.sharpe_ratio < 0.5 and stats.has_enough_data:
            intel.add_weakness(f"Low Sharpe ratio ({score.sharpe_ratio:.2f})")
        if not stats.has_enough_data:
            intel.add_weakness(
                f"Insufficient performance data ({stats.total_trades} trades, "
                f"minimum {profile.definition.min_trades_required})"
            )

        # Opportunities
        if intel.regime_compatibility in (RegimeCompatibility.OPTIMAL, RegimeCompatibility.COMPATIBLE):
            intel.add_opportunity("Strategy is compatible with current market regime")
        if score.profit_factor >= 1.5:
            intel.add_opportunity(f"Strong profit factor ({score.profit_factor:.2f})")

        # Risks
        if intel.regime_compatibility == RegimeCompatibility.INCOMPATIBLE:
            intel.add_risk("Strategy is NOT compatible with current market regime")
        if profile.lifecycle_status == StrategyStatus.SUSPENDED:
            intel.add_risk("Strategy is currently suspended")

        # Observations
        intel.add_observation(
            f"Status: {profile.lifecycle_status.value} | "
            f"Score: {score.overall_score:.1f} | "
            f"Grade: {score.grade.value}"
        )
        intel.add_observation(
            f"Trades: {stats.total_trades} | "
            f"Win rate: {stats.win_rate:.1%} | "
            f"Sharpe: {stats.sharpe_ratio:.2f}"
        )


# ── module-level singleton ────────────────────────────────────────────────────

_manager_lock:     threading.Lock           = threading.Lock()
_manager_instance: StrategyManager | None  = None


def get_strategy_manager() -> StrategyManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = StrategyManager()
        return _manager_instance


def reset_strategy_manager() -> None:
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
