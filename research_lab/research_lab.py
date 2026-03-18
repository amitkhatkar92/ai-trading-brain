"""
Research Lab — Experimental Strategy Sandbox
============================================
An isolated environment for testing new strategy ideas without any
risk to the live trading system.

The Research Lab is completely decoupled from the live cycle:
  • Uses its own in-memory order book
  • Never calls the real broker
  • Never mutates live portfolio state
  • Runs on historical or simulated data

Workflow:
  1. Register a new strategy (params dict + signal_fn callable)
  2. Run it on a list of MarketSnapshot objects
  3. Get a LabResult with P&L, win-rate, drawdown metrics
  4. Promote to production only if it passes promotion criteria

Promotion criteria (conservative defaults):
  • Total return      > 0%
  • Win rate          ≥ 50%
  • Max drawdown      < 15%
  • Sharpe ratio      > 0.8
  • Walk-forward pass ≥ 60%
"""

from __future__ import annotations
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Promotion gate thresholds ─────────────────────────────────────────────
PROMO_MIN_RETURN_PCT   =  0.0
PROMO_MIN_WIN_RATE     = 50.0
PROMO_MAX_DRAWDOWN_PCT = 15.0
PROMO_MIN_SHARPE       =  0.8
PROMO_MIN_WF_PASS_PCT  = 60.0


@dataclass
class LabTrade:
    """Simulated trade record within the research lab."""
    strategy_name: str
    entry_price:   float
    exit_price:    float
    qty:           int
    direction:     str    # "LONG" | "SHORT"
    entry_ts:      datetime = field(default_factory=datetime.now)
    exit_ts:       Optional[datetime] = None

    @property
    def pnl(self) -> float:
        mult = 1 if self.direction == "LONG" else -1
        return mult * (self.exit_price - self.entry_price) * self.qty

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return self.pnl / (self.entry_price * self.qty) * 100


@dataclass
class LabResult:
    strategy_name:     str
    trades:            list[LabTrade]
    total_return_pct:  float
    win_rate_pct:      float
    max_drawdown_pct:  float
    sharpe_ratio:      float
    wf_pass_pct:       float
    promoted:          bool
    promotion_notes:   list[str] = field(default_factory=list)

    def summary(self) -> str:
        promo = "✅ PROMOTED" if self.promoted else "❌ NOT PROMOTED"
        return (
            f"[ResearchLab] {promo} | {self.strategy_name} | "
            f"Return={self.total_return_pct:+.1f}% | "
            f"WinRate={self.win_rate_pct:.0f}% | "
            f"MaxDD={self.max_drawdown_pct:.1f}% | "
            f"Sharpe={self.sharpe_ratio:.2f}"
        )


@dataclass
class ExperimentConfig:
    """Configuration for one research experiment."""
    name:         str
    description:  str
    params:       dict
    initial_capital: float = 1_000_000.0
    created_at:   datetime = field(default_factory=datetime.now)
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


