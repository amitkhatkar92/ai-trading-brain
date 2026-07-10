"""core/learning_configuration.py — Training configuration for learning jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.learning.learning_constants import (
    DataSplitStrategy,
    DEFAULT_BATCH_SIZE,
    DEFAULT_EARLY_STOP_PATIENCE,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_EPOCHS,
    DEFAULT_RANDOM_SEED,
    DEFAULT_TEST_SPLIT,
    DEFAULT_TRAIN_SPLIT,
    DEFAULT_VAL_SPLIT,
)


@dataclass
class LearningConfiguration:
    """
    Encapsulates all hyperparameters and training settings for a job.

    Model-agnostic: the ``hyperparameters`` dict is passed directly to the
    model's ``fit()`` method for model-specific settings.
    """

    # Data splits
    train_split:         float             = DEFAULT_TRAIN_SPLIT
    val_split:           float             = DEFAULT_VAL_SPLIT
    test_split:          float             = DEFAULT_TEST_SPLIT
    split_strategy:      DataSplitStrategy = DataSplitStrategy.RANDOM

    # Training loop
    max_epochs:          int               = DEFAULT_MAX_EPOCHS
    early_stop_patience: int               = DEFAULT_EARLY_STOP_PATIENCE
    batch_size:          int               = DEFAULT_BATCH_SIZE
    learning_rate:       float             = DEFAULT_LEARNING_RATE
    random_seed:         int               = DEFAULT_RANDOM_SEED

    # Model-specific hyperparameters (passed through to model.fit)
    hyperparameters:     dict[str, Any]    = field(default_factory=dict)

    # Callback names (e.g. "early_stopping", "lr_scheduler")
    callbacks:           list[str]         = field(default_factory=list)

    # Free-form extra config
    extra:               dict[str, Any]    = field(default_factory=dict)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty = valid)."""
        errors: list[str] = []
        total = self.train_split + self.val_split + self.test_split
        if abs(total - 1.0) > 1e-6:
            errors.append(f"Splits must sum to 1.0, got {total:.4f}")
        for name, val in [("train_split", self.train_split), ("val_split", self.val_split),
                           ("test_split", self.test_split)]:
            if not (0.0 < val < 1.0):
                errors.append(f"{name} must be between 0 and 1, got {val}")
        if self.max_epochs < 1:
            errors.append("max_epochs must be >= 1")
        if self.batch_size < 1:
            errors.append("batch_size must be >= 1")
        if self.learning_rate <= 0.0:
            errors.append("learning_rate must be positive")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_split":         self.train_split,
            "val_split":           self.val_split,
            "test_split":          self.test_split,
            "split_strategy":      self.split_strategy.value,
            "max_epochs":          self.max_epochs,
            "early_stop_patience": self.early_stop_patience,
            "batch_size":          self.batch_size,
            "learning_rate":       self.learning_rate,
            "random_seed":         self.random_seed,
            "hyperparameters":     self.hyperparameters,
            "callbacks":           self.callbacks,
            "extra":               self.extra,
        }
