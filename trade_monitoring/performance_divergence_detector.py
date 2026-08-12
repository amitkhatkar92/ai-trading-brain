"""
Performance Divergence Detector — G-002 Governance Remediation
===============================================================
Detects material divergence between live strategy performance (recorded in
StrategyHealthMonitor) and the synthetic/backtest baseline stored in
BacktestingAI's _BACKTEST_CACHE.

When divergence exceeds configurable thresholds, creates a persisted
ResearchInvestigation record so governance/ILC/GVA can review.

Safety guarantees:
  • Does NOT automatically enable or disable any strategy.
  • Does NOT generate trading signals.
  • Investigation records are idempotent — one per strategy per disable event.
  • Divergence detection thresholds are fully configurable via DivergenceConfig.

Data flow:
  MasterOrchestrator._do_eod_learning()
      → PerformanceDivergenceDetector.check_divergence(...)
          → DIVERGENCE_DETECTED → create investigation record
          → NO_DIVERGENCE       → log and exit
          → INSUFFICIENT_DATA   → log and exit

Lifecycle of an investigation:
  DIVERGENCE_DETECTED → RESEARCH_REQUIRED → INVESTIGATION → EXPLANATION_FOUND /
  INCONCLUSIVE → GOVERNANCE_DECISION (external, not automated here)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

INVESTIGATIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "divergence_investigations.json"
)

# ── Investigation status codes ─────────────────────────────────────────────
STATUS_RESEARCH_REQUIRED   = "RESEARCH_REQUIRED"
STATUS_UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
STATUS_EXPLANATION_FOUND   = "EXPLANATION_FOUND"
STATUS_INCONCLUSIVE        = "INCONCLUSIVE"
STATUS_CLOSED              = "CLOSED"


@dataclass
class DivergenceConfig:
    """Configurable thresholds for divergence detection.  All values are absolute."""

    # Minimum live trades before divergence is evaluated (too few = noise)
    min_live_sample: int = 5

    # Win-rate divergence threshold: abs(synthetic_wr - live_wr) must exceed this
    min_wr_divergence: float = 0.15          # 15 percentage points

    # Expectancy divergence: abs(synthetic_r - live_avg_r) must exceed this
    min_expectancy_divergence: float = 0.30  # 0.30R per trade

    # Above this sample size, divergence evidence is considered strong
    strong_signal_min_n: int = 20


@dataclass
class DivergenceInvestigation:
    """Persisted record of a divergence investigation."""

    investigation_id:   str
    strategy_name:      str
    status:             str                  # STATUS_* constant
    created_at:         str
    last_updated:       str
    # Evidence snapshot at time of detection
    live_wr:            float
    live_n:             int
    live_avg_r:         float
    synthetic_wr:       float
    synthetic_avg_r:    float
    wr_divergence:      float
    expectancy_divergence: float
    confidence:         str                  # HIGH / MEDIUM / LOW
    # Audit trail
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DivergenceInvestigation":
        return cls(**d)


class PerformanceDivergenceDetector:
    """
    Detects and records material divergence between live and synthetic strategy performance.

    Usage (from orchestrator EOD phase):
        detector = PerformanceDivergenceDetector()
        detector.check_divergence(
            strategy_name = "Mean_Reversion",
            live_wr       = 0.22,
            live_n        = 9,
            live_avg_r    = -0.188,
            synthetic_wr  = 0.58,
            synthetic_avg_r = 0.00715,
        )
    """

    def __init__(self, config: Optional[DivergenceConfig] = None) -> None:
        self._config = config or DivergenceConfig()
        self._investigations: Dict[str, DivergenceInvestigation] = {}
        self._load()
        log.info("[DivergenceDetector] Initialised. %d investigations on record.",
                 len(self._investigations))

    # ── Public API ─────────────────────────────────────────────────────────

    def check_divergence(
        self,
        strategy_name:   str,
        live_wr:         float,
        live_n:          int,
        live_avg_r:      float,
        synthetic_wr:    float,
        synthetic_avg_r: float,
    ) -> bool:
        """
        Evaluate whether the live vs synthetic performance gap is material.

        Returns True if a new investigation was created, False otherwise.
        Idempotent: will not create a second investigation for the same strategy
        while one is already in RESEARCH_REQUIRED or UNDER_INVESTIGATION state.
        """
        cfg = self._config

        # Guard: insufficient live data
        if live_n < cfg.min_live_sample:
            log.debug(
                "[DivergenceDetector] %s: insufficient live sample (%d < %d) — skip.",
                strategy_name, live_n, cfg.min_live_sample,
            )
            return False

        wr_div   = abs(synthetic_wr  - live_wr)
        r_div    = abs(synthetic_avg_r - live_avg_r)
        material = (wr_div >= cfg.min_wr_divergence
                    or r_div >= cfg.min_expectancy_divergence)

        if not material:
            log.debug(
                "[DivergenceDetector] %s: no material divergence "
                "(wr_div=%.2f r_div=%.3f).",
                strategy_name, wr_div, r_div,
            )
            return False

        # Idempotency: skip if an open investigation already exists
        existing = self._investigations.get(strategy_name)
        if existing and existing.status in (STATUS_RESEARCH_REQUIRED,
                                            STATUS_UNDER_INVESTIGATION):
            log.info(
                "[DivergenceDetector] %s: divergence detected but investigation "
                "already open (status=%s id=%s).",
                strategy_name, existing.status, existing.investigation_id,
            )
            return False

        confidence = (
            "HIGH"   if live_n >= cfg.strong_signal_min_n else
            "MEDIUM" if live_n >= cfg.min_live_sample * 2 else
            "LOW"
        )
        inv_id = f"DIV_{strategy_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ts     = datetime.now().isoformat()

        inv = DivergenceInvestigation(
            investigation_id      = inv_id,
            strategy_name         = strategy_name,
            status                = STATUS_RESEARCH_REQUIRED,
            created_at            = ts,
            last_updated          = ts,
            live_wr               = live_wr,
            live_n                = live_n,
            live_avg_r            = live_avg_r,
            synthetic_wr          = synthetic_wr,
            synthetic_avg_r       = synthetic_avg_r,
            wr_divergence         = wr_div,
            expectancy_divergence = r_div,
            confidence            = confidence,
            notes                 = [],
        )
        self._investigations[strategy_name] = inv
        self._save()

        log.warning(
            "[DivergenceDetector] 🔬 DIVERGENCE_DETECTED strategy=%s "
            "live_wr=%.0f%%(n=%d) synthetic_wr=%.0f%% "
            "wr_divergence=%.0fpp r_divergence=%.3fR "
            "confidence=%s investigation_id=%s "
            "→ RESEARCH_REQUIRED — governance review needed.",
            strategy_name,
            live_wr * 100, live_n, synthetic_wr * 100,
            wr_div * 100, r_div,
            confidence, inv_id,
        )
        return True

    def get_pending_investigations(self) -> List[DivergenceInvestigation]:
        """Return all investigations not yet CLOSED."""
        return [
            inv for inv in self._investigations.values()
            if inv.status not in (STATUS_CLOSED,)
        ]

    def update_investigation(
        self,
        strategy_name: str,
        new_status:    str,
        note:          str = "",
    ) -> None:
        """Progress an investigation to a new status and append a note."""
        inv = self._investigations.get(strategy_name)
        if inv is None:
            log.warning("[DivergenceDetector] update_investigation: no record for '%s'.",
                        strategy_name)
            return
        inv.status       = new_status
        inv.last_updated = datetime.now().isoformat()
        if note:
            inv.notes.append(f"{inv.last_updated}: {note}")
        self._save()
        log.info("[DivergenceDetector] investigation=%s strategy=%s → status=%s",
                 inv.investigation_id, strategy_name, new_status)

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(INVESTIGATIONS_PATH), exist_ok=True)
            with open(INVESTIGATIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._investigations.items()},
                    f, indent=2,
                )
        except Exception as exc:
            log.warning("[DivergenceDetector] Could not persist investigations: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(INVESTIGATIONS_PATH):
            return
        try:
            with open(INVESTIGATIONS_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                self._investigations[k] = DivergenceInvestigation.from_dict(v)
        except Exception as exc:
            log.warning("[DivergenceDetector] Could not load investigations: %s", exc)
