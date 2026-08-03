"""
mls_config.py — Market Learning System configuration.

All MLS algorithm thresholds are owned by this module.
No threshold is hardcoded anywhere else in the market_learning package.
Changes to these values must follow the change control process in
MLS_GOVERNANCE.md §4.1.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass


@dataclass
class MLSConfig:
    """
    Single source of truth for all MLS configurable parameters.

    Every threshold that governs observation, DNA discovery, or validation
    lives here.  Statistical gates G-ML-01 through G-ML-07 (MLS_GOVERNANCE.md)
    correspond directly to the fields in this class.
    """

    # ── Temporal contract ──────────────────────────────────────────────────
    feature_deadline_hour:   int   = 9    # 09:15 IST = market open
    feature_deadline_minute: int   = 15
    feature_deadline_second: int   = 0    # boundary is inclusive: 09:15:00 passes

    # ── Universe ───────────────────────────────────────────────────────────
    min_universe_size: int = 10           # abort capture if fewer symbols extracted

    # ── Statistical gates ─────────────────────────────────────────────────
    min_group_size:            int   = 30    # G-ML-01: minimum n per winner/loser group
    min_effect_size:           float = 0.50  # G-ML-02: minimum |Cohen's d|
    max_p_value:               float = 0.05  # G-ML-03: max adjusted p-value
    min_consistency_pct_weekly:    float = 60.0  # G-ML-04: % of days in 5-day window
    min_consistency_pct_monthly:   float = 60.0  # G-ML-04: % of days in 20-day window
    min_consistency_pct_quarterly: float = 50.0  # G-ML-04: % of days in 60-day window
    min_regime_count:          int   = 2    # G-ML-05: regimes where characteristic holds
    min_sector_count:          int   = 3    # G-ML-06: sectors where characteristic holds
    min_oos_consistency_pct:   float = 0.50  # G-ML-07: OOS walk-forward pass rate
    max_contradiction_ratio:   float = 0.20  # max fraction of contradicting studies

    # ── Confidence formula weights (must sum to 1.0) ───────────────────────
    confidence_consistency_weight:  float = 0.50
    confidence_effect_size_weight:  float = 0.30
    confidence_significance_weight: float = 0.20

    # ── DNA lifecycle ──────────────────────────────────────────────────────
    new_char_lookback_days: int = 5    # days absent before re-flagging as "new"
    retirement_days:        int = 20   # consecutive absent days before RETIRED

    # ── Aggregation windows ────────────────────────────────────────────────
    weekly_window_days:    int = 5
    monthly_window_days:   int = 20
    quarterly_window_days: int = 60

    # ── Storage ────────────────────────────────────────────────────────────
    snapshot_retention_days: int = 90

    def config_hash(self) -> str:
        """SHA-256[:16] of canonical JSON config — used in audit trail."""
        raw = json.dumps(dataclasses.asdict(self), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
