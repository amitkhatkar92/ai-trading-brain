"""iios/investment/strategy/evaluation/signal_explanation.py
Explains the primary signals that drove a strategy's performance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.strategy.evaluation.trade import Trade


@dataclass(frozen=True)
class SignalExplanation:
    """Natural-language + structured explanation of strategy signal quality."""

    primary_edge: str                  # one-sentence description of the strategy's edge
    best_conditions: List[str]         # list of market conditions where it excels
    worst_conditions: List[str]        # list of conditions where it struggles
    entry_quality_notes: List[str]
    exit_quality_notes: List[str]
    symbols_performing_well: List[str]
    symbols_underperforming: List[str]
    holding_time_assessment: str       # e.g., "Optimal: 3–7 days"
    consistency_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_edge":            self.primary_edge,
            "best_conditions":         self.best_conditions,
            "worst_conditions":        self.worst_conditions,
            "entry_quality_notes":     self.entry_quality_notes,
            "exit_quality_notes":      self.exit_quality_notes,
            "symbols_performing_well": self.symbols_performing_well,
            "symbols_underperforming": self.symbols_underperforming,
            "holding_time_assessment": self.holding_time_assessment,
            "consistency_notes":       self.consistency_notes,
        }


class SignalExplainer:
    """Generates SignalExplanation from trade data."""

    def explain(self, trades: List[Trade]) -> SignalExplanation:
        if not trades:
            return SignalExplanation(
                primary_edge="Insufficient data",
                best_conditions=[],
                worst_conditions=[],
                entry_quality_notes=["No trades available for analysis"],
                exit_quality_notes=[],
                symbols_performing_well=[],
                symbols_underperforming=[],
                holding_time_assessment="Unknown",
                consistency_notes="No data",
            )

        winners = [t for t in trades if t.is_winner]
        losers = [t for t in trades if t.is_loser]
        win_rate = len(winners) / len(trades)

        # Holding time analysis
        win_hold = (
            sum(t.holding_days for t in winners) / len(winners)
            if winners else 0.0
        )
        loss_hold = (
            sum(t.holding_days for t in losers) / len(losers)
            if losers else 0.0
        )

        hold_note = (
            f"Winners held {win_hold:.1f}d on average vs losers {loss_hold:.1f}d"
        )

        # Per-symbol analysis
        sym_pnl: Dict[str, float] = {}
        for t in trades:
            sym_pnl[t.symbol] = sym_pnl.get(t.symbol, 0.0) + t.net_pnl

        sorted_syms = sorted(sym_pnl.items(), key=lambda x: x[1], reverse=True)
        good_syms = [s for s, p in sorted_syms if p > 0.0][:3]
        bad_syms = [s for s, p in sorted_syms if p < 0.0][:3]

        # Entry quality notes
        avg_entry_slip = (
            sum(abs(t.entry_slippage) for t in trades) / len(trades)
        )
        entry_notes = []
        if avg_entry_slip > 0.01:
            entry_notes.append(f"Entry slippage averages {avg_entry_slip:.4f}; consider limit orders")
        else:
            entry_notes.append("Entry slippage is acceptable")

        # Edge description
        if win_rate >= 0.60:
            edge = "High-win-rate strategy with consistent profitable entries"
        elif win_rate >= 0.45:
            edge = "Balanced strategy relying on favorable risk/reward ratio"
        else:
            edge = "Low-win-rate strategy requiring large winners to offset losses"

        # Consistency
        pnl_vals = [t.net_pnl for t in trades]
        mean_abs = sum(abs(p) for p in pnl_vals) / len(pnl_vals)
        if mean_abs > 0:
            from iios.investment.strategy.evaluation.performance_statistics import safe_std
            cov = safe_std(pnl_vals) / mean_abs
            if cov < 0.5:
                consistency = "High consistency; trade outcomes are predictable"
            elif cov < 1.0:
                consistency = "Moderate consistency; some variance in trade outcomes"
            else:
                consistency = "Low consistency; trade outcomes vary significantly"
        else:
            consistency = "Cannot assess consistency with zero mean outcome"

        return SignalExplanation(
            primary_edge=edge,
            best_conditions=["Trending markets", "High liquidity sessions"],
            worst_conditions=["Range-bound/choppy markets", "Low-volume gaps"],
            entry_quality_notes=entry_notes,
            exit_quality_notes=[
                f"Winning exits averaged {win_hold:.1f} days holding",
                f"Losing exits averaged {loss_hold:.1f} days holding",
            ],
            symbols_performing_well=good_syms,
            symbols_underperforming=bad_syms,
            holding_time_assessment=hold_note,
            consistency_notes=consistency,
        )
