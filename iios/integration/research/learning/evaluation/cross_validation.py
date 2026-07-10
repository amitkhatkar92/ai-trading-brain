"""evaluation/cross_validation.py — K-fold and walk-forward cross-validation."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DEFAULT_CV_FOLDS
from iios.integration.research.learning.datasets.training_dataset import TrainingDataset


class CrossValidator:
    """
    Provides k-fold and walk-forward cross-validation split generation.

    Returns fold index tuples suitable for slicing TrainingDataset records.
    No external dependencies.
    """

    def __init__(self, n_folds: int = DEFAULT_CV_FOLDS, seed: int = 42) -> None:
        self.n_folds = n_folds
        self.seed    = seed

    def k_fold_splits(self, n: int) -> list[tuple[list[int], list[int]]]:
        """Return n_folds splits of (train_indices, val_indices) for n total rows."""
        import random
        rng     = random.Random(self.seed)
        indices = list(range(n))
        rng.shuffle(indices)
        fold_size = n // self.n_folds
        splits: list[tuple[list[int], list[int]]] = []
        for fold in range(self.n_folds):
            start = fold * fold_size
            end   = start + fold_size if fold < self.n_folds - 1 else n
            val   = indices[start:end]
            train = indices[:start] + indices[end:]
            splits.append((train, val))
        return splits

    def walk_forward_splits(self, n: int) -> list[tuple[list[int], list[int]]]:
        """Expanding window walk-forward splits."""
        oos_n  = max(1, n // (self.n_folds + 1))
        splits: list[tuple[list[int], list[int]]] = []
        for fold in range(self.n_folds):
            oos_start = oos_n + fold * oos_n
            oos_end   = oos_start + oos_n
            if oos_end > n:
                break
            splits.append((list(range(oos_start)), list(range(oos_start, oos_end))))
        return splits