class ResearchLab:
    """
    Sandboxed strategy research environment.

    Usage::
        lab = ResearchLab()

        def my_signal_fn(snapshot, params):
            # return a list of hypothetical trades
            ...

        config = ExperimentConfig(
            name="MomentumV2",
            description="RSI + VWAP momentum with tighter stops",
            params={"rsi_period": 14, "stop_pct": 1.5},
        )
        result = lab.run_experiment(config, my_signal_fn, snapshots)
        if result.promoted:
            print("Ready for promotion to live system!")
    """

    def __init__(self) -> None:
        self._experiments:  list[ExperimentConfig] = []
        self._results:      list[LabResult]         = []
        self._promoted:     list[str]               = []
        log.info(
            "[ResearchLab] Initialised. Promotion gates: "
            "Return>%.0f%% | WinRate≥%.0f%% | MaxDD<%.0f%% | Sharpe>%.1f",
            PROMO_MIN_RETURN_PCT, PROMO_MIN_WIN_RATE,
            PROMO_MAX_DRAWDOWN_PCT, PROMO_MIN_SHARPE,
        )

    # ── Public API ────────────────────────────────────────────────────────
    def run_experiment(
        self,
        config:    ExperimentConfig,
        signal_fn: Callable,
        snapshots: list,
    ) -> LabResult:
        """
        Run a strategy signal function against a list of snapshots in
        a fully isolated paper-trading environment.

        signal_fn(snapshot, params) → list[dict] where each dict has:
          direction: "LONG"|"SHORT", entry: float, exit: float, qty: int
        """
        log.info("[ResearchLab] Starting experiment: %s (id=%s)",
                 config.name, config.experiment_id)
        self._experiments.append(config)

        trades: list[LabTrade] = []
        for snap in snapshots:
            try:
                raw_trades = signal_fn(snap, config.params)
                for t in (raw_trades or []):
                    trades.append(LabTrade(
                        strategy_name=config.name,
                        entry_price=float(t.get("entry", 0)),
                        exit_price=float(t.get("exit",  0)),
                        qty=int(t.get("qty", 1)),
                        direction=t.get("direction", "LONG"),
                    ))
            except Exception as exc:  # noqa: BLE001
                log.warning("[ResearchLab] Error in signal_fn for %s: %s",
                            config.name, exc)

        result = self._evaluate(config.name, trades, config.initial_capital)
        self._results.append(result)
        if result.promoted:
            self._promoted.append(config.name)
        log.info(result.summary())
        return result

    def get_summary(self) -> str:
        """Print a text summary of all experiments run so far."""
        if not self._results:
            return "[ResearchLab] No experiments run yet."
        lines = [
            f"[ResearchLab] {len(self._results)} experiment(s) run | "
            f"{len(self._promoted)} promoted"
        ]
        for r in self._results:
            lines.append(f"  {'✅' if r.promoted else '❌'} {r.strategy_name}: "
                         f"Return={r.total_return_pct:+.1f}%  "
                         f"WinRate={r.win_rate_pct:.0f}%  "
                         f"MaxDD={r.max_drawdown_pct:.1f}%  "
                         f"Sharpe={r.sharpe_ratio:.2f}")
        return "\n".join(lines)

    def promoted_strategies(self) -> list[str]:
        return list(self._promoted)

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _evaluate(name: str, trades: list[LabTrade],
                  capital: float) -> LabResult:
        if not trades:
            return LabResult(
                strategy_name=name, trades=[], total_return_pct=0.0,
                win_rate_pct=0.0, max_drawdown_pct=0.0,
                sharpe_ratio=0.0, wf_pass_pct=0.0, promoted=False,
                promotion_notes=["No trades generated"],
            )

        pnls       = [t.pnl for t in trades]
        total_pnl  = sum(pnls)
        wins       = sum(1 for p in pnls if p > 0)
        win_rate   = wins / len(trades) * 100

        # Cumulative equity curve & max drawdown
        equity      = capital
        peak        = capital
        max_dd      = 0.0
        for p in pnls:
            equity += p
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Sharpe (annualised, assuming ~250 trades/year as proxy)
        total_return_pct = total_pnl / capital * 100
        try:
            daily_ret  = [p / capital for p in pnls]
            mean_r     = statistics.mean(daily_ret)
            std_r      = statistics.stdev(daily_ret) if len(daily_ret) > 1 else 1e-9
            sharpe     = (mean_r / std_r) * (250 ** 0.5) if std_r > 0 else 0.0
        except statistics.StatisticsError:
            sharpe = 0.0

        # Walk-forward pass — split 60/40, check if OOS profitable
        split      = max(1, int(len(trades) * 0.6))
        oos_pnl    = sum(t.pnl for t in trades[split:])
        wf_pass    = 100.0 if oos_pnl > 0 else 0.0

        # Check promotion gates
        notes:  list[str] = []
        passes: list[bool] = []

        def gate(condition: bool, msg_pass: str, msg_fail: str) -> None:
            passes.append(condition)
            notes.append(f"{'✅' if condition else '❌'} "
                         f"{msg_pass if condition else msg_fail}")

        gate(total_return_pct > PROMO_MIN_RETURN_PCT,
             f"Return={total_return_pct:+.1f}% > 0%",
             f"Return={total_return_pct:+.1f}% ≤ 0%")
        gate(win_rate >= PROMO_MIN_WIN_RATE,
             f"WinRate={win_rate:.0f}% ≥ {PROMO_MIN_WIN_RATE:.0f}%",
             f"WinRate={win_rate:.0f}% < {PROMO_MIN_WIN_RATE:.0f}%")
        gate(max_dd < PROMO_MAX_DRAWDOWN_PCT,
             f"MaxDD={max_dd:.1f}% < {PROMO_MAX_DRAWDOWN_PCT:.0f}%",
             f"MaxDD={max_dd:.1f}% ≥ {PROMO_MAX_DRAWDOWN_PCT:.0f}%")
        gate(sharpe > PROMO_MIN_SHARPE,
             f"Sharpe={sharpe:.2f} > {PROMO_MIN_SHARPE:.1f}",
             f"Sharpe={sharpe:.2f} ≤ {PROMO_MIN_SHARPE:.1f}")
        gate(wf_pass >= PROMO_MIN_WF_PASS_PCT,
             f"WF={wf_pass:.0f}% ≥ {PROMO_MIN_WF_PASS_PCT:.0f}%",
             f"WF={wf_pass:.0f}% < {PROMO_MIN_WF_PASS_PCT:.0f}%")

        promoted = all(passes)
        return LabResult(
            strategy_name=name, trades=trades,
            total_return_pct=round(total_return_pct, 2),
            win_rate_pct=round(win_rate, 1),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 3),
            wf_pass_pct=wf_pass,
            promoted=promoted,
            promotion_notes=notes,
        )
