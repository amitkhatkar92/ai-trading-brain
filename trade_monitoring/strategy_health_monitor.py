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

Health gates — expectancy-aware governance
──────────────────────────────────────────
  Win rate alone does NOT disable a strategy.  Many profitable systematic
  strategies (trend-following, breakout, long-gamma) run 20–40% WR but earn
  their edge through large payoff asymmetry.  Suppressing them destroys the
  convex tail that makes them valuable.

  HARD DISABLE (execution blocked):
    Early-abort (8–19 trades):  WR < 25%  AND  total_r < −0.50
    Full gate   (≥ 20 trades):  WR < 45%  AND  total_r < −0.50
    Max Drawdown > 20%  (any trade count)
    Sharpe < 0.80       (any trade count)

  WARNING — advisory only, execution continues:
    WR < 25%  AND  total_r ≥ −0.50  (convex / asymmetric payoff candidate)
    WR < 45%  AND  total_r ≥ −0.50  (low WR but positive expectancy)
    Any metric approaching threshold (within 5% / 3% margin)

  Minimum CLEAN trades before any qualification verdict: 20

Status levels
─────────────
  ✅ HEALTHY        — all metrics pass comfortably
  ⚠️ WARNING        — threshold breached OR low WR with positive expectancy (advisory)
  🚫 DISABLED       — execution blocked (WR + expectancy both poor, or DD/Sharpe failed)
  ❓ WARMING_UP     — insufficient clean trade data (< 20 trades; treated as passing)
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
MIN_TRADES       = 20      # minimum CLEAN trades before any qualification verdict
                           # (5 was too low — corrupted data triggering premature flags)
WARN_WIN_MARGIN  = 0.05    # warning if within 5% of win rate floor
WARN_DD_MARGIN   = 0.03    # warning if within 3% of drawdown ceiling
WARN_SHARPE_DELTA= 0.20    # warning if within 0.20 of Sharpe floor
RECENT_WINDOW    = 20      # rolling window (last N closed trades)

# Early-abort: suspend a strategy before MIN_TRADES only when BOTH:
#   • WR < EARLY_ABORT_MAX_WR          — hit rate is critically low
#   • total_r < EARLY_ABORT_MIN_TOTAL_R — cumulative expectancy is also negative
# A strategy with low WR but positive/flat total_r is a convex or asymmetric-payoff
# system (trend-following, breakout, long-gamma).  It receives an advisory WARNING,
# NOT a hard execution block — suppressing it destroys its convex tail.
EARLY_ABORT_MIN_TRADES  = 8      # minimum trades before early-abort applies
EARLY_ABORT_MAX_WR      = 0.25   # WR threshold for early-abort gate
EARLY_ABORT_MIN_TOTAL_R = -0.50  # total_r must fall below this to trigger hard-disable

# Cooldown: sessions that must pass after an EARLY_ABORT disable before the
# strategy is eligible to auto-reactivate.  A 'session' is one trading day
# (incremented by tick_session()).  Manual override bypasses this.
EARLY_ABORT_COOLDOWN    = 5      # sessions

# Full-data expectancy gate (≥ MIN_TRADES): win rate alone does not justify a
# hard disable.  Hard-disable only when BOTH win rate AND cumulative expectancy
# are poor.  Strategies with low WR / positive total_r fall into WARNING only.
MIN_TOTAL_R             = -0.50  # total_r floor for full-data win-rate hard-disable

# Disable reason codes — stored in StrategyHealthRecord.disabled_reason
DISABLE_REASON_EARLY_ABORT  = "EARLY_ABORT_LOW_WR"
DISABLE_REASON_LOW_WIN_RATE = "LOW_WIN_RATE"
DISABLE_REASON_HIGH_DD      = "HIGH_DRAWDOWN"
DISABLE_REASON_LOW_SHARPE   = "LOW_SHARPE"
DISABLE_REASON_MANUAL       = "MANUAL_PAUSE"

