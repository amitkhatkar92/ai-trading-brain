"""datasets/training_dataset.py — Core dataset entity for the Learning Framework."""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from iios.integration.research.learning.learning_constants import (
    DataSplitStrategy,
    DEFAULT_RANDOM_SEED,
    DEFAULT_TEST_SPLIT,
    DEFAULT_TRAIN_SPLIT,
    DEFAULT_VAL_SPLIT,
    MIN_DATASET_SIZE,
)
from iios.integration.research.learning.learning_exceptions import InsufficientDataError
from iios.integration.research.learning.datasets.dataset_statistics import DatasetStatistics


@dataclass
class DatasetRecord:
    """A single labelled (or unlabelled) data point."""
    row_id:    str
    features:  dict[str, Any]
    label:     Optional[Any]   = None
    timestamp: Optional[float] = None
    weight:    float           = 1.0
    metadata:  dict[str, Any]  = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        features:  dict[str, Any],
        label:     Optional[Any]   = None,
        timestamp: Optional[float] = None,
        weight:    float           = 1.0,
        *,
        row_id:    Optional[str]   = None,
    ) -> "DatasetRecord":
        return cls(
            row_id    = row_id or f"row_{uuid.uuid4().hex[:10]}",
            features  = features,
            label     = label,
            timestamp = timestamp,
            weight    = weight,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id":    self.row_id,
            "features":  self.features,
            "label":     self.label,
            "timestamp": self.timestamp,
            "weight":    self.weight,
        }


class TrainingDataset:
    """
    Primary dataset type used for model training.

    Stores records in memory and provides train/val/test split helpers.
    """

    def __init__(
        self,
        dataset_id:    str,
        name:          str,
        records:       list[DatasetRecord],
        *,
        version:       str                  = "1.0.0",
        label_name:    Optional[str]        = None,
        feature_names: Optional[list[str]] = None,
        metadata:      Optional[dict]       = None,
    ) -> None:
        self.dataset_id   = dataset_id
        self.name         = name
        self.version      = version
        self._records:    list[DatasetRecord] = list(records)
        self.label_name   = label_name
        self.feature_names: list[str] = feature_names or (
            list(records[0].features.keys()) if records else []
        )
        self.metadata     = metadata or {}
        self.created_at   = time.time()

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:          str,
        records:       list[DatasetRecord],
        *,
        dataset_id:    Optional[str]        = None,
        version:       str                  = "1.0.0",
        label_name:    Optional[str]        = None,
        feature_names: Optional[list[str]] = None,
        metadata:      Optional[dict]       = None,
    ) -> "TrainingDataset":
        return cls(
            dataset_id   = dataset_id or f"ds_{uuid.uuid4().hex[:12]}",
            name         = name,
            records      = records,
            version      = version,
            label_name   = label_name,
            feature_names = feature_names,
            metadata     = metadata,
        )

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[DatasetRecord]:
        return iter(self._records)

    def records(self) -> list[DatasetRecord]:
        return list(self._records)

    def record_dicts(self) -> list[dict[str, Any]]:
        """Return all records as flat dicts: {**features, label, timestamp}."""
        result = []
        for r in self._records:
            d = dict(r.features)
            if self.label_name and r.label is not None:
                d[self.label_name] = r.label
            if r.timestamp is not None:
                d["timestamp"] = r.timestamp
            result.append(d)
        return result

    # ── Splits ────────────────────────────────────────────────────────────────

    def split_train_val_test(
        self,
        train:  float = DEFAULT_TRAIN_SPLIT,
        val:    float = DEFAULT_VAL_SPLIT,
        test:   float = DEFAULT_TEST_SPLIT,
        *,
        seed:   int   = DEFAULT_RANDOM_SEED,
    ) -> tuple["TrainingDataset", "ValidationDataset", "TestDataset"]:
        """Random shuffle split into train / validation / test subsets."""
        if len(self) < MIN_DATASET_SIZE:
            raise InsufficientDataError(
                f"Dataset has {len(self)} records; minimum is {MIN_DATASET_SIZE}"
            )
        rng    = random.Random(seed)
        data   = list(self._records)
        rng.shuffle(data)
        n      = len(data)
        n_train = int(n * train)
        n_val   = int(n * val)
        return (
            TrainingDataset.create(
                self.name + "_train", data[:n_train],
                dataset_id    = self.dataset_id + "_train",
                version       = self.version,
                label_name    = self.label_name,
                feature_names = self.feature_names,
            ),
            ValidationDataset.create(
                self.name + "_val", data[n_train:n_train + n_val],
                dataset_id    = self.dataset_id + "_val",
                version       = self.version,
                label_name    = self.label_name,
                feature_names = self.feature_names,
            ),
            TestDataset.create(
                self.name + "_test", data[n_train + n_val:],
                dataset_id    = self.dataset_id + "_test",
                version       = self.version,
                label_name    = self.label_name,
                feature_names = self.feature_names,
            ),
        )

    def split_time_series(
        self,
        n_folds:      int   = 5,
        oos_fraction: float = 0.20,
    ) -> list[tuple["TrainingDataset", "ValidationDataset"]]:
        """Expanding-window walk-forward split for time-series data."""
        n      = len(self._records)
        oos_n  = max(1, n // (n_folds + 1))
        folds: list[tuple["TrainingDataset", "ValidationDataset"]] = []
        for fold in range(n_folds):
            oos_start = oos_n + fold * oos_n
            oos_end   = oos_start + oos_n
            if oos_end > n:
                break
            train_recs = self._records[:oos_start]
            val_recs   = self._records[oos_start:oos_end]
            folds.append((
                TrainingDataset.create(
                    f"{self.name}_fold{fold}_train", train_recs,
                    label_name=self.label_name, feature_names=self.feature_names,
                ),
                ValidationDataset.create(
                    f"{self.name}_fold{fold}_val", val_recs,
                    label_name=self.label_name, feature_names=self.feature_names,
                ),
            ))
        return folds

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> DatasetStatistics:
        flat = self.record_dicts()
        return DatasetStatistics.compute(
            flat,
            self.feature_names,
            self.label_name,
            has_timestamps = any(r.timestamp is not None for r in self._records),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id":    self.dataset_id,
            "name":          self.name,
            "version":       self.version,
            "record_count":  len(self),
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "label_name":    self.label_name,
            "created_at":    self.created_at,
            "metadata":      self.metadata,
        }


class ValidationDataset(TrainingDataset):
    """Validation split of a training dataset."""
    pass


class TestDataset(TrainingDataset):
    """Held-out test split of a training dataset."""
    pass
