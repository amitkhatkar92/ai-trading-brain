"""
dre_config.py — Configuration for the DNA Reinforcement Engine.

O-002: DNA Reinforcement Engine (DRE).

All DRE thresholds and learning weights in one place.
Change control: update only through explicit parameter assignment.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class DREConfig:
    """
    Single source of truth for all DRE configurable parameters.

    Safety invariants:
        max_single_trade_delta  — hard cap on |confidence change| per trade.
        min_idr_evidence_count  — protects new DNA from premature reinforcement.
        learning_rate           — scales all confidence deltas globally.

    These three values prevent any single trade from corrupting institutional DNA.
    """

    # ── Safety caps ───────────────────────────────────────────────────────────
    # Maximum |confidence_delta| any single reinforcement event may produce.
    max_single_trade_delta:   float = 0.05

    # DNA must have at least this many statistical observations before DRE touches it.
    min_idr_evidence_count:   int   = 10

    # PMCI alignment below this threshold → DNA is not considered "used" in the trade.
    min_alignment_threshold:  float = 0.30

    # |R-multiple| below this → outcome is NEUTRAL regardless of win/loss.
    min_r_multiple_magnitude: float = 0.25

    # ── Learning rate ─────────────────────────────────────────────────────────
    # Base multiplier applied to every confidence delta before capping.
    learning_rate:            float = 0.03

    # R-multiple is clamped to [r_scale_min, r_scale_max] before multiplication.
    r_multiple_scale_min:     float = 0.5
    r_multiple_scale_max:     float = 2.0

    # ── Outcome quality thresholds ────────────────────────────────────────────
    r_excellent_threshold:    float = 2.0   # R >= → EXCELLENT
    r_good_threshold:         float = 1.0   # R >= → GOOD (win only)
    r_fair_min:               float = -0.5  # R >= → FAIR (loss side)
    r_poor_min:               float = -1.5  # R >= → POOR; below → BAD

    # ── Stability adjustments ─────────────────────────────────────────────────
    stability_win_delta:      float =  0.01  # positive events gently improve stability
    stability_loss_delta:     float = -0.02  # negative events gently reduce stability
    stability_neutral_delta:  float =  0.0   # neutral events leave stability unchanged

    # ── DNA lifecycle eligibility ─────────────────────────────────────────────
    # Only DNA in these lifecycle states are eligible for reinforcement.
    eligible_lifecycles:      Tuple[str, ...] = (
        "INSTITUTIONAL", "WEAKENING", "DRIFTING",
    )

    # ── Confidence / stability bounds ─────────────────────────────────────────
    confidence_min:           float = 0.05
    confidence_max:           float = 0.99
    stability_min:            float = 0.00
    stability_max:            float = 1.00

    # ── History management ────────────────────────────────────────────────────
    # Oldest records beyond this limit are evicted (FIFO) when history is saved.
    max_history_records:      int   = 10_000

    # ── Batch guard ───────────────────────────────────────────────────────────
    # Prevents runaway: one DNA can be reinforced at most this many times per batch.
    max_reinforcements_per_batch: int = 5

    # ── Contradictory weight ──────────────────────────────────────────────────
    # Fractional weight applied to confidence_delta for CONTRADICTORY events.
    contradictory_weight:     float = 0.5

    # ── Dry run ───────────────────────────────────────────────────────────────
    # Compute all reinforcements but do NOT write to IDR or history file.
    dry_run:                  bool  = False

    def fingerprint(self) -> str:
        """Stable 16-char SHA-256 fingerprint for audit logs (excludes dry_run)."""
        d = dataclasses.asdict(self)
        d.pop("dry_run", None)
        # tuples are not JSON-serialisable; normalise to list
        d["eligible_lifecycles"] = list(d.get("eligible_lifecycles", []))
        return hashlib.sha256(
            json.dumps(d, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