# ── Strategy profile classification ───────────────────────────────────────
# Describes the expected payoff structure of a strategy.  Stored on every
# StrategyHealthRecord as metadata only — governance thresholds are NOT
# profile-aware yet.  Profile-aware governance is a future milestone;
# requires ≥ 50 official trades per strategy before classification is
# reliable enough to act on.
#
# Profiles:
#   HIGH_WR_LOW_R        — many small winners, rare large losses (e.g. mean-reversion)
#   LOW_WR_HIGH_R        — few large winners, many small losses (trend/momentum/breakout)
#   MODERATE_WR_DEF_RISK — defined max-loss per leg (options spreads, pairs)
#   UNKNOWN              — insufficient data or not yet classified
STRATEGY_PROFILES: Dict[str, str] = {
    "Mean_Reversion":           "HIGH_WR_LOW_R",
    "Momentum_Retest":          "LOW_WR_HIGH_R",
    "Trend_Pullback":           "LOW_WR_HIGH_R",
    "Breakout_Volume":          "LOW_WR_HIGH_R",
    "Bull_Call_Spread":         "MODERATE_WR_DEF_RISK",
    "Bear_Put_Spread":          "MODERATE_WR_DEF_RISK",
    "Iron_Condor_Range":        "MODERATE_WR_DEF_RISK",
    "Short_Straddle_IV_Spike":  "MODERATE_WR_DEF_RISK",
    "Long_Straddle_Pre_Event":  "LOW_WR_HIGH_R",
    "Hedging_Model":            "MODERATE_WR_DEF_RISK",
    "Futures_Basis_Arb":        "MODERATE_WR_DEF_RISK",
    "ETF_NAV_Arb":              "MODERATE_WR_DEF_RISK",
}  # type: ignore[assignment]  # evolved variants resolved at runtime

