"""
Strategy Health Monitor — Meta-Control Layer
==============================================
Tracks live performance of every strategy and automatically disables
those showing signs of decay (falling win rate, rising drawdown, poor Sharpe).

Markets evolve. A strategy that worked six months ago may be curve-fitted
to a regime that no longer exists. This module catches that drift early.

Pipeline position:
    Trade Monitoring
        ↓
    Strategy Health Monitor   ← THIS MODULE
        ↓
    Learning Engine

Health gates (institutional thresholds)
─────────────────────────────────────────
  Win Rate  < 45%  → DISABLED
  Max Drawdown > 20%  → DISABLED     (rolling on last-20 trades)
  Sharpe Ratio < 0.80 → DISABLED     (annualised, last-20 trades)
  Minimum trades to assess: 5

Status levels
─────────────
  ✅ HEALTHY   — all metrics pass comfortably
  ⚠️ WARNING   — one metric approaching threshold (5% margin)
  ⛔ DISABLED  — one or more thresholds breached
  ❓ UNKNOWN   — insufficient trade data (< 5 trades; treated as passing)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Set

from utils import get_logger

log = get_logger(__name__)

HEALTH_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "strategy_health.json"
)

# ── Health gate constants ──────────────────────────────────────────────────
MIN_WIN_RATE     = 0.45    # minimum acceptable win rate
MAX_DRAWDOWN     = 0.20    # maximum tolerable rolling drawdown
MIN_SHARPE       = 0.80    # minimum annualised Sharpe (simplified)
MIN_TRADES       = 5       # minimum trades before dis-qualification
WARN_WIN_MARGIN  = 0.05    # warning if within 5% of win rate floor
WARN_DD_MARGIN   = 0.03    # warning if within 3% of drawdown ceiling
WARN_SHARPE_DELTA= 0.20    # warning if within 0.20 of Sharpe floor
RECENT_WINDOW    = 20      # rolling window (last N closed trades)


class HealthStatus(str, Enum):
    HEALTHY  = "healthy"
    WARNING  = "warning"
    DISABLED = "disabled"
    UNKNOWN  = "unknown"


@dataclass
class StrategyHealthRecord:
    """Live performance record for a single strategy."""

    strategy_name:  str
    trades:         int         = 0
    wins:           int         = 0
    total_r:        float       = 0.0       # cumulative R-multiples
    peak_equity:    float       = 0.0       # running peak of cumulative PnL%
    max_drawdown:   float       = 0.0       # max observed rolling drawdown
    recent_pnl:     List[float] = field(default_factory=list)   # last N trades
    disabled_since: Optional[str] = None
    last_updated:   str         = field(default_factory=lambda: datetime.now().isoformat())

    # ── Computed properties ────────────────────────────────────────────────

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    @property
    def avg_r(self) -> float:
        return self.total_r / self.trades if self.trades else 0.0

    @property
    def sharpe(self) -> float:
        """
        Annualised Sharpe of recent trades (simplified).
        Uses last-N PnL% values; annualises assuming ~252 trading days.
        """
        pnl = self.recent_pnl
        if len(pnl) < 3:
            return 0.0
        mu    = mean(pnl)
        sigma = stdev(pnl)
        return (mu / sigma * math.sqrt(252)) if sigma > 0 else 0.0

    @property
    def status(self) -> HealthStatus:
        if self.trades < MIN_TRADES:
            return HealthStatus.UNKNOWN

        # Hard failures
        if self.win_rate  < MIN_WIN_RATE:
            return HealthStatus.DISABLED
        if self.max_drawdown > MAX_DRAWDOWN:
            return HealthStatus.DISABLED
        if self.sharpe < MIN_SHARPE:
            return HealthStatus.DISABLED

        # Warning zone — approaching threshold
        if (self.win_rate  < MIN_WIN_RATE  + WARN_WIN_MARGIN
                or self.max_drawdown > MAX_DRAWDOWN - WARN_DD_MARGIN
                or self.sharpe < MIN_SHARPE + WARN_SHARPE_DELTA):
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name":  self.strategy_name,
            "trades":         self.trades,
            "wins":           self.wins,
            "total_r":        self.total_r,
            "peak_equity":    self.peak_equity,
            "max_drawdown":   self.max_drawdown,
            "recent_pnl":     self.recent_pnl[-RECENT_WINDOW:],
            "disabled_since": self.disabled_since,
            "last_updated":   datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyHealthRecord":
        obj = cls(strategy_name=d["strategy_name"])
        obj.trades         = d.get("trades", 0)
        obj.wins           = d.get("wins", 0)
        obj.total_r        = d.get("total_r", 0.0)
        obj.peak_equity    = d.get("peak_equity", 0.0)
        obj.max_drawdown   = d.get("max_drawdown", 0.0)
        obj.recent_pnl     = d.get("recent_pnl", [])
        obj.disabled_since = d.get("disabled_since")
        obj.last_updated   = d.get("last_updated", "")
        return obj


class StrategyHealthMonitor:
    """
    Monitors live performance of each strategy and automatically
    disables those that breach institutional quality thresholds.

    Persists state to data/strategy_health.json so health history
    survives between process restarts.
    """

    def __init__(self):
        self._records: Dict[str, StrategyHealthRecord] = {}
        self._load_db()
        log.info("[StrategyHealthMonitor] Initialised. Tracking %d strategies.",
                 len(self._records))

    # ─────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────

    def record_trade(
        self,
        strategy_name: str,
        pnl_pct: float,     # e.g. 0.015 = +1.5% on the trade
        r_multiple: float,  # e.g. 2.0 = a 2R win
    ) -> HealthStatus:
        """
        Record the outcome of a closed trade for the given strategy.
        Updates all metrics and persists state.
        Returns the updated health status.
        """
        rec = self._records.setdefault(
            strategy_name, StrategyHealthRecord(strategy_name=strategy_name)
        )

        rec.trades += 1
        if pnl_pct > 0:
            rec.wins += 1
        rec.total_r     += r_multiple
        rec.recent_pnl   = (rec.recent_pnl + [pnl_pct])[-RECENT_WINDOW:]

        # Rolling drawdown on recent PnL
        running = 0.0
        peak    = 0.0
        for p in rec.recent_pnl:
            running += p
            if running > peak:
                peak = running
            dd = (peak - running) / (1 + abs(peak)) if peak > 0 else 0.0
            if dd > rec.max_drawdown:
                rec.max_drawdown = dd

        # Update peak equity
        if running > rec.peak_equity:
            rec.peak_equity = running

        # Status transitions
        status = rec.status
        if status == HealthStatus.DISABLED and rec.disabled_since is None:
            rec.disabled_since = datetime.now().isoformat()
            log.warning(
                "[SHM] ⛔ '%s' DISABLED — WR=%.0f%% DD=%.1f%% Sharpe=%.2f",
                strategy_name, rec.win_rate * 100, rec.max_drawdown * 100, rec.sharpe,
            )
        elif status in (HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.UNKNOWN):
            if rec.disabled_since:
                log.info("[SHM] ✅ '%s' RE-ENABLED after metric recovery.", strategy_name)
                rec.disabled_since = None

        rec.last_updated = datetime.now().isoformat()
        self._save_db()
        return status

    def get_passing_strategies(self) -> Set[str]:
        """
        Returns the set of strategy names that are NOT disabled.
        UNKNOWN strategies (< 5 traded) are treated as passing —
        they get the benefit of the doubt until enough data exists.
        """
        passing: Set[str] = set()
        for name, rec in self._records.items():
            if rec.status != HealthStatus.DISABLED:
                passing.add(name)
        return passing

    def get_disabled_strategies(self) -> Set[str]:
        """Returns strategy names currently flagged as DISABLED."""
        return {
            name for name, rec in self._records.items()
            if rec.status == HealthStatus.DISABLED
        }

    def get_health_status(self, strategy_name: str) -> HealthStatus:
        rec = self._records.get(strategy_name)
        return rec.status if rec else HealthStatus.UNKNOWN

    def print_health_report(self) -> None:
        """Print a formatted strategy health table to the log."""
        if not self._records:
            log.info("[SHM] No strategy health data recorded yet.")
            return

        w = 84
        log.info("═" * w)
        log.info(
            "  STRATEGY HEALTH MONITOR  |  %d strategies tracked  |  %s",
            len(self._records),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        log.info("═" * w)
        log.info(
            "  %-30s  %6s  %8s  %6s  %8s  %7s  Status",
            "Strategy", "Trades", "WinRate", "Avg R", "Sharpe", "MaxDD%",
        )
        log.info("  " + "─" * (w - 2))

        _STATUS_LABEL = {
            HealthStatus.HEALTHY:  "✅ HEALTHY",
            HealthStatus.WARNING:  "⚠️  WARNING",
            HealthStatus.DISABLED: "⛔ DISABLED",
            HealthStatus.UNKNOWN:  "❓ UNKNOWN",
        }

        for name, rec in sorted(self._records.items()):
            log.info(
                "  %-30s  %6d  %7.0f%%  %6.2f  %8.2f  %6.1f%%  %s",
                name, rec.trades, rec.win_rate * 100,
                rec.avg_r, rec.sharpe, rec.max_drawdown * 100,
                _STATUS_LABEL.get(rec.status, "?"),
            )

        n_healthy  = sum(1 for r in self._records.values() if r.status == HealthStatus.HEALTHY)
        n_warn     = sum(1 for r in self._records.values() if r.status == HealthStatus.WARNING)
        n_disabled = sum(1 for r in self._records.values() if r.status == HealthStatus.DISABLED)
        n_unknown  = sum(1 for r in self._records.values() if r.status == HealthStatus.UNKNOWN)
        disabled_names = self.get_disabled_strategies()

        log.info("  " + "─" * (w - 2))
        log.info(
            "  ✅ Healthy: %d  ⚠️ Warning: %d  ⛔ Disabled: %d  ❓ Unknown: %d",
            n_healthy, n_warn, n_disabled, n_unknown,
        )
        if disabled_names:
            log.info("  Disabled strategies: %s", ", ".join(sorted(disabled_names)))
        log.info("  Thresholds — WinRate: >%.0f%%  MaxDD: <%.0f%%  Sharpe: >%.2f",
                 MIN_WIN_RATE * 100, MAX_DRAWDOWN * 100, MIN_SHARPE)
        log.info("═" * w)

    # ─────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────

    def _load_db(self) -> None:
        if not os.path.exists(HEALTH_DB_PATH):
            return
        try:
            with open(HEALTH_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, d in data.items():
                self._records[name] = StrategyHealthRecord.from_dict(d)
            log.info("[SHM] Loaded health records for %d strategies.", len(self._records))
        except Exception as exc:
            log.warning("[SHM] Could not load health DB: %s", exc)

    def _save_db(self) -> None:
        os.makedirs(os.path.dirname(HEALTH_DB_PATH), exist_ok=True)
        try:
            with open(HEALTH_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {name: rec.to_dict() for name, rec in self._records.items()},
                    f, indent=2,
                )
        except Exception as exc:
            log.warning("[SHM] Could not save health DB: %s", exc)
