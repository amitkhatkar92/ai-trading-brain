"""
Strategy Performance Tracker — Q3 Learning Mechanism 1
========================================================
Tracks every trade outcome and maintains running statistics per strategy.

What it tracks (per strategy)
──────────────────────────────
  • total trades
  • wins / losses
  • win rate (%)
  • average R-multiple (return in R units)
  • expectancy (win_rate × avg_win_R - loss_rate × avg_loss_R)
  • consecutive losses
  • last 20 trades (rolling)

Auto-disable rules
──────────────────
  A strategy is AUTO-DISABLED when ANY of these trigger:
    1. win_rate  < 35%   AND  trades >= MIN_SAMPLE
    2. expectancy < -0.3R AND  trades >= MIN_SAMPLE
    3. consecutive_losses >= 5

  Auto-enable (recovery) rules:
    • Disabled strategy may be re-tested after COOLDOWN_TRADES new trades
      by the system (paper mode, 2-trade micro-test batch)

Persistence
───────────
  Stats are stored in  data/strategy_performance.json
  and reloaded on startup so learning survives restarts.

Usage
──────
  tracker = StrategyPerformanceTracker()
  tracker.record_trade("Breakout_Volume", pnl_r=+1.8)
  tracker.record_trade("Mean_Reversion",  pnl_r=-1.0)
  print(tracker.get_table())              # full leaderboard
  active = tracker.get_active_strategies(["Breakout_Volume", "Mean_Reversion"])
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Tuning ────────────────────────────────────────────────────────────────────
MIN_SAMPLE          = 10      # need at least this many OFFICIAL trades to auto-disable
WIN_RATE_FLOOR      = 0.35    # below 35% win rate → disable
EXPECTANCY_FLOOR    = -0.30   # below -0.3R expectancy → disable
MAX_CONSEC_LOSSES   = 5       # 5 consecutive losses → disable
# ── Research Integrity Gate ─────────────────────────────────────────────────────────
# Minimum PREPARED_UNIVERSE_V1 trades required per strategy before ANY
# auto-disable, threshold mutation, or adaptive suppression may fire.
# LEGACY_STATIC trades (stale universe, proxy ATR, frozen levels) must not
# drive strategy governance decisions.
# Falls back to config value if available.
try:
    from config import MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT as _MIN_PREP_CFG
    MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT: int = _MIN_PREP_CFG
except Exception:
    MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT: int = 25
PERF_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "strategy_performance.json"
)
STABILITY_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "stability_ledger.json"
)

try:
    from config import BASELINE_CANDIDATE_DATE, STABILITY_REQUIRED_SESSIONS
except Exception:
    BASELINE_CANDIDATE_DATE    = "2026-04-27"
    STABILITY_REQUIRED_SESSIONS = 10


def _get_current_arch_gen() -> str:
    """Return the architecture generation for a trade being recorded right now."""
    try:
        from config import USE_PREPARED_UNIVERSE
        return "PREPARED_UNIVERSE_V1" if USE_PREPARED_UNIVERSE else "LEGACY_STATIC"
    except Exception:
        return "LEGACY_STATIC"


@dataclass
class StrategyStats:
    name:             str
    total_trades:     int   = 0
    wins:             int   = 0
    losses:           int   = 0
    total_r:          float = 0.0    # sum of R multiples
    win_r:            float = 0.0    # sum of positive R
    loss_r:           float = 0.0    # sum of negative R (stored positive)
    consec_losses:    int   = 0
    enabled:          bool  = True
    disabled_reason:  str   = ""
    last_trades:      List[float] = field(default_factory=list)   # last 20 R values
    last_updated:     str   = ""
    # ── Two-ledger separation ─────────────────────────────────────────────
    # official_trades: trades recorded ON or AFTER BASELINE_CANDIDATE_DATE.
    # Only these count toward auto-disable decisions.
    # total_trades includes all history (including the engineering-era records).
    official_trades:             int   = 0
    # prepared_universe_trades: trades with architecture_generation=PREPARED_UNIVERSE_V1.
    # This is the Research Integrity Gate: only these trades may trigger auto-disable,
    # threshold mutation, or adaptive suppression.  LEGACY_STATIC trades are weighted
    # at 0.25 and never count toward punitive governance decisions.
    prepared_universe_trades:    int   = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0

    @property
    def avg_r(self) -> float:
        return self.total_r / self.total_trades if self.total_trades else 0.0

    @property
    def avg_win_r(self) -> float:
        return self.win_r / self.wins if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        return self.loss_r / self.losses if self.losses else 0.0

    @property
    def expectancy(self) -> float:
        """Expected R per trade = win_rate × avg_win - loss_rate × avg_loss."""
        wr = self.win_rate
        lr = 1.0 - wr
        return round(wr * self.avg_win_r - lr * self.avg_loss_r, 4)

    def to_row(self) -> dict:
        return {
            "Strategy":        self.name,
            "Trades":          self.total_trades,
            "Win%":            f"{self.win_rate * 100:.1f}%",
            "Avg R":           f"{self.avg_r:+.2f}R",
            "Expectancy":      f"{self.expectancy:+.3f}R",
            "Consec Losses":   self.consec_losses,
            "Status":          "✅ ACTIVE" if self.enabled else f"⛔ DISABLED ({self.disabled_reason})",
        }


class StrategyPerformanceTracker:
    """
    Per-strategy P&L ledger with automatic disable/enable logic.
    """

    def __init__(self) -> None:
        self._stats: Dict[str, StrategyStats] = {}
        self._load()
        log.info("[StrategyPerformanceTracker] Loaded %d strategy records.", len(self._stats))

    # ── Public API ────────────────────────────────────────────────────────────

    def record_trade(self, strategy: str, pnl_r: float,
                     order_id: str = "",
                     architecture_generation: str = "") -> StrategyStats:
        """
        Record a completed trade for a strategy.

        Parameters
        ----------
        strategy : strategy name, e.g. "Breakout_Volume"
        pnl_r    : trade P&L in R multiples (+1.5 = win, -1.0 = loss)
        order_id : optional order ID for LearningGate integrity check

        Returns the updated StrategyStats.
        """
        # ── LearningGate ────────────────────────────────────────────────────
        # Only VERIFIED trades influence win rates, expectancy, and auto-disable.
        # LEGACY_UNVERIFIED / INVALID_MARKET_DATA / EXECUTION_INTEGRITY_FAILURE
        # trades are excluded to prevent contaminated data from corrupting
        # governance intelligence.
        if order_id:
            try:
                from data_integrity.trade_classifier import classify_trades, TradeClassification as _TC
                _cls_map = classify_trades()
                _cls = _cls_map.get(order_id)
                if _cls is not None and _cls != _TC.VERIFIED:
                    log.info(
                        "[LearningGate] PerfTracker EXCLUDED  "
                        "trade_id=%s  strategy=%s  classification=%s  "
                        "pnl_r=%.2fR  included=False",
                        order_id, strategy, _cls.value, pnl_r,
                    )
                    return self._get_or_create(strategy)   # return unchanged stats
                log.debug(
                    "[LearningGate] PerfTracker INCLUDED  "
                    "trade_id=%s  classification=%s  included=True",
                    order_id, _cls.value if _cls else "UNCLASSIFIED",
                )
            except Exception as _gate_exc:
                log.debug(
                    "[LearningGate] Classifier unavailable: %s — "
                    "proceeding without integrity filter.", _gate_exc,
                )
        # ────────────────────────────────────────────────────────────────────
        s = self._get_or_create(strategy)
        s.total_trades += 1
        s.total_r      += pnl_r
        s.last_trades   = (s.last_trades + [pnl_r])[-20:]  # keep last 20
        s.last_updated  = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Count toward official ledger if trade date is in the evaluation window
        try:
            from datetime import date as _date
            if _date.today() >= _date.fromisoformat(BASELINE_CANDIDATE_DATE):
                s.official_trades += 1
        except Exception:
            pass

        # Count toward prepared-universe ledger for Research Integrity Gate
        _gen = architecture_generation or ""
        if _gen == "PREPARED_UNIVERSE_V1" or (
            not _gen and _get_current_arch_gen() == "PREPARED_UNIVERSE_V1"
        ):
            s.prepared_universe_trades += 1

        # ── [ResearchIntegrity] telemetry ───────────────────────────────────────
        _mutation_blocked = (
            s.prepared_universe_trades < MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT
        )
        log.info(
            "[ResearchIntegrity] strategy=%s  generation=%s  "
            "prepared_trades=%d  min_required=%d  "
            "strategy_mutation_blocked=%s",
            strategy,
            _gen or "(inferred)",
            s.prepared_universe_trades,
            MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT,
            _mutation_blocked,
        )

        if pnl_r >= 0:
            s.wins      += 1
            s.win_r     += pnl_r
            s.consec_losses = 0
        else:
            s.losses    += 1
            s.loss_r    += abs(pnl_r)
            s.consec_losses += 1

        # ── Auto-disable checks ────────────────────────────────────────────
        if s.enabled:
            self._check_disable(s)

        self._save()
        log.info("[PerfTracker] %s | trade=%+.2fR | winrate=%.0f%% | E=%.3fR | status=%s",
                 strategy, pnl_r, s.win_rate * 100, s.expectancy,
                 "ACTIVE" if s.enabled else "DISABLED")
        return s

    def get_active_strategies(self, candidates: List[str]) -> List[str]:
        """Filter a list of strategy names to only those currently enabled."""
        result = []
        for name in candidates:
            s = self._stats.get(name)
            if s is None or s.enabled:
                result.append(name)   # unknown = assume active (no data yet)
        return result

    def get_disabled_set(self) -> set:
        """
        Return the set of strategy names that have been auto-disabled.
        Used by the orchestrator to subtract from the MSC passing_set.
        """
        return {name for name, s in self._stats.items() if not s.enabled}

    def get_performance_weight(self, strategy: str) -> float:
        """
        Return a capital-size multiplier (0.5 – 2.0) based on the strategy's
        live expectancy.  Used by PortfolioAllocationAI to tilt capital toward
        high-expectancy strategies and away from struggling ones.

        Formula  :  weight = clamp(1.0 + expectancy, 0.5, 2.0)
        Examples :
          E = +0.50R  →  1.5×  (strong — allocate more)
          E =  0.00R  →  1.0×  (neutral)
          E = −0.20R  →  0.8×  (weak but not retired)
          No data yet  →  1.0×  (prior = neutral)

        INTEGRITY RULE: Returns neutral (1.0) until MIN_SAMPLE official-window
        trades exist.  Engineering-era rows (Ledger A) must never tilt capital.
        """
        s = self._stats.get(strategy)
        if s is None or s.official_trades < MIN_SAMPLE:
            return 1.0   # prior: neutral — not enough official data yet
        return max(0.5, min(2.0, 1.0 + s.expectancy))

    def get_table(self) -> str:
        """Return a formatted leaderboard string (for logging / Telegram)."""
        if not self._stats:
            return "No strategy performance data yet."
        rows = sorted(self._stats.values(),
                      key=lambda s: s.expectancy, reverse=True)
        lines = [
            "📊 <b>Strategy Leaderboard</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for r in rows:
            row = r.to_row()
            lines.append(
                f"  <b>{row['Strategy']}</b>  "
                f"W:{row['Win%']}  AvgR:{row['Avg R']}  E:{row['Expectancy']}  "
                f"{row['Status']}"
            )
        return "\n".join(lines)

    def get_stats(self, strategy: str) -> Optional[StrategyStats]:
        return self._stats.get(strategy)

    def get_all_stats(self) -> Dict[str, StrategyStats]:
        return dict(self._stats)

    def re_enable(self, strategy: str) -> None:
        """Manually re-enable a disabled strategy (e.g. after regime change)."""
        if strategy in self._stats:
            self._stats[strategy].enabled        = True
            self._stats[strategy].disabled_reason = ""
            self._stats[strategy].consec_losses   = 0
            log.info("[PerfTracker] %s manually re-enabled.", strategy)
            self._save()

    # ── Auto-disable logic ────────────────────────────────────────────────────

    def _check_disable(self, s: StrategyStats) -> None:
        # Guard 1: require MIN_SAMPLE *official-window* trades before auto-disable.
        # Historical/engineering-era rows (Ledger A) must never disable a strategy.
        if s.official_trades < MIN_SAMPLE:
            return   # not enough official-window data yet

        # Guard 2: Research Integrity Gate — require MIN_PREPARED_UNIVERSE_TRADES
        # PREPARED_UNIVERSE_V1 trades before ANY per-strategy auto-disable fires.
        # LEGACY_STATIC trades (stale universe, proxy ATR, frozen levels) are
        # structurally biased and cannot safely drive strategy governance.
        if s.prepared_universe_trades < MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT:
            log.info(
                "[ResearchIntegrity] _check_disable BLOCKED for %s — "
                "prepared_trades=%d < min_required=%d  "
                "LEGACY_STATIC trades may not disable a strategy.",
                s.name, s.prepared_universe_trades,
                MIN_PREPARED_UNIVERSE_TRADES_FOR_STRATEGY_JUDGMENT,
            )
            return   # research integrity gate: protect strategy from legacy-data decisions

        # Guard 3: System-wide Adaptive Mutation Freeze (Patch 24).
        # Until total prepared trade count >= MIN_CLEAN_PREPARED_TRADES (100),
        # early telemetry distributions are statistically unstable.
        # Auto-disable during this phase risks overfitting noise.
        try:
            from learning_system.research_integrity import (
                is_clean_research_ready, emit_clean_research_state,
            )
            if not is_clean_research_ready():
                emit_clean_research_state(source="check_disable")
                log.info(
                    "[CleanResearchState] _check_disable FROZEN for %s — "
                    "system not yet clean-research-ready  "
                    "(prepared_trade_count < MIN_CLEAN_PREPARED_TRADES=%d)",
                    s.name, 100,
                )
                return   # adaptive mutation freeze: protect all strategies system-wide
        except Exception as _crs_exc:
            log.debug("[CleanResearchState] gate check skipped: %s", _crs_exc)

        reason = ""
        if s.win_rate < WIN_RATE_FLOOR:
            reason = f"win_rate={s.win_rate:.0%}<{WIN_RATE_FLOOR:.0%}"
        elif s.expectancy < EXPECTANCY_FLOOR:
            reason = f"expectancy={s.expectancy:.3f}R<{EXPECTANCY_FLOOR}R"
        elif s.consec_losses >= MAX_CONSEC_LOSSES:
            reason = f"{s.consec_losses} consecutive_losses"

        if reason:
            s.enabled        = False
            s.disabled_reason = reason
            log.warning("[PerfTracker] ⛔ AUTO-DISABLED: %s — %s", s.name, reason)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _get_or_create(self, strategy: str) -> StrategyStats:
        if strategy not in self._stats:
            self._stats[strategy] = StrategyStats(name=strategy)
        return self._stats[strategy]

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(PERF_FILE), exist_ok=True)
            data = {k: asdict(v) for k, v in self._stats.items()}
            with open(PERF_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            log.warning("[PerfTracker] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(PERF_FILE):
            return
        try:
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, raw in data.items():
                # Drop computed properties if they were accidentally serialised
                for computed in ("win_rate", "avg_r", "avg_win_r", "avg_loss_r", "expectancy"):
                    raw.pop(computed, None)
                # Backward-compat: backfill prepared_universe_trades for old records
                if "prepared_universe_trades" not in raw:
                    raw["prepared_universe_trades"] = 0
                self._stats[name] = StrategyStats(**raw)
        except Exception as exc:
            log.warning("[PerfTracker] Load failed: %s", exc)
        # Reconcile persisted enabled flag against authoritative thresholds.
        # Runs in a separate loop so a _check_disable error never wipes _stats.
        # Prevents a strategy with consec_losses >= MAX_CONSEC_LOSSES from
        # being incorrectly marked enabled=True after restart.
        for _s in list(self._stats.values()):
            try:
                self._check_disable(_s)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_TRACKER: Optional[StrategyPerformanceTracker] = None


def get_performance_tracker() -> StrategyPerformanceTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = StrategyPerformanceTracker()
    return _TRACKER


# ── Stability Ledger ──────────────────────────────────────────────────────────
# Tracks consecutive clean sessions to confirm when the evaluation baseline
# is trustworthy.  A session is "clean" unless flag_session_issue() is called
# before EOD.  After STABILITY_REQUIRED_SESSIONS consecutive clean sessions the
# baseline is confirmed and statistical trust is established.
#
# Two-ledger rule (enforced here and in _check_disable above):
#   Ledger A — Apr 15 → Apr 26  (engineering era, archive only, never counted)
#   Ledger B — Apr 27 onward    (official evaluation window)
#
# Stability stages:
#   Stage 1:  streak <  STABILITY_REQUIRED_SESSIONS  — machine proving it is stable
#   Stage 2:  streak >= STABILITY_REQUIRED_SESSIONS  — baseline confirmed, evaluate strategy
#   Stage 3:  30+ official closed trades             — optimisation decisions valid

class StabilityLedger:
    """
    Persistent session-stability counter.

    Call flag_session_issue(reason) any time a structural failure is detected
    during the trading session.  Call close_session() at EOD.

    If no issues were flagged, streak increments.
    If any issue was flagged, streak resets to 0.
    """

    def __init__(self) -> None:
        self.streak:             int  = 0
        self.candidate_date:     str  = BASELINE_CANDIDATE_DATE
        self.required:           int  = STABILITY_REQUIRED_SESSIONS
        self._today_issues:      list = []
        self._last_session_date: str  = ""
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def flag_session_issue(self, reason: str) -> None:
        """Mark the current session as dirty.  May be called multiple times."""
        log.warning("[StabilityLedger] ⚠️  Session issue flagged: %s", reason)
        self._today_issues.append(reason)

    def close_session(self) -> dict:
        """
        Called once at EOD.  Increments streak if session was clean, resets to 0
        if any issue was flagged.

        Returns a dict with: clean (bool), streak (int), confirmed (bool).
        """
        today     = datetime.now().strftime("%Y-%m-%d")
        was_clean = len(self._today_issues) == 0

        if was_clean:
            self.streak += 1
            log.info(
                "[StabilityLedger] ✅ Session %s CLEAN — streak=%d/%d%s",
                today, self.streak, self.required,
                "  🎯 BASELINE CONFIRMED" if self.is_confirmed() else "",
            )
        else:
            old = self.streak
            self.streak = 0
            log.warning(
                "[StabilityLedger] ❌ Session %s DIRTY (streak reset from %d). Issues: %s",
                today, old, " | ".join(self._today_issues),
            )

        self._today_issues      = []
        self._last_session_date = today
        self._save()

        return {
            "clean":     was_clean,
            "streak":    self.streak,
            "confirmed": self.is_confirmed(),
        }

    def is_confirmed(self) -> bool:
        """True once STABILITY_REQUIRED_SESSIONS consecutive clean sessions achieved."""
        return self.streak >= self.required

    def status_summary(self) -> str:
        """One-line status for logs and Telegram."""
        if self.is_confirmed():
            return (
                f"✅ BASELINE CONFIRMED — {self.streak} clean sessions "
                f"(since {self.candidate_date})"
            )
        remaining = self.required - self.streak
        return (
            f"🔄 Stability: Day {self.streak} of {self.required} "
            f"({remaining} more clean sessions needed) — "
            f"candidate since {self.candidate_date}"
        )

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(STABILITY_FILE)), exist_ok=True)
            with open(STABILITY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "streak":             self.streak,
                    "candidate_date":     self.candidate_date,
                    "last_session_date":  self._last_session_date,
                    "required":           self.required,
                }, f, indent=2)
        except Exception as exc:
            log.warning("[StabilityLedger] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(STABILITY_FILE):
            return
        try:
            with open(STABILITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.streak             = data.get("streak", 0)
            self.candidate_date     = data.get("candidate_date", BASELINE_CANDIDATE_DATE)
            self._last_session_date = data.get("last_session_date", "")
            self.required           = data.get("required", STABILITY_REQUIRED_SESSIONS)
            log.info(
                "[StabilityLedger] Loaded — streak=%d/%d  last_session=%s",
                self.streak, self.required, self._last_session_date,
            )
        except Exception as exc:
            log.warning("[StabilityLedger] Load failed: %s", exc)


_STABILITY_LEDGER: Optional[StabilityLedger] = None


def get_stability_ledger() -> StabilityLedger:
    global _STABILITY_LEDGER
    if _STABILITY_LEDGER is None:
        _STABILITY_LEDGER = StabilityLedger()
    return _STABILITY_LEDGER
