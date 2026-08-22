"""
mlc_config.py — Configuration for MarketLearningCoordinator.

All MLC thresholds live here. No magic numbers in the coordinator itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DEFAULT_HISTORY_PATH = str(
    Path(__file__).resolve().parent.parent / "data" / "mls" / "mlc" / "history.json"
)


@dataclass
class MLCConfig:
    """
    Configuration for one MarketLearningCoordinator instance.

    All boolean flags follow a consistent pattern:
        True  → stage is enabled and will be attempted each run
        False → stage is skipped; its LearningStage is marked SKIPPED

    Setting a flag to False is safe at any time — downstream stages are
    not affected because each stage is independent.
    """

    # ── History ────────────────────────────────────────────────────────────
    history_path:           str = _DEFAULT_HISTORY_PATH
    # Maximum number of historical runs kept on disk. Older runs are
    # evicted when the file is written at the end of each pipeline run.
    max_history_runs:       int = 90

    # ── Stage toggles ──────────────────────────────────────────────────────
    # Stage 1 — Strategy Learning: call LearningEngine.learn(trades)
    strategy_learning_enabled: bool = True

    # Stage 2 — AMLS: run the full MLS pipeline (7 stages)
    amls_enabled:           bool = True

    # Stage 3 — DNA Reinforcement: process closed trade outcomes through DRE
    dre_enabled:            bool = True

    # Stage 4 — IDR Refresh: read IDR statistics after reinforcement
    idr_refresh_enabled:    bool = True

    # Stage 5 — PIG Refresh: reload PIG library after IDR update
    pig_refresh_enabled:    bool = True

    # ── Safety ─────────────────────────────────────────────────────────────
    # If True, no IDR writes are made (useful for test environments).
    # Passed through to DREConfig if DRE is constructed by the coordinator.
    dry_run:                bool = False

    def __post_init__(self) -> None:
        if self.max_history_runs < 1:
            raise ValueError("max_history_runs must be >= 1")
