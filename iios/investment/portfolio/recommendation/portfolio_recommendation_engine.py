"""iios/investment/portfolio/recommendation/portfolio_recommendation_engine.py

Portfolio Recommendation Engine — main orchestrator.

Responsibilities:
  - Receive complete portfolio intelligence from all upstream engines
  - Evaluate institutional recommendation policies against that intelligence
  - Generate deterministic, auditable PortfolioRecommendation objects
  - Manage recommendation lifecycle
  - Maintain per-portfolio history and query APIs
  - Publish recommendation events

This engine does NOT execute trades.
This engine does NOT independently analyze markets, companies, or strategies.
"""
from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    PortfolioRecommendation, RecommendationCandidate, build_recommendation,
)
from iios.investment.portfolio.recommendation.recommendation_confidence import (
    calculate_confidence, intelligence_quality_score,
)
from iios.investment.portfolio.recommendation.recommendation_expiration import (
    compute_expires_at,
)
from iios.investment.portfolio.recommendation.recommendation_health import (
    RecommendationHealthMonitor, RecommendationHealthReport,
)
from iios.investment.portfolio.recommendation.recommendation_history import (
    PortfolioRecommendationHistory,
)
from iios.investment.portfolio.recommendation.recommendation_lifecycle import (
    LifecycleManager,
)
from iios.investment.portfolio.recommendation.recommendation_logic import (
    RecommendationLogic,
)
from iios.investment.portfolio.recommendation.recommendation_monitor import (
    RecommendationMonitor, RecommendationMonitorReport,
)
from iios.investment.portfolio.recommendation.recommendation_policies import (
    InstitutionalPolicy,
)
from iios.investment.portfolio.recommendation.recommendation_quality import (
    RecommendationQualityAssessor, RecommendationQualityReport,
)
from iios.investment.portfolio.recommendation.recommendation_registry import (
    RecommendationPolicyRegistry,
)
from iios.investment.portfolio.recommendation.recommendation_score import (
    RecommendationScore, RecommendationScoreCalculator,
)
from iios.investment.portfolio.recommendation.recommendation_snapshot import (
    RecommendationHistory, RecommendationRecord,
)
from iios.investment.portfolio.recommendation.recommendation_statistics import (
    PortfolioRecommendationStatistics, RecommendationRunMetric,
    RecommendationStatisticsSnapshot,
)
from iios.investment.portfolio.recommendation.recommendation_tracker import (
    RecommendationTracker,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState, PortfolioIntelligence, RecommendationAction,
    RecommendationStatus, intelligence_from_any, now_utc,
    priority_to_expiry_hours,
)
from iios.investment.portfolio.recommendation.recommendation_validator import (
    RecValidationReport, RecommendationValidator,
)


