"""iios/decision_evaluation/evaluation_manager.py — EvaluationRequest, EvaluationResult, EvaluationManager."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from .evaluation_constants import (
    DEFAULT_NORMALIZATION,
    DEFAULT_RANKING_METHOD,
    DEFAULT_SCORING_METHOD,
    MAX_EVALUATION_HISTORY,
    EvaluationMode,
    NormalizationMethod,
    RankingMethod,
    ScoringMethod,
)
from .evaluation_exceptions import EvaluationNotFoundError, InsufficientAlternativesError
from .evaluation_context import Alternative
from .criteria.criterion import Criterion
from .scoring.score_calculator import AlternativeScore
from .scoring.score_report import ScoreReport
from .scoring.scoring_engine import ScoringEngine
from .ranking.ranking_engine import RankingEngine
from .ranking.ranking_report import RankingReport
from .tradeoff.decision_matrix import DecisionMatrix
from .tradeoff.tradeoff_analyzer import TradeoffAnalysis, TradeoffPair
from .tradeoff.tradeoff_engine import TradeoffEngine
from .tradeoff.utility_engine import UtilityFunction
from .weighting.weight_manager import WeightManager


@dataclass
class EvaluationRequest:
    request_id:       str  = field(default_factory=lambda: str(uuid.uuid4()))
    alternatives:     list[Alternative] = field(default_factory=list)
    criteria:         list[Criterion]   = field(default_factory=list)
    weights:          dict[str, float]  = field(default_factory=dict)
    evaluation_mode:  EvaluationMode    = EvaluationMode.LENIENT
    scoring_method:   ScoringMethod     = DEFAULT_SCORING_METHOD
    normalization:    NormalizationMethod = DEFAULT_NORMALIZATION
    ranking_method:   RankingMethod     = DEFAULT_RANKING_METHOD
    tradeoff_pairs:   list[TradeoffPair] = field(default_factory=list)
    utility_fn:       UtilityFunction | None = None
    metadata:         dict = field(default_factory=dict)
    created_at:       float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "n_alternatives":   len(self.alternatives),
            "n_criteria":       len(self.criteria),
            "evaluation_mode":  self.evaluation_mode.value,
            "scoring_method":   self.scoring_method.value,
            "normalization":    self.normalization.value,
            "ranking_method":   self.ranking_method.value,
            "n_tradeoff_pairs": len(self.tradeoff_pairs),
        }


@dataclass
class EvaluationResult:
    result_id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:          str = ""
    alternatives:        list[Alternative]     = field(default_factory=list)
    scored_alternatives: list[AlternativeScore] = field(default_factory=list)
    ranked_alternatives: list[AlternativeScore] = field(default_factory=list)
    recommended_id:      str | None = None
    decision_matrix:     DecisionMatrix | None = None
    score_report:        ScoreReport   | None = None
    ranking_report:      RankingReport | None = None
    tradeoff_analysis:   TradeoffAnalysis | None = None
    succeeded:           bool = True
    errors:              list[str] = field(default_factory=list)
    warnings:            list[str] = field(default_factory=list)
    total_alternatives:  int   = 0
    total_criteria:      int   = 0
    duration_ms:         float = 0.0
    created_at:          float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":          self.result_id,
            "request_id":         self.request_id,
            "succeeded":          self.succeeded,
            "recommended_id":     self.recommended_id,
            "total_alternatives": self.total_alternatives,
            "total_criteria":     self.total_criteria,
            "duration_ms":        self.duration_ms,
            "errors":             self.errors,
            "warnings":           self.warnings,
        }


class EvaluationManager:
    """
    High-level interface for running evaluation pipelines.
    Thread-safe; maintains a capped result history.
    """

    def __init__(
        self,
        scoring_engine:  ScoringEngine  | None = None,
        ranking_engine:  RankingEngine  | None = None,
        tradeoff_engine: TradeoffEngine | None = None,
        weight_manager:  WeightManager  | None = None,
    ) -> None:
        self._scoring  = scoring_engine  or ScoringEngine()
        self._ranking  = ranking_engine  or RankingEngine()
        self._tradeoff = tradeoff_engine or TradeoffEngine()
        self._weights  = weight_manager  or WeightManager()
        self._history: dict[str, EvaluationResult] = {}
        self._lock = threading.RLock()

    # ── Core evaluate ──────────────────────────────────────────────────────

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        start = time.perf_counter()
        result = EvaluationResult(
            request_id       = request.request_id,
            alternatives     = list(request.alternatives),
            total_alternatives = len(request.alternatives),
            total_criteria     = len(request.criteria),
        )

        try:
            if len(request.alternatives) < 1:
                raise InsufficientAlternativesError(len(request.alternatives), required=1)

            # 1. Score
            scored = self._scoring.score(
                request.alternatives,
                request.criteria,
                weights       = request.weights or None,
                normalization = request.normalization,
                method        = request.scoring_method,
            )

            # 2. Optional utility transform
            if request.utility_fn is not None:
                scored = self._tradeoff.apply_utility(scored, request.utility_fn)

            # 3. Rank
            ranked = self._ranking.rank(scored, method=request.ranking_method)

            # 4. Build artifacts
            score_report   = self._scoring.build_report(
                scored, request.criteria,
                normalization = request.normalization,
                method        = request.scoring_method,
            )
            ranking_report = self._ranking.build_report(ranked, method=request.ranking_method)

            tradeoff_analysis = None
            if request.tradeoff_pairs:
                tradeoff_analysis = self._tradeoff.analyze(scored, request.tradeoff_pairs)

            # Build raw scores map for the decision matrix
            raw_scores_map = self._build_raw_map(scored)
            norm_scores_map = self._build_norm_map(scored)
            weight_map      = {c.criterion_id: score_report.scores.get(c.criterion_id, 0.0)
                                for c in request.criteria}

            from .tradeoff.decision_matrix import build_decision_matrix
            matrix = build_decision_matrix(
                request.alternatives, request.criteria,
                raw_scores_map, norm_scores_map,
                self._weights.resolve(request.criteria, request.weights or None),
                scored,
            )

            result.scored_alternatives = scored
            result.ranked_alternatives = ranked
            result.recommended_id      = ranked[0].alternative_id if ranked else None
            result.decision_matrix     = matrix
            result.score_report        = score_report
            result.ranking_report      = ranking_report
            result.tradeoff_analysis   = tradeoff_analysis

        except Exception as exc:  # noqa: BLE001
            result.succeeded = request.evaluation_mode == EvaluationMode.AUDIT
            result.errors.append(str(exc))
            if request.evaluation_mode == EvaluationMode.STRICT:
                raise

        result.duration_ms = (time.perf_counter() - start) * 1_000.0
        self._store(result)
        return result

    # ── Query history ──────────────────────────────────────────────────────

    def get(self, result_id: str) -> EvaluationResult:
        with self._lock:
            if result_id not in self._history:
                raise EvaluationNotFoundError(result_id)
            return self._history[result_id]

    def recent(self, n: int = 10) -> list[EvaluationResult]:
        with self._lock:
            items = sorted(self._history.values(), key=lambda r: r.created_at, reverse=True)
            return items[:n]

    def statistics(self) -> dict:
        with self._lock:
            total   = len(self._history)
            success = sum(1 for r in self._history.values() if r.succeeded)
            return {"total": total, "success": success, "failure": total - success}

    def stats(self) -> dict:
        return self.statistics()

    # ── Private helpers ────────────────────────────────────────────────────

    def _store(self, result: EvaluationResult) -> None:
        with self._lock:
            self._history[result.result_id] = result
            if len(self._history) > MAX_EVALUATION_HISTORY:
                oldest = sorted(self._history, key=lambda k: self._history[k].created_at)
                for k in oldest[:len(self._history) - MAX_EVALUATION_HISTORY]:
                    del self._history[k]

    @staticmethod
    def _build_raw_map(scored: list[AlternativeScore]) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for a in scored:
            result[a.alternative_id] = {cs.criterion_id: cs.raw_score for cs in a.criterion_scores}
        return result

    @staticmethod
    def _build_norm_map(scored: list[AlternativeScore]) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for a in scored:
            result[a.alternative_id] = {cs.criterion_id: cs.normalized_score for cs in a.criterion_scores}
        return result


_manager: EvaluationManager | None = None
_lock    = threading.Lock()


def get_evaluation_manager() -> EvaluationManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = EvaluationManager()
    return _manager


def reset_evaluation_manager() -> None:
    global _manager
    with _lock:
        _manager = None
