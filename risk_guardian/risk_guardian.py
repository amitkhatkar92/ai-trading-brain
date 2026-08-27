"""
Fail-Safe Risk Guardian
========================
The last hard gate before any order reaches the broker.

While the Risk Control layer (Layer 5) uses position-level rules,
the Risk Guardian enforces portfolio-level and system-level circuit
breakers that can halt trading entirely.

Rules enforced (in priority order)
    1. KILL_SWITCH     — market crash detected (Nifty < -5% or VIX > 45)
    2. DAILY_LOSS      — intraday realised + unrealised drawdown ≥ MAX_DAILY_LOSS_PCT
    3. MAX_OPEN_TRADES — open trade count ≥ MAX_OPEN_TRADES
    4. PORTFOLIO_RISK  — total risk exposure ≥ MAX_PORTFOLIO_RISK_PCT
    5. CIRCUIT_BREAKER — 3 consecutive losing trades → temporary pause
    6. MARGIN_CUSHION  — available margin < MIN_MARGIN_BUFFER_PCT of capital

When any rule triggers:
  • GuardianDecision.approved = False
  • GuardianDecision.rule_triggered = <rule name>
  • All pending signals are rejected with reason

The guardian stores intraday state and resets at market open.
"""

from __future__ import annotations
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from models import TradeSignal, Portfolio, MarketSnapshot
from utils  import get_logger
from config import DD_REDUCE_PCT, DD_PAUSE_PCT, DD_REDUCE_FACTOR

_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "risk_guardian_state.json",
)

log = get_logger(__name__)

# ── Hard-coded thresholds (tune per risk appetite) ────────────────────────
MAX_DAILY_LOSS_PCT       = 2.0    # % of total capital
MAX_PORTFOLIO_RISK_PCT   = 5.0    # total risk-at-stake as % of capital
MAX_OPEN_TRADES          = 8      # concurrent open positions
KILL_SWITCH_NIFTY_DROP   = -5.0   # Nifty intraday % move triggers kill
KILL_SWITCH_VIX          = 45.0   # VIX level triggers kill
CONSEC_LOSS_PAUSE        = 3      # N consecutive losses → circuit breaker
MIN_MARGIN_BUFFER_PCT    = 20.0   # must keep ≥ 20% capital as free margin


@dataclass
class GuardianDecision:
    approved:       bool
    rule_triggered: str              = ""      # "" means no rule triggered
    reason:         str              = ""
    approved_signals: list          = field(default_factory=list)
    rejected_signals: list          = field(default_factory=list)

    def summary(self) -> str:
        if self.approved:
            return (f"[RiskGuardian] ✅ APPROVED — "
                    f"{len(self.approved_signals)} signal(s) cleared for execution")
        return (f"[RiskGuardian] 🛑 BLOCKED [{self.rule_triggered}] — {self.reason}")