class PortfolioRecommendationEngine:
    """
    Institutional Portfolio Recommendation Engine.

    Transforms completed portfolio intelligence from all upstream engines
    into deterministic, explainable, auditable portfolio recommendations.

    Input:   PortfolioIntelligence (aggregated from 8 upstream engines)
    Output:  List[PortfolioRecommendation] (primary output type)

    Does NOT execute trades.
    Does NOT independently analyze markets, companies, or strategies.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        *,
        policy_registry:    Optional[RecommendationPolicyRegistry] = None,
        logic:              Optional[RecommendationLogic]           = None,
        scorer:             Optional[RecommendationScoreCalculator] = None,
        validator:          Optional[RecommendationValidator]       = None,
        quality_assessor:   Optional[RecommendationQualityAssessor] = None,
        lifecycle_manager:  Optional[LifecycleManager]             = None,
        tracker:            Optional[RecommendationTracker]         = None,
        monitor:            Optional[RecommendationMonitor]         = None,
        health_monitor:     Optional[RecommendationHealthMonitor]   = None,
        max_history:        int = 50,
        event_callback:     Optional[Callable[[str, Any], None]] = None,
    ) -> None:
        self._registry   = policy_registry  or RecommendationPolicyRegistry()
        self._logic      = logic            or RecommendationLogic()
        self._scorer     = scorer           or RecommendationScoreCalculator()
        self._validator  = validator        or RecommendationValidator()
        self._assessor   = quality_assessor or RecommendationQualityAssessor()
        self._lifecycle  = lifecycle_manager or LifecycleManager()
        self._tracker    = tracker          or RecommendationTracker()
        self._monitor    = monitor          or RecommendationMonitor()
        self._health     = health_monitor   or RecommendationHealthMonitor()
        self._max_hist   = max_history
        self._callback   = event_callback

        self._lock       = threading.RLock()
        self._running    = False
        self._portfolios: Dict[str, RecommendationHistory] = {}
        self._history    = PortfolioRecommendationHistory(max_per_portfolio=max_history)
        self._statistics = PortfolioRecommendationStatistics()
        self._integrations: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        with self._lock:
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ------------------------------------------------------------------ #
    # Integration references (read-only metadata; never called)
    # ------------------------------------------------------------------ #

    def configure_integrations(self, refs: Dict[str, Any]) -> None:
        self._integrations = refs

    # ------------------------------------------------------------------ #
    # Portfolio registry
    # ------------------------------------------------------------------ #

    def register_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            if portfolio_id not in self._portfolios:
                self._portfolios[portfolio_id] = RecommendationHistory(portfolio_id)

    def deregister_portfolio(self, portfolio_id: str) -> None:
        with self._lock:
            self._portfolios.pop(portfolio_id, None)
        self._tracker.expire_all(portfolio_id)

    def is_registered(self, portfolio_id: str) -> bool:
        with self._lock:
            return portfolio_id in self._portfolios

    # ------------------------------------------------------------------ #
    # Core evaluation
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        portfolio_id:  str,
        intelligence:  Any,   # PortfolioIntelligence or duck-typed / dict
        *,
        policy_id:     Optional[str] = None,
        auto_register: bool = True,
    ) -> List[PortfolioRecommendation]:
        """
        Generate portfolio recommendations from intelligence.

        Parameters
        ----------
        portfolio_id  : Unique portfolio identifier.
        intelligence  : PortfolioIntelligence (or dict / duck-typed).
        policy_id     : Policy to apply; uses registry default if None.
        auto_register : Register portfolio_id if not already registered.

        Returns
        -------
        List[PortfolioRecommendation] — frozen, deterministic, fully traceable.
        """
        t0 = time.monotonic()
        if auto_register:
            self.register_portfolio(portfolio_id)

        intel  = intelligence_from_any(intelligence)
        policy = self._registry.get_or_default(policy_id)

        succeeded = False
        recs: List[PortfolioRecommendation] = []

        try:
            recs = self._build_recommendations(intel, policy, portfolio_id)
            succeeded = True
        except Exception:
            recs = [self._fallback_recommendation(portfolio_id, policy)]
        finally:
            dur_ms = (time.monotonic() - t0) * 1000
            n_recs = len(recs)
            n_act  = sum(1 for r in recs if r.is_actionable)
            metric = RecommendationRunMetric(
                portfolio_id         = portfolio_id,
                succeeded            = succeeded,
                duration_ms          = dur_ms,
                n_recommendations    = n_recs,
                n_actionable         = n_act,
                recommendation_score = recs[0].recommendation_score if recs else 0.0,
                primary_action       = recs[0].action.value if recs else "no_action",
            )
            self._statistics.record(metric)
            self._health.record_run(succeeded, dur_ms, n_recs)

            for rec in recs:
                self._tracker.add(portfolio_id, rec)
                record = self._build_record(rec)
                with self._lock:
                    if portfolio_id in self._portfolios:
                        self._portfolios[portfolio_id].add(record)
                self._history.add(portfolio_id, rec)

            if self._callback and recs:
                for rec in recs:
                    self._callback("recommendation_published", rec)

        return recs

    # ------------------------------------------------------------------ #
    # Query APIs
    # ------------------------------------------------------------------ #

    def current_recommendations(self, portfolio_id: str) -> List[PortfolioRecommendation]:
        """Return active (non-expired) recommendations for a portfolio."""
        return self._tracker.get_active(portfolio_id)

    def latest_recommendation(self, portfolio_id: str) -> Optional[PortfolioRecommendation]:
        return self._history.latest(portfolio_id)

    def recommendation_history(
        self,
        portfolio_id: str,
        n: int = 5,
    ) -> List[PortfolioRecommendation]:
        return self._history.recent(portfolio_id, n)

    def best_recommendation(self, portfolio_id: str) -> Optional[PortfolioRecommendation]:
        return self._history.best(portfolio_id)

    def statistics_snapshot(self) -> RecommendationStatisticsSnapshot:
        return self._statistics.snapshot()

    def health(self) -> RecommendationHealthReport:
        n_active = len(self._portfolios)
        return self._health.check(n_active)

    def monitor_active(self) -> RecommendationMonitorReport:
        """Monitor the health of currently active recommendations."""
        active_map = {
            pid: self._tracker.get_active(pid)
            for pid in self._tracker.all_portfolio_ids()
        }
        return self._monitor.check(active_map)

    def search_recommendations(
        self,
        portfolio_id: Optional[str] = None,
        action:       Optional[RecommendationAction] = None,
        n:            int = 20,
    ) -> List[PortfolioRecommendation]:
        """Search recent recommendations with optional filters."""
        results = []
        pids = [portfolio_id] if portfolio_id else self._history.all_portfolio_ids()
        for pid in pids:
            recent = self._history.recent(pid, n)
            for rec in recent:
                if action is None or getattr(rec, "action", None) == action:
                    results.append(rec)
        return results[-n:]

    def validate_recommendation(
        self,
        rec:          PortfolioRecommendation,
        intelligence: PortfolioIntelligence,
        policy_id:    Optional[str] = None,
    ) -> RecValidationReport:
        policy = self._registry.get_or_default(policy_id)
        return self._validator.validate(rec, policy, intelligence)

    def assess_quality(
        self,
        rec: PortfolioRecommendation,
    ) -> RecommendationQualityReport:
        return self._assessor.assess(
            overall_score    = rec.recommendation_score,
            confidence       = rec.confidence,
            requires_approval= rec.requires_approval,
            portfolio_id     = rec.portfolio_id,
        )

    # ------------------------------------------------------------------ #
    # Internal builders
    # ------------------------------------------------------------------ #

    def _build_recommendations(
        self,
        intel:        PortfolioIntelligence,
        policy:       InstitutionalPolicy,
        portfolio_id: str,
    ) -> List[PortfolioRecommendation]:
        params  = policy.parameters
        iq      = intelligence_quality_score(intel)
        created_at = now_utc()

        # Generate candidates from logic layer
        candidates = self._logic.generate(intel, policy)

        recs: List[PortfolioRecommendation] = []
        for candidate in candidates:
            # Skip if below confidence threshold
            final_conf = calculate_confidence(
                base_confidence      = candidate.confidence,
                n_evidence           = len(candidate.evidence),
                signal_confidence    = intel.signal_confidence,
                intelligence_quality = iq,
                priority             = candidate.priority,
            )
            if final_conf < params.min_confidence_to_publish:
                continue

            # Score
            score = self._scorer.calculate(
                confidence           = final_conf,
                n_evidence           = len(candidate.evidence),
                priority             = candidate.priority,
                intelligence_quality = iq,
                portfolio_id         = portfolio_id,
            )

            # Expiry
            expires_at  = compute_expires_at(candidate.priority, params, created_at)
            expiry_hours = priority_to_expiry_hours(
                candidate.priority,
                params.critical_expiry_hours,
                params.high_expiry_hours,
                params.default_expiry_hours,
                params.low_expiry_hours,
                params.no_action_expiry_hours,
            )

            # Requires approval?
            req_approval = (
                params.require_approval_for_high_risk
                and candidate.risk_level.value == "high"
            )
            is_time_sensitive = candidate.priority.value in ("immediate", "high")

            # Build recommendation
            rec = build_recommendation(
                candidate         = candidate,
                portfolio_id      = portfolio_id,
                policy_id         = policy.policy_id,
                policy_name       = policy.name,
                intelligence_id   = intel.intelligence_id,
                score             = score.overall,
                expires_at        = expires_at,
                expiry_hours      = expiry_hours,
                requires_approval = req_approval,
                is_time_sensitive = is_time_sensitive,
            )

            # Transition to PUBLISHED
            try:
                rec = self._lifecycle.publish(rec)
            except ValueError:
                pass   # already published or state issue

            recs.append(rec)

        # If nothing publishable, ensure NO_ACTION
        if not recs:
            fallback_candidate = RecommendationCandidate(
                action         = RecommendationAction.NO_ACTION,
                priority       = __import__(
                    "iios.investment.portfolio.recommendation.recommendation_types",
                    fromlist=["RecommendationPriority"],
                ).RecommendationPriority.INFORMATIONAL,
                confidence     = 0.95,
                rationale      = "Portfolio is within all institutional policy thresholds",
                evidence       = (),
                triggered_rule = "no_trigger",
                risk_level     = __import__(
                    "iios.investment.portfolio.recommendation.recommendation_types",
                    fromlist=["RecommendationRisk"],
                ).RecommendationRisk.MINIMAL,
                tags           = ("governance",),
            )
            recs.append(self._build_single_rec(
                fallback_candidate, intel, policy, portfolio_id, created_at, iq, params
            ))

        return recs

    def _build_single_rec(
        self,
        candidate:    RecommendationCandidate,
        intel:        PortfolioIntelligence,
        policy:       InstitutionalPolicy,
        portfolio_id: str,
        created_at:   str,
        iq:           float,
        params:       Any,
    ) -> PortfolioRecommendation:
        """Helper: score, build, and publish a single candidate."""
        final_conf = calculate_confidence(
            candidate.confidence, len(candidate.evidence),
            intel.signal_confidence, iq, candidate.priority,
        )
        score = self._scorer.calculate(
            final_conf, len(candidate.evidence), candidate.priority, iq, portfolio_id
        )
        expires_at   = compute_expires_at(candidate.priority, params, created_at)
        expiry_hours = priority_to_expiry_hours(
            candidate.priority,
            params.critical_expiry_hours, params.high_expiry_hours,
            params.default_expiry_hours, params.low_expiry_hours, params.no_action_expiry_hours,
        )
        rec = build_recommendation(
            candidate         = candidate,
            portfolio_id      = portfolio_id,
            policy_id         = policy.policy_id,
            policy_name       = policy.name,
            intelligence_id   = intel.intelligence_id,
            score             = score.overall,
            expires_at        = expires_at,
            expiry_hours      = expiry_hours,
            requires_approval = False,
            is_time_sensitive = False,
        )
        try:
            rec = self._lifecycle.publish(rec)
        except ValueError:
            pass
        return rec

    @staticmethod
    def _fallback_recommendation(
        portfolio_id: str,
        policy:       InstitutionalPolicy,
    ) -> PortfolioRecommendation:
        """Return a safe NO_ACTION recommendation when evaluation fails."""
        from iios.investment.portfolio.recommendation.recommendation_types import (
            RecommendationPriority, RecommendationRisk,
        )
        return PortfolioRecommendation(
            portfolio_id        = portfolio_id,
            action              = RecommendationAction.NO_ACTION,
            priority            = RecommendationPriority.INFORMATIONAL,
            confidence          = 0.50,
            risk_level          = RecommendationRisk.MINIMAL,
            status              = RecommendationStatus.DRAFT,
            lifecycle_state     = LifecycleState.CREATED,
            rationale           = "Engine evaluation error — defaulting to NO_ACTION",
            policy_id           = policy.policy_id,
            policy_name         = policy.name,
            recommendation_score= 0.0,
            is_actionable       = False,
        )

    @staticmethod
    def _build_record(rec: PortfolioRecommendation) -> RecommendationRecord:
        return RecommendationRecord(
            recommendation_id  = rec.recommendation_id,
            portfolio_id       = rec.portfolio_id,
            action             = rec.action,
            priority           = rec.priority,
            status             = rec.status,
            lifecycle_state    = rec.lifecycle_state,
            confidence         = rec.confidence,
            recommendation_score = rec.recommendation_score,
            grade              = rec.grade,
            is_actionable      = rec.is_actionable,
            requires_approval  = rec.requires_approval,
            category           = rec.category,
            policy_id          = rec.policy_id,
            expires_at         = rec.expires_at,
        )
