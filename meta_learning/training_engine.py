"""
Meta-Learning — Training Engine
==================================
Manages the periodic retraining cycle for the MetaModel.

Retraining schedule:
  • Weekly full retrain (every 7 days of accumulated data)
  • Incremental add on every new trade result

The TrainingEngine:
  1. Reads all records from PerformanceDataset
  2. Builds Observation objects (features + strategy + r_multiple)
  3. Calls MetaModel.fit() with the full observation set
  4. Tracks when the last retrain occurred

Training status is logged after each run.
"""

from __future__ import annotations
import math
from datetime import date, datetime, timedelta
from typing   import Optional

from utils import get_logger
from .feature_extractor  import FeatureExtractor
from .performance_dataset import PerformanceDataset
from .meta_model         import MetaModel, Observation

log = get_logger(__name__)

RETRAIN_INTERVAL_DAYS = 7    # full retrain every N calendar days


class TrainingEngine:
    """
    Drives periodic retraining of the MetaModel from the PerformanceDataset.

    Usage::
        engine = TrainingEngine(dataset, model)
        engine.train_if_due()          # retrain only when interval elapsed
        engine.force_retrain()         # retrain immediately
    """

    def __init__(self, dataset: PerformanceDataset,
                 model: MetaModel) -> None:
        self._dataset    = dataset
        self._model      = model
        self._extractor  = FeatureExtractor()
        self._last_train: Optional[date] = None
        self._train_count: int           = 0
        log.info("[TrainingEngine] Initialised. "
                 "Retrain interval: %d days.", RETRAIN_INTERVAL_DAYS)

    # ── Public API ────────────────────────────────────────────────────────
    def train_if_due(self) -> bool:
        """
        Retrain if:
          • we have never trained before, OR
          • RETRAIN_INTERVAL_DAYS have passed since last retrain
        Returns True if retraining occurred.
        """
        if not self._dataset.is_ready_for_training():
            log.debug("[TrainingEngine] Not enough data yet (%d / %d records).",
                      self._dataset.record_count(), 20)
            return False

        today = date.today()
        if (self._last_train is None or
                (today - self._last_train).days >= RETRAIN_INTERVAL_DAYS):
            return self.force_retrain()
        return False

    def force_retrain(self) -> bool:
        """Retrain immediately regardless of schedule."""
        records = self._dataset.get_all()
        if not records:
            log.warning("[TrainingEngine] No records to train on.")
            return False

        observations: list[Observation] = []
        for rec in records:
            fv   = self._extractor.extract_from_dict(rec.feature_dict())
            obs  = Observation(
                features   = fv.to_list(),
                strategy   = rec.strategy,
                r_multiple = rec.r_multiple,
            )
            observations.append(obs)

        self._model.fit(observations)
        self._last_train  = date.today()
        self._train_count += 1

        n_strats = len(set(o.strategy for o in observations))
        log.info("[TrainingEngine] Retrain #%d complete. "
                 "Records: %d  |  Strategies: %d  |  Model ready: %s",
                 self._train_count, len(observations), n_strats,
                 "✅" if self._model.is_trained() else "❌")
        return True

    def add_observation(self, strategy: str, features_dict: dict,
                        r_multiple: float) -> None:
        """
        Incremental update — add a single new observation to the live model
        without waiting for the next scheduled retrain.
        """
        fv  = self._extractor.extract_from_dict(features_dict)
        obs = Observation(
            features   = fv.to_list(),
            strategy   = strategy,
            r_multiple = r_multiple,
        )
        self._model.add(obs)

    @property
    def days_until_retrain(self) -> int:
        if self._last_train is None:
            return 0
        delta = RETRAIN_INTERVAL_DAYS - (date.today() - self._last_train).days
        return max(0, delta)
