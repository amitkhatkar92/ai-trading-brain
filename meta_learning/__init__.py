"""
Meta-Learning Engine
=====================
Institutional-grade strategy-of-strategies learning layer.

The MetaLearningEngine learns WHICH strategies perform best under WHICH
market conditions and dynamically allocates capital accordingly — instead
of using static regime→strategy rules.

Architecture:
  MarketSnapshot
      ↓
  FeatureExtractor  →  FeatureVector (8-dim normalised)
      ↓
  MetaModel (k-NN weighted regression)
      ↓
  StrategyWeightPredictor  →  {strategy: weight} dict
      ↓
  MetaStrategyController.set_ml_weights()

Training feedback loop:
  Trade closes → PerformanceDataset.add_from_trade()
               → TrainingEngine.add_observation() (incremental live update)
               → Weekly: TrainingEngine.force_retrain()

Usage::
    from meta_learning import MetaLearningEngine

    engine     = MetaLearningEngine()
    allocation = engine.predict(market_snapshot, active_strategies)
    # allocation.allocations → {"Mean_Reversion": 0.42, "Momentum": 0.27, ...}

    # after trades close:
    engine.record_result(strategy="Mean_Reversion", snapshot=snap,
                         r_multiple=+1.35, return_pct=0.62, won=True)
    engine.retrain_if_due()
"""

from __future__ import annotations
from typing import Optional

from utils import get_logger

from .feature_extractor       import FeatureExtractor,      FeatureVector
from .performance_dataset     import PerformanceDataset,    PerformanceRecord
from .meta_model              import MetaModel,             Observation
from .training_engine         import TrainingEngine
from .strategy_weight_predictor import (StrategyWeightPredictor,
                                        StrategyAllocation)

log = get_logger(__name__)

# Agents exposed for system agent count
AGENTS = [
    "MetaLearningEngine",
    "FeatureExtractor",
    "MetaModel",
    "TrainingEngine",
    "StrategyWeightPredictor",
    "PerformanceDataset",
]


class MetaLearningEngine:
    """
    Single entry point for the meta-learning strategy selection layer.

    Sits between Market Intelligence and Meta Strategy Controller in the
    orchestrator pipeline.

    Usage::
        engine     = MetaLearningEngine()

        # On each cycle — produce ML-driven allocation
        allocation = engine.predict(snapshot, ["Mean_Rev", "Breakout", "ORB"])

        # After EOD — record trade results for learning
        engine.record_result("Mean_Rev", snapshot, r_multiple=1.2,
                             return_pct=0.55, won=True)

        # Periodic (weekly) retrain
        engine.retrain_if_due()
    """

    def __init__(self) -> None:
        self._extractor  = FeatureExtractor()
        self._dataset    = PerformanceDataset()
        self._model      = MetaModel()
        self._trainer    = TrainingEngine(self._dataset, self._model)
        self._predictor  = StrategyWeightPredictor(self._model)
        self._last_snapshot = None   # cache latest snapshot for record_result

        # Attempt initial train if we have saved data
        self._trainer.train_if_due()

        log.info("[MetaLearningEngine] Initialised. "
                 "Dataset records: %d  |  Model trained: %s",
                 self._dataset.record_count(),
                 "✅" if self._model.is_trained() else "⬜ (warming up)")

    # ── Public API ────────────────────────────────────────────────────────
    def predict(self, snapshot, strategies: list[str],
                print_report: bool = False) -> StrategyAllocation:
        """
        Produce ML-driven strategy allocation weights for the current cycle.

        Parameters
        ----------
        snapshot   : MarketSnapshot (or duck-typed object with regime/vix/etc.)
        strategies : List of candidate strategy names to allocate across
        print_report : Whether to print the allocation table to stdout

        Returns
        -------
        StrategyAllocation with .allocations dict (sum ≈ 1.0)
        """
        self._last_snapshot = snapshot
        features   = self._extractor.extract(snapshot)
        allocation = self._predictor.predict(features, strategies)

        if print_report:
            allocation.print_allocation()
        return allocation

    def record_result(self, strategy: str, snapshot,
                      r_multiple: float, return_pct: float, won: bool,
                      trade_date: Optional[str] = None) -> None:
        """
        Record a trade outcome into the performance dataset AND update the
        live model incrementally (no full retrain needed).
        """
        snap = snapshot if snapshot is not None else self._last_snapshot
        if snap is None:
            log.warning("[MetaLearningEngine] No snapshot available for record_result.")
            return

        self._dataset.add_from_trade(
            strategy   = strategy,
            snapshot   = snap,
            r_multiple = r_multiple,
            return_pct = return_pct,
            won        = won,
            trade_date = trade_date,
        )

        # Incremental model update (same record added to live model)
        features = self._extractor.extract(snap)
        self._trainer.add_observation(strategy, features.__dict__, r_multiple)

    def retrain_if_due(self) -> bool:
        """
        Trigger a full retrain if the weekly interval has elapsed.
        Returns True if retraining occurred.
        """
        retrained = self._trainer.train_if_due()
        if retrained:
            self._dataset.save()
        return retrained

    def force_retrain(self) -> None:
        """Force immediate full retrain (e.g. called after paper-trading review)."""
        self._trainer.force_retrain()
        self._dataset.save()

    def save_dataset(self) -> None:
        """Persist the performance dataset to disk."""
        self._dataset.save()

    def status(self) -> str:
        return (f"Records={self._dataset.record_count()}  "
                f"ModelTrained={self._model.is_trained()}  "
                f"Observations={self._model.observation_count()}")


__all__ = [
    "MetaLearningEngine",
    "StrategyAllocation",
    "FeatureVector",
    "PerformanceRecord",
    "RegimeStrategyMap",
    "get_regime_strategy_map",
]

from .regime_strategy_map import RegimeStrategyMap, get_regime_strategy_map