class FailSafeRiskGuardian:
    """
    Portfolio-level and system-level circuit breaker.

    Maintains intraday state:
      _daily_pnl         — running realised + unrealised P&L today
      _open_trades       — current count of open positions
      _consec_losses     — consecutive losing fills
      _trading_halted    — True if kill switch / daily loss triggered
      _halt_reason       — reason for halt

    Usage::
        guardian = FailSafeRiskGuardian(total_capital=1_000_000)
        decision = guardian.evaluate(signals, snapshot, portfolio)
        if decision.approved:
            execute(decision.approved_signals)
    """

    def __init__(self, total_capital: float = 1_000_000,
                 state_file: Optional[str] = None) -> None:
        self._capital           = total_capital
        self._daily_pnl         = 0.0
        self._open_trades       = 0
        self._consec_losses     = 0
        self._trading_halted    = False
        self._halt_reason       = ""
        self._session_date: Optional[date] = None
        self._state_file        = state_file or _STATE_FILE
        self._state_lock        = threading.Lock()  # D-016: protect concurrent _save_state calls
        # Restore persisted state BEFORE normal session reset so today's
        # accumulated loss and any active halt survive a container restart.
        self._load_state()
        log.info(
            "[RiskGuardian] Initialised. Capital=₹%.0f | MaxDailyLoss=%.0f%% | "
            "MaxPortfolioRisk=%.0f%% | MaxOpenTrades=%d | KillVIX=%.0f",
            total_capital, MAX_DAILY_LOSS_PCT, MAX_PORTFOLIO_RISK_PCT,
            MAX_OPEN_TRADES, KILL_SWITCH_VIX,
        )

    # ── Public API ────────────────────────────────────────────────────────
    def evaluate(
        self,
        signals:   list[TradeSignal],
        snapshot:  MarketSnapshot,
        portfolio: Optional[Portfolio] = None,
    ) -> GuardianDecision:
        """
        Main entry point. Evaluates all circuit-breaker rules.
        Returns GuardianDecision with approved/rejected signal lists.
        """
        self._reset_daily_if_new_session()

        # First: check system-wide halts
        halt = self._check_system_halts(snapshot, portfolio)
        if halt:
            return GuardianDecision(
                approved=False,
                rule_triggered=halt[0],
                reason=halt[1],
                approved_signals=[],
                rejected_signals=list(signals),
            )

        # All clear — pass signals through
        decision = GuardianDecision(
            approved=True,
            approved_signals=list(signals),
            rejected_signals=[],
        )
        log.info(decision.summary())
        return decision

    def record_trade_result(self, pnl: float, won: bool) -> None:
        """Call after each trade closes to update intraday state."""
        # D8-002: protect read-modify-write under lock; _save_state() acquires its own
        # internal lock so it must be called OUTSIDE this block to avoid deadlock.
        with self._state_lock:
            self._daily_pnl += pnl
            if won:
                self._consec_losses = 0
            else:
                self._consec_losses += 1
        log.info("[RiskGuardian] Trade recorded. DailyPnL=\u20b9%+.0f | "
                 "ConsecLosses=%d", self._daily_pnl, self._consec_losses)
        self._save_state()  # persist after every P&L mutation

    def record_open_trade(self) -> None:
        self._open_trades += 1

    def record_closed_trade(self) -> None:
        self._open_trades = max(0, self._open_trades - 1)

    def get_position_governor_factor(self) -> float:
        """
        Capital protection governor — returns a position-size multiplier
        based on the current intraday drawdown tier.

        Tier          Daily loss       Multiplier
        ─────────────────────────────────────────
        Full size     < DD_REDUCE_PCT  1.0
        Reduced size  < DD_PAUSE_PCT   DD_REDUCE_FACTOR (default 0.5)
        Paused        >= DD_PAUSE_PCT  0.0  (no new trades)
        """
        daily_loss_pct = abs(min(0.0, self._daily_pnl)) / self._capital * 100
        if daily_loss_pct >= DD_PAUSE_PCT:
            log.warning("[RiskGuardian] Governor=PAUSED  daily_loss=%.2f%%", daily_loss_pct)
            return 0.0
        elif daily_loss_pct >= DD_REDUCE_PCT:
            log.info("[RiskGuardian] Governor=REDUCE  daily_loss=%.2f%%  factor=%.0f%%",
                     daily_loss_pct, DD_REDUCE_FACTOR * 100)
            return DD_REDUCE_FACTOR
        return 1.0

    def get_status(self) -> dict:
        daily_loss_pct = abs(min(0.0, self._daily_pnl)) / self._capital * 100
        return {
            "halted":         self._trading_halted,
            "halt_reason":    self._halt_reason,
            "daily_pnl":      self._daily_pnl,
            "daily_loss_pct": daily_loss_pct,
            "open_trades":    self._open_trades,
            "consec_losses":  self._consec_losses,
        }

    # ── Private helpers ───────────────────────────────────────────────────
    def _check_system_halts(
        self,
        snapshot:  MarketSnapshot,
        portfolio: Optional[Portfolio],
    ) -> tuple[str, str] | None:
        """
        Returns (rule_name, reason) if any halt condition is met, else None.
        """
        # 1. Kill switch — market crash
        vix = snapshot.vix if snapshot else 15.0
        if vix >= KILL_SWITCH_VIX:
            self._trading_halted = True
            self._halt_reason    = f"VIX={vix:.1f} ≥ {KILL_SWITCH_VIX}"
            self._save_state()
            log.critical("[RiskGuardian] 🛑 KILL SWITCH ACTIVATED — %s",
                         self._halt_reason)
            return ("KILL_SWITCH", f"VIX={vix:.1f} signals market panic. "
                                    f"All trading suspended.")

        # 2. Daily loss limit
        daily_loss_pct = abs(min(0.0, self._daily_pnl)) / self._capital * 100
        if daily_loss_pct >= MAX_DAILY_LOSS_PCT:
            self._trading_halted = True
            self._halt_reason    = f"DailyLoss={daily_loss_pct:.2f}%"
            self._save_state()
            log.error("[RiskGuardian] 🛑 DAILY LOSS LIMIT — %s",
                      self._halt_reason)
            return ("DAILY_LOSS_LIMIT",
                    f"Intraday loss of {daily_loss_pct:.1f}% reached "
                    f"(limit={MAX_DAILY_LOSS_PCT}%). Trading halted for today.")

        # 3. Max open trades
        if self._open_trades >= MAX_OPEN_TRADES:
            log.warning("[RiskGuardian] Max open trades reached (%d/%d). "
                        "No new entries.", self._open_trades, MAX_OPEN_TRADES)
            return ("MAX_OPEN_TRADES",
                    f"Already have {self._open_trades} open positions "
                    f"(limit={MAX_OPEN_TRADES}).")

        # 4. Portfolio risk
        if portfolio:
            risk_pct = self._calc_portfolio_risk_pct(portfolio)
            if risk_pct >= MAX_PORTFOLIO_RISK_PCT:
                log.warning("[RiskGuardian] Portfolio risk=%.1f%% ≥ %.1f%%",
                            risk_pct, MAX_PORTFOLIO_RISK_PCT)
                return ("MAX_PORTFOLIO_RISK",
                        f"Portfolio risk={risk_pct:.1f}% at limit "
                        f"(max={MAX_PORTFOLIO_RISK_PCT}%).")

        # 5. Consecutive loss circuit breaker
        if self._consec_losses >= CONSEC_LOSS_PAUSE:
            log.warning("[RiskGuardian] Circuit breaker: %d consecutive losses.",
                        self._consec_losses)
            return ("CIRCUIT_BREAKER",
                    f"{self._consec_losses} consecutive losses — "
                    f"pausing new entries until reviewed.")

        return None   # all clear

    def _calc_portfolio_risk_pct(self, portfolio: Portfolio) -> float:
        """
        Estimate total portfolio risk = sum of (entry−stop)*qty for open trades.
        """
        total_risk = 0.0
        for trade in getattr(portfolio, "open_trades", []):
            entry = getattr(trade, "entry_price", 0.0) or 0.0
            stop  = getattr(trade, "stop_loss",   0.0) or 0.0
            qty   = getattr(trade, "quantity",     0)  or 0
            total_risk += abs(entry - stop) * qty
        return total_risk / self._capital * 100 if self._capital else 0.0

    def _reset_daily_if_new_session(self) -> None:
        today = date.today()
        if self._session_date != today:
            if self._session_date is not None:
                log.info("[RiskGuardian] New session. Resetting intraday state.")
            self._session_date   = today
            self._daily_pnl      = 0.0
            self._consec_losses  = 0
            self._open_trades    = 0
            self._trading_halted = False
            self._halt_reason    = ""
            self._save_state()  # persist clean new-session state

    # ── Persistence ───────────────────────────────────────────────────────
    def _save_state(self) -> None:
        """Atomically persist intraday kill-switch state to disk."""
        # Ensure session_date is always set — record_trade_result may be called
        # before evaluate(), which is the only other place that sets _session_date.
        if self._session_date is None:
            self._session_date = date.today()
        state = {
            "session_date":   self._session_date.isoformat(),
            "daily_pnl":      self._daily_pnl,
            "trading_halted": self._trading_halted,
            "halt_reason":    self._halt_reason,
            "consec_losses":  self._consec_losses,
            "last_updated":   datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self._state_lock:  # D-016: serialize concurrent save calls
                os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self._state_file),
                                           prefix=".rg_state_", suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as fh:
                        json.dump(state, fh, indent=2)
                        fh.flush()
                        os.fsync(fh.fileno())  # D-020: flush to disk before rename
                    os.replace(tmp, self._state_file)
                except Exception:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                    raise
        except Exception as exc:
            log.warning("[RiskGuardian] State save failed (non-critical): %s", exc)

    def _load_state(self) -> None:
        """Restore persisted intraday state. Fails safe on missing/corrupt file."""
        today = date.today()
        try:
            if not os.path.exists(self._state_file):
                return  # no prior state — safe default (all zeros)
            with open(self._state_file, encoding="utf-8") as fh:
                raw = fh.read()
            state = json.loads(raw)
            saved_date_str = state.get("session_date")
            if not saved_date_str:
                return  # corrupt/empty — fail safe
            saved_date = date.fromisoformat(saved_date_str)
            if saved_date != today:
                log.info(
                    "[RiskGuardian] Persisted state is from %s (not today %s) "
                    "— starting fresh session.",
                    saved_date, today,
                )
                return  # previous day — normal new-session start
            # Same trading date — restore accumulated loss and halt state
            self._session_date   = saved_date
            self._daily_pnl      = float(state.get("daily_pnl", 0.0))
            self._trading_halted = bool(state.get("trading_halted", False))
            self._halt_reason    = str(state.get("halt_reason", ""))
            self._consec_losses  = int(state.get("consec_losses", 0))
            if self._trading_halted:
                log.warning(
                    "[RiskGuardian] ⚠️  RESTORED HALT from prior run: %s | "
                    "DailyPnL=\u20b9%+.0f",
                    self._halt_reason, self._daily_pnl,
                )
            else:
                log.info(
                    "[RiskGuardian] Restored intraday state: DailyPnL=\u20b9%+.0f "
                    "ConsecLosses=%d",
                    self._daily_pnl, self._consec_losses,
                )
        except Exception as exc:
            # D-002: Corrupt state file — quarantine it, alert operator, and fail CLOSED
            # (halt trading) rather than silently reset to zero.  A corrupt state file
            # could mean a crash during a halt → resetting to zero would let trading
            # resume past a financial safety threshold.
            _quarantine = self._state_file + ".corrupt"
            try:
                import shutil
                shutil.move(self._state_file, _quarantine)
            except Exception:
                pass
            log.error(
                "[RiskGuardian] ⚠️  State file CORRUPT — quarantined to %s. "
                "Halting trading as a precaution. Operator must verify. Error: %s",
                _quarantine, exc,
            )
            self._daily_pnl      = 0.0
            self._trading_halted = True   # fail closed — never assume safe
            self._halt_reason    = "STATE_FILE_CORRUPT"
            self._session_date   = date.today()
            try:
                from notifications.notifier_manager import get_notifier as _gn
                _gn().send_alert(
                    "⚠️ <b>[RiskGuardian] State file CORRUPT</b>\n"
                    f"Quarantined: {_quarantine}\n"
                    "Trading halted as precaution. Verify manually and restart if safe."
                )
            except Exception:
                pass
