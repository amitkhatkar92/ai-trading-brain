"""iios/investment/strategy/learning/strategy_learning_engine.py
StrategyLearningEngine — main facade for the Institutional Strategy Learning Engine.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_policy import LearningPolicy, DEFAULT_POLICY
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_history import ObservationStore, LearningSnapshotStore
from iios.investment.strategy.learning.learning_snapshot import LearningSnapshot
from iios.investment.strategy.learning.learning_events import LearningEventBus, LearningEvent, LearningEventType
from iios.investment.strategy.learning.learning_score import LearningScore, LearningScoreCalculator
from iios.investment.strategy.learning.drift_detector import DriftDetector, DriftSignal
from iios.investment.strategy.learning.degradation_detector import DegradationDetector, DegradationReport
from iios.investment.strategy.learning.performance_monitor import StrategyPerformanceMonitor
from iios.investment.strategy.learning.performance_learning import PerformanceLearner, PerformanceLearningResult
from iios.investment.strategy.learning.adaptation_engine import AdaptationEngine, AdaptationReport
from iios.investment.strategy.learning.knowledge_engine import KnowledgeEngine, KnowledgeReport
from iios.investment.strategy.learning.lesson_registry import Lesson, LessonRegistry, LessonCategory
from iios.investment.strategy.learning.recommendation_engine import Recommendation, RecommendationEngine
from iios.investment.strategy.learning.improvement_engine import ImprovementSuggestion
from iios.investment.strategy.learning.strategy_maturity import StrategyMaturity, MaturityAssessor
from iios.investment.strategy.learning.learning_confidence import LearningConfidence
from iios.investment.strategy.learning.learning_quality import LearningQuality


class StrategyLearningEngine:
    """
    Main facade for the Institutional Strategy Learning Engine.
    Observe → Learn → Explain → Recommend → Preserve.
    
    Constraints enforced by design:
    - Never modifies strategies automatically.
    - Never retrains ML models.
    - Never generates Buy/Sell/Hold decisions.
    - All recommendations are explainable, auditable, versioned, reversible.
    """

    def __init__(
        self,
        policy:      LearningPolicy = DEFAULT_POLICY,
        event_bus:   Optional[LearningEventBus] = None,
        max_workers: int = 4,
    ) -> None:
        self._policy      = policy
        self._event_bus   = event_bus or LearningEventBus()
        self._max_workers = max_workers
        self._lock        = threading.RLock()

        # Per-strategy state
        self._profiles:      Dict[str, StrategyLearningProfile] = {}
        self._obs_store      = ObservationStore(max_per_strategy=2000)
        self._snap_store     = LearningSnapshotStore(max_per_strategy=2000)

        # Cached analytics (invalidated on each observe)
        self._scores:        Dict[str, LearningScore]        = {}
        self._degradations:  Dict[str, DegradationReport]   = {}
        self._adaptations:   Dict[str, AdaptationReport]    = {}
        self._recs:          Dict[str, List[Recommendation]] = {}
        self._knowledge:     Dict[str, KnowledgeReport]     = {}
        self._maturities:    Dict[str, StrategyMaturity]    = {}
        self._confidences:   Dict[str, LearningConfidence]  = {}

        # Engines (stateless apart from lesson_registry in knowledge_engine)
        self._perf_monitor   = StrategyPerformanceMonitor()
        self._drift_detector = DriftDetector()
        self._deg_detector   = DegradationDetector()
        self._perf_learner   = PerformanceLearner()
        self._adapt_engine   = AdaptationEngine()
        self._know_engine    = KnowledgeEngine()
        self._rec_engine     = RecommendationEngine()
        self._maturity_ass   = MaturityAssessor()
        self._score_calc     = LearningScoreCalculator()

    # ── Core public API ────────────────────────────────────────────────────────

    def observe(self, obs: LearningObservation) -> StrategyLearningProfile:
        """Record a new observation and update the learning profile."""
        with self._lock:
            sid = obs.strategy_id
            if sid not in self._profiles:
                self._profiles[sid] = StrategyLearningProfile(
                    strategy_id=sid,
                    strategy_name=obs.strategy_name,
                )

            profile = self._profiles[sid]
            profile.record(obs, baseline_window=self._policy.baseline_window)
            self._obs_store.append(obs)
            self._perf_monitor.observe(obs)

            # Invalidate cache
            for store in (self._scores, self._degradations, self._adaptations,
                          self._recs, self._knowledge, self._maturities,
                          self._confidences):
                store.pop(sid, None)

            # Run analytics in background (sync inside lock to keep cache consistent)
            self._run_analytics(sid)

            # Snapshot
            score = self._scores.get(sid)
            deg   = self._degradations.get(sid)
            snap  = LearningSnapshot.from_profile(
                profile,
                learning_score=score.overall_learning_score if score else 0.0,
                degradation_score=deg.degradation_score if deg else 0.0,
                adaptability_score=self._adaptations.get(sid,
                    type("", (), {"overall_adaptation": 0.0})()).overall_adaptation,
            )
            self._snap_store.append(snap)

            # Emit event
            self._event_bus.emit(LearningEvent(
                event_id=str(__import__("uuid").uuid4()),
                event_type=LearningEventType.OBSERVATION_RECORDED,
                strategy_id=sid,
                payload={"observation_id": obs.observation_id,
                         "evaluation_score": obs.evaluation_score},
            ))

            return profile

    def observe_batch(
        self, observations: List[LearningObservation]
    ) -> Dict[str, StrategyLearningProfile]:
        """Record a batch of observations, parallelising by strategy."""
        by_strategy: Dict[str, List[LearningObservation]] = {}
        for obs in observations:
            by_strategy.setdefault(obs.strategy_id, []).append(obs)

        profiles: Dict[str, StrategyLearningProfile] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self._observe_strategy_batch, sid, obs_list): sid
                for sid, obs_list in by_strategy.items()
            }
            for fut in as_completed(futures):
                sid = futures[fut]
                profiles[sid] = fut.result()

        return profiles

    def _observe_strategy_batch(
        self, sid: str, observations: List[LearningObservation]
    ) -> StrategyLearningProfile:
        profile = None
        for obs in observations:
            profile = self.observe(obs)
        return profile  # type: ignore[return-value]

    # ── Query API ──────────────────────────────────────────────────────────────

    def get_profile(self, strategy_id: str) -> Optional[StrategyLearningProfile]:
        with self._lock:
            return self._profiles.get(strategy_id)

    def get_learning_score(self, strategy_id: str) -> Optional[LearningScore]:
        with self._lock:
            return self._scores.get(strategy_id)

    def get_degradation_report(self, strategy_id: str) -> Optional[DegradationReport]:
        with self._lock:
            return self._degradations.get(strategy_id)

    def get_adaptation_report(self, strategy_id: str) -> Optional[AdaptationReport]:
        with self._lock:
            return self._adaptations.get(strategy_id)

    def get_recommendations(self, strategy_id: str) -> List[Recommendation]:
        with self._lock:
            return self._recs.get(strategy_id, [])

    def get_knowledge(self, strategy_id: str) -> List[Lesson]:
        with self._lock:
            return self._know_engine.get_lessons(strategy_id)

    def get_maturity(self, strategy_id: str) -> Optional[StrategyMaturity]:
        with self._lock:
            return self._maturities.get(strategy_id)

    def get_confidence(self, strategy_id: str) -> Optional[LearningConfidence]:
        with self._lock:
            return self._confidences.get(strategy_id)

    def get_lessons(self, strategy_id: str) -> List[Lesson]:
        with self._lock:
            return self._know_engine.get_lessons(strategy_id)

    def get_drift_signals(self, strategy_id: str) -> List[DriftSignal]:
        with self._lock:
            obs = self._obs_store.get_all(strategy_id)
            if len(obs) < self._policy.baseline_window + 1:
                return []
            baseline = obs[:self._policy.baseline_window]
            recent   = obs[-self._policy.drift_window:]
            return self._drift_detector.detect(baseline, recent)

    def learning_history(self, strategy_id: str, n: int = 20) -> List[LearningSnapshot]:
        with self._lock:
            return self._snap_store.history(strategy_id, n)

    def improvement_timeline(self, strategy_id: str, n: int = 10) -> List[float]:
        with self._lock:
            return self._snap_store.score_trend(strategy_id, n)

    def compare_strategies(
        self, strategy_ids: List[str]
    ) -> Dict[str, Optional[LearningScore]]:
        with self._lock:
            return {sid: self._scores.get(sid) for sid in strategy_ids}

    def top_strategies(self, n: int = 5) -> List[Tuple[str, float]]:
        with self._lock:
            scored = [
                (sid, score.overall_learning_score)
                for sid, score in self._scores.items()
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:n]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_strategies":    len(self._profiles),
                "total_observations":  sum(
                    len(self._obs_store.get_all(sid))
                    for sid in self._profiles
                ),
                "scored_strategies":   len(self._scores),
                "policy":              {
                    "baseline_window": self._policy.baseline_window,
                    "drift_window":    self._policy.drift_window,
                    "success_threshold": self._policy.success_threshold,
                },
            }

    @property
    def event_bus(self) -> LearningEventBus:
        return self._event_bus

    # ── Internal analytics ─────────────────────────────────────────────────────

    def _run_analytics(self, sid: str) -> None:
        """Compute all analytics for a strategy. Called while holding the lock."""
        obs     = self._obs_store.get_all(sid)
        profile = self._profiles[sid]

        if not obs:
            return

        baseline_obs = obs[:self._policy.baseline_window]
        recent_obs   = obs[-self._policy.drift_window:]

        # Degradation
        deg = self._deg_detector.detect(obs) if len(obs) >= self._policy.baseline_window + 1 else None
        if deg:
            self._degradations[sid] = deg

        # Adaptation
        if len(obs) >= self._policy.min_observations_for_patterns:
            adapt = self._adapt_engine.analyse(obs)
            self._adaptations[sid] = adapt
        else:
            adapt = None

        # Knowledge
        know = self._know_engine.extract(obs, deg)
        self._knowledge[sid] = know

        # Performance
        if len(obs) >= self._policy.min_observations_for_patterns:
            perf_result = self._perf_learner.learn(obs)
        else:
            perf_result = None

        # Maturity
        maturity = self._maturity_ass.assess(profile, obs)
        self._maturities[sid] = maturity

        # Confidence
        conf = LearningConfidence.compute(profile, obs, self._policy)
        self._confidences[sid] = conf

        # Score
        score = self._score_calc.score(profile, perf_result, adapt, know, maturity, conf)
        self._scores[sid] = score

        # Recommendations
        recs = self._rec_engine.generate(profile, deg, adapt, know)
        self._recs[sid] = recs