# Minimum trades needed before auto-classification heuristics are meaningful.
# Below this the distribution is too noisy — manual profile remains authoritative.
# This constant gates _compute_profile_suggestion() only; governance is unaffected.
PROFILE_SUGGEST_MIN_TRADES = 30


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

    # ── Disable metadata (persisted for analytics / regime analysis) ───────
    # Operational disable ≠ strategy deletion. Fields below enable post-disable
    # analysis to distinguish failure cause and support future reactivation.
    disabled_reason:     Optional[str]   = None   # e.g. EARLY_ABORT_LOW_WR
    disabled_at_trades:  Optional[int]   = None   # trade count when disabled
    disabled_wr:         Optional[float] = None   # win rate at disable time
    disabled_total_r:    Optional[float] = None   # total_r at disable time

    # ── Cooldown tracking ──────────────────────────────────────────────────
    # sessions_since_disabled is incremented once per trading session (EOD).
    # Strategies disabled via EARLY_ABORT stay blocked until this reaches
    # EARLY_ABORT_COOLDOWN (default 5 sessions) — prevents thrashing on
    # a single lucky trade.
    sessions_since_disabled: int  = 0
    cooldown_override:       bool = False   # True = manual bypass

    # ── Profile metadata ────────────────────────────────────────────────────
    # Payoff-structure classification.  METADATA ONLY — no governance logic
    # reads this field yet.  Profile-aware thresholds are a future milestone
    # (requires ≥ 50 official trades).  Auto-stamped from STRATEGY_PROFILES
    # on first record_trade() call; manually settable for evolved variants.
    strategy_profile_type: str = "UNKNOWN"

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
    def _cooldown_satisfied(self) -> bool:
        """True when cooldown requirement is met (or manually overridden)."""
        if self.cooldown_override:
            return True
        if self.disabled_reason == DISABLE_REASON_EARLY_ABORT:
            return self.sessions_since_disabled >= EARLY_ABORT_COOLDOWN
        return True

    @property
    def status(self) -> HealthStatus:
        # Early-abort gate (EARLY_ABORT_MIN_TRADES ≤ trades < MIN_TRADES):
        # Hard-disable only when BOTH WR is critically low AND expectancy is negative.
        # A low-WR / positive-expectancy profile indicates convex (asymmetric) payoff
        # behaviour — blocking it destroys the edge.  Issue WARNING instead.
        if EARLY_ABORT_MIN_TRADES <= self.trades < MIN_TRADES:
            if self.win_rate < EARLY_ABORT_MAX_WR:
                if self.total_r < EARLY_ABORT_MIN_TOTAL_R:
                    return HealthStatus.DISABLED          # low WR + negative expectancy
                return HealthStatus.WARNING               # low WR + positive expectancy

        # A previously early-aborted strategy whose metrics have recovered but
        # whose cooldown has not been served remains blocked.
        if (self.disabled_reason == DISABLE_REASON_EARLY_ABORT
                and self.disabled_since is not None
                and not self._cooldown_satisfied):
            return HealthStatus.DISABLED

        if self.trades < MIN_TRADES:
            return HealthStatus.UNKNOWN

        # Hard failures
        # Win-rate gate: only hard-disable when expectancy is also negative.
        # A low-WR / positive-total_r strategy is a convex system — it falls
        # through to WARNING (advisory) rather than a hard execution block.
        if self.win_rate < MIN_WIN_RATE and self.total_r < MIN_TOTAL_R:
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
            "strategy_name":           self.strategy_name,
            "trades":                  self.trades,
            "wins":                    self.wins,
            "total_r":                 self.total_r,
            "peak_equity":             self.peak_equity,
            "max_drawdown":            self.max_drawdown,
            "recent_pnl":              self.recent_pnl[-RECENT_WINDOW:],
            "disabled_since":          self.disabled_since,
            "last_updated":            datetime.now().isoformat(),
            # Disable metadata
            "disabled_reason":         self.disabled_reason,
            "disabled_at_trades":      self.disabled_at_trades,
            "disabled_wr":             self.disabled_wr,
            "disabled_total_r":        self.disabled_total_r,
            # Cooldown
            "sessions_since_disabled": self.sessions_since_disabled,
            "cooldown_override":       self.cooldown_override,
            # Profile metadata
            "strategy_profile_type":   self.strategy_profile_type,
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
        # Disable metadata
        obj.disabled_reason    = d.get("disabled_reason")
        obj.disabled_at_trades = d.get("disabled_at_trades")
        obj.disabled_wr        = d.get("disabled_wr")
        obj.disabled_total_r   = d.get("disabled_total_r")
        # Cooldown
        obj.sessions_since_disabled = d.get("sessions_since_disabled", 0)
        obj.cooldown_override       = d.get("cooldown_override", False)
        # Profile metadata — only load what is already in the JSON.
        # _backfill_profiles() handles stamping + saving for records without the field.
        obj.strategy_profile_type = d.get("strategy_profile_type", "UNKNOWN")
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
        # Auto-stamp profile on first encounter (no-op if already set from DB)
        if rec.strategy_profile_type == "UNKNOWN" and strategy_name in STRATEGY_PROFILES:
            rec.strategy_profile_type = STRATEGY_PROFILES[strategy_name]

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
            # First disable — stamp full metadata
            rec.disabled_since      = datetime.now().isoformat()
            rec.disabled_at_trades  = rec.trades
            rec.disabled_wr         = rec.win_rate
            rec.disabled_total_r    = rec.total_r
            rec.sessions_since_disabled = 0
            if rec.trades < MIN_TRADES:
                rec.disabled_reason = DISABLE_REASON_EARLY_ABORT
                log.warning(
                    "[SHM] 🚫 EARLY-ABORT '%s' — WR=%.0f%% after %d trades, total_r=%.2f"
                    " — HARD BLOCKED. Cooldown: %d sessions required.",
                    strategy_name, rec.win_rate * 100, rec.trades,
                    rec.total_r, EARLY_ABORT_COOLDOWN,
                )
            else:
                if rec.win_rate < MIN_WIN_RATE:
                    rec.disabled_reason = DISABLE_REASON_LOW_WIN_RATE
                elif rec.max_drawdown > MAX_DRAWDOWN:
                    rec.disabled_reason = DISABLE_REASON_HIGH_DD
                else:
                    rec.disabled_reason = DISABLE_REASON_LOW_SHARPE
                log.warning(
                    "[SHM] 🚫 DISABLED '%s' reason=%s — WR=%.0f%% DD=%.1f%% Sharpe=%.2f"
                    " — HARD BLOCKED from new signals.",
                    strategy_name, rec.disabled_reason,
                    rec.win_rate * 100, rec.max_drawdown * 100, rec.sharpe,
                )
        elif status in (HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.UNKNOWN):
            if rec.disabled_since:
                if rec._cooldown_satisfied:
                    log.info(
                        "[SHM] ✅ '%s' re-enabled — metrics recovered (was: %s, sessions=%d).",
                        strategy_name, rec.disabled_reason, rec.sessions_since_disabled,
                    )
                    rec.disabled_since          = None
                    rec.disabled_reason         = None
                    rec.disabled_at_trades      = None
                    rec.disabled_wr             = None
                    rec.disabled_total_r        = None
                    rec.sessions_since_disabled = 0
                else:
                    log.info(
                        "[SHM] ⏳ '%s' metrics recovering but cooldown not served"
                        " (%d/%d sessions) — still blocked.",
                        strategy_name, rec.sessions_since_disabled, EARLY_ABORT_COOLDOWN,
                    )

        # Advisory: convex / asymmetric-payoff strategy in watchlist
        if (status == HealthStatus.WARNING
                and rec.win_rate < EARLY_ABORT_MAX_WR
                and rec.total_r > 0):
            log.info(
                "[SHM] 📊 CONVEX_WATCH '%s' — WR=%.0f%% total_r=+%.2f"
                " (asymmetric payoff — advisory WARNING, execution continues).",
                strategy_name, rec.win_rate * 100, rec.total_r,
            )

        rec.last_updated = datetime.now().isoformat()
        self._save_db()
        return status

    def get_passing_strategies(self) -> Set[str]:
        """
        Returns the set of strategy names that are NOT disabled.
        UNKNOWN strategies (< 20 clean trades) are treated as passing —
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

    def get_disable_metadata(self, strategy_name: str) -> Dict[str, Any]:
        """
        Returns disable metadata for a strategy (empty dict if not disabled).
        Used by audit logs, analytics, and the health report.
        Disabled strategies remain tracked here — operational disable ≠ deletion.
        """
        rec = self._records.get(strategy_name)
        if rec is None:
            return {}
        cooldown_rem = 0
        if rec.disabled_reason == DISABLE_REASON_EARLY_ABORT:
            cooldown_rem = max(0, EARLY_ABORT_COOLDOWN - rec.sessions_since_disabled)
        return {
            "reason":                     rec.disabled_reason,
            "at_trades":                  rec.disabled_at_trades,
            "wr":                         rec.disabled_wr,
            "total_r":                    rec.disabled_total_r,
            "since":                      rec.disabled_since,
            "sessions_cooldown_remaining": cooldown_rem,
        }

    def tick_session(self) -> None:
        """
        Advance the session counter for all disabled strategies.
        Call once per trading day at EOD (from MasterOrchestrator._do_eod_learning).
        After EARLY_ABORT_COOLDOWN sessions the strategy becomes eligible for
        re-enable on the next trade that produces a passing status.
        """
        changed = False
        for name, rec in self._records.items():
            if rec.disabled_since is not None:
                rec.sessions_since_disabled += 1
                changed = True
                if (rec.disabled_reason == DISABLE_REASON_EARLY_ABORT
                        and rec.sessions_since_disabled == EARLY_ABORT_COOLDOWN):
                    log.info(
                        "[SHM] ⏰ '%s' cooldown complete (%d sessions). "
                        "Eligible for re-enable on next passing trade.",
                        name, EARLY_ABORT_COOLDOWN,
                    )
        if changed:
            self._save_db()

    def manual_override(self, strategy_name: str, enable: bool = True) -> None:
        """
        Operator tool — bypass cooldown and immediately enable or disable a strategy.
        Sets cooldown_override=True so status() ignores the cooldown gate.
        """
        rec = self._records.get(strategy_name)
        if rec is None:
            log.warning("[SHM] manual_override: unknown strategy '%s'.", strategy_name)
            return
        if enable:
            rec.disabled_since          = None
            rec.disabled_reason         = None
            rec.disabled_at_trades      = None
            rec.disabled_wr             = None
            rec.disabled_total_r        = None
            rec.sessions_since_disabled = 0
            rec.cooldown_override       = True
            log.warning("[SHM] 🔓 MANUAL ENABLE '%s' — cooldown bypassed.", strategy_name)
        else:
            rec.disabled_since      = datetime.now().isoformat()
            rec.disabled_reason     = DISABLE_REASON_MANUAL
            rec.disabled_at_trades  = rec.trades
            rec.disabled_wr         = rec.win_rate
            rec.disabled_total_r    = rec.total_r
            rec.cooldown_override   = True   # manual disable has no cooldown
            log.warning("[SHM] 🔒 MANUAL DISABLE '%s'.", strategy_name)
        self._save_db()

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
            HealthStatus.DISABLED: "🚫 DISABLED",
            HealthStatus.UNKNOWN:  "❓ WARMING_UP",
        }

        for name, rec in sorted(self._records.items()):
            status_label = _STATUS_LABEL.get(rec.status, "?")
            if rec.status == HealthStatus.DISABLED and rec.disabled_reason:
                cooldown_rem = (max(0, EARLY_ABORT_COOLDOWN - rec.sessions_since_disabled)
                                if rec.disabled_reason == DISABLE_REASON_EARLY_ABORT else 0)
                status_label += f" [{rec.disabled_reason}"
                if cooldown_rem > 0:
                    status_label += f" cooldown={cooldown_rem}s"
                status_label += "]"
            profile_tag = f"  [{rec.strategy_profile_type}]" if rec.strategy_profile_type != "UNKNOWN" else ""
            log.info(
                "  %-30s  %6d  %7.0f%%  %6.2f  %8.2f  %6.1f%%  %s%s",
                name, rec.trades, rec.win_rate * 100,
                rec.avg_r, rec.sharpe, rec.max_drawdown * 100,
                status_label, profile_tag,
            )

        n_healthy  = sum(1 for r in self._records.values() if r.status == HealthStatus.HEALTHY)
        n_warn     = sum(1 for r in self._records.values() if r.status == HealthStatus.WARNING)
        n_disabled = sum(1 for r in self._records.values() if r.status == HealthStatus.DISABLED)
        n_unknown  = sum(1 for r in self._records.values() if r.status == HealthStatus.UNKNOWN)
        disabled_names = self.get_disabled_strategies()

        log.info("  " + "─" * (w - 2))
        log.info(
            "  ✅ Healthy: %d  ⚠️ Warning: %d  🚫 Disabled: %d  ❓ Warming-up: %d",
            n_healthy, n_warn, n_disabled, n_unknown,
        )
        if disabled_names:
            for dname in sorted(disabled_names):
                meta = self.get_disable_metadata(dname)
                log.info(
                    "  [StrategyBlocked] %-28s  reason=%-22s wr=%.0f%%  trades=%s  total_r=%.2f",
                    dname, meta.get("reason", "?"),
                    (meta.get("wr") or 0) * 100,
                    meta.get("at_trades", "?"),
                    meta.get("total_r") or 0,
                )
        log.info(
            "  Thresholds — WinRate: >%.0f%%  MaxDD: <%.0f%%  Sharpe: >%.2f"
            "  MinTrades: %d  EarlyAbort: %d+ trades WR<%.0f%%+R<%.2f"
            "  | low-WR+positive-R → WARNING (not DISABLED)",
            MIN_WIN_RATE * 100, MAX_DRAWDOWN * 100, MIN_SHARPE, MIN_TRADES,
            EARLY_ABORT_MIN_TRADES, EARLY_ABORT_MAX_WR * 100, EARLY_ABORT_MIN_TOTAL_R,
        )
        log.info("═" * w)

        # Emit profile drift suggestions for strategies with enough realized trades.
        # These are advisory log lines only — they never modify strategy_profile_type.
        for name, rec in sorted(self._records.items()):
            suggested, confidence, reasoning = self._compute_profile_suggestion(rec)
            if suggested is None:
                continue
            if suggested != rec.strategy_profile_type:
                log.info(
                    "  [ProfileSuggestion] %-28s  current=%-22s  suggested=%-22s"
                    "  confidence=%s  reason=%s"
                    "  — advisory only, requires manual confirmation to apply.",
                    name, rec.strategy_profile_type, suggested, confidence, reasoning,
                )

    # ─────────────────────────────────────────────
    # PROFILE HEURISTICS  (read-only, never writes)
    # ─────────────────────────────────────────────

    def _compute_profile_suggestion(
        self, rec: "StrategyHealthRecord"
    ) -> "tuple[Optional[str], str, str]":
        """
        Derive a payoff-profile suggestion from realized trade distribution.
        Returns (suggested_profile, confidence, reasoning) or (None, '', '') if
        there is insufficient data or no meaningful suggestion can be made.

        CONTRACT:
          - NEVER modifies any field on rec or elsewhere.
          - NEVER auto-applies the suggestion; caller decides what to log.
          - Manual assignments in STRATEGY_PROFILES always remain authoritative.
          - Evolved EDG variants may drift behaviorally — this method helps detect
            that drift without silently relabelling them.

        Heuristic rules (all require >= PROFILE_SUGGEST_MIN_TRADES):
          LOW_WR_HIGH_R        WR < 40%  AND payoff_ratio >= 1.8  AND total_r > 0
          HIGH_WR_LOW_R        WR >= 55% AND payoff_ratio < 1.5
          MODERATE_WR_DEF_RISK 40% <= WR < 55% AND 0.8 <= payoff_ratio <= 2.5
          UNKNOWN              does not cleanly fit any profile

        Confidence levels: HIGH / MEDIUM / LOW
        """
        if rec.trades < PROFILE_SUGGEST_MIN_TRADES:
            return None, "", ""

        pnl = rec.recent_pnl
        winners = [p for p in pnl if p > 0]
        losers  = [abs(p) for p in pnl if p < 0]

        if not winners or not losers:
            return None, "", "insufficient winner/loser split in recent window"

        avg_w = mean(winners)
        avg_l = mean(losers)
        payoff_ratio = avg_w / avg_l if avg_l > 0 else 0.0
        wr = rec.win_rate

        # Sample size bonus: more trades → higher confidence
        trades_bonus = "HIGH" if rec.trades >= 50 else "MEDIUM" if rec.trades >= 30 else "LOW"

        if wr < 0.40 and payoff_ratio >= 1.8 and rec.total_r > 0:
            confidence = trades_bonus
            reasoning  = (
                f"WR={wr:.0%} payoff_ratio={payoff_ratio:.1f}x total_r=+{rec.total_r:.2f}"
                " → asymmetric convex payoff"
            )
            return "LOW_WR_HIGH_R", confidence, reasoning

        if wr >= 0.55 and payoff_ratio < 1.5:
            confidence = trades_bonus
            reasoning  = (
                f"WR={wr:.0%} payoff_ratio={payoff_ratio:.1f}x → high hit-rate low-R profile"
            )
            return "HIGH_WR_LOW_R", confidence, reasoning

        if 0.40 <= wr < 0.55 and 0.8 <= payoff_ratio <= 2.5:
            confidence = "LOW" if rec.trades < 50 else "MEDIUM"
            reasoning  = (
                f"WR={wr:.0%} payoff_ratio={payoff_ratio:.1f}x → balanced / defined-risk profile"
            )
            return "MODERATE_WR_DEF_RISK", confidence, reasoning

        # No clean fit
        return None, "", ""

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
            self._backfill_legacy()
            self._backfill_profiles()
        except Exception as exc:
            log.warning("[SHM] Could not load health DB: %s", exc)

    def _backfill_legacy(self) -> None:
        """
        One-time migration: stamp LEGACY_DISABLE_PRE_METADATA on any record that is
        functionally disabled (metrics breach threshold) but predates the metadata
        fields introduced in May 2026. Preserves historical honesty — does not
        fabricate an EARLY_ABORT reason retroactively.
        """
        patched = 0
        for name, rec in self._records.items():
            if rec.disabled_reason is not None:
                continue                                    # already has a reason
            if not (
                EARLY_ABORT_MIN_TRADES <= rec.trades < MIN_TRADES
                and rec.win_rate < EARLY_ABORT_MAX_WR
                and rec.total_r < 0
            ):
                continue                                    # not functionally disabled
            rec.disabled_reason    = "LEGACY_DISABLE_PRE_METADATA"
            rec.disabled_at_trades = rec.trades
            rec.disabled_wr        = rec.win_rate
            rec.disabled_total_r   = rec.total_r
            if rec.disabled_since is None:
                rec.disabled_since = "pre-metadata-deploy"
            patched += 1
            log.info(
                "[SHM] Backfilled legacy metadata for %s: reason=%s  trades=%d  wr=%.0f%%",
                name, rec.disabled_reason, rec.trades, rec.win_rate * 100,
            )
        if patched:
            self._save_db()

    def _backfill_profiles(self) -> None:
        """
        Stamp strategy_profile_type on existing records that predate the
        profile field (introduced May 2026).  Uses the STRATEGY_PROFILES
        lookup table; leaves UNKNOWN for strategies not in the table.
        """
        patched = 0
        for name, rec in self._records.items():
            if rec.strategy_profile_type != "UNKNOWN":
                continue
            profile = STRATEGY_PROFILES.get(name)
            if profile:
                rec.strategy_profile_type = profile
                patched += 1
        if patched:
            log.info("[SHM] Backfilled profile_type for %d strategies.", patched)
            self._save_db()

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
