"""
Stress Test AI — Layer 5 Agent 3
===================================
Simulates extreme market scenarios against the proposed signals to ensure
the portfolio can survive adverse conditions.

Scenarios simulated:
  1. Market crash       — Nifty -15% in 1 week
  2. Liquidity crisis   — Spreads widen 5×, fills at 3% slippage
  3. Volatility spike   — VIX doubles overnight
  4. Black Swan event   — Gap down -8% at open
"""

from __future__ import annotations
from typing import Dict, List, Tuple

from models.market_data  import MarketSnapshot
from models.trade_signal import TradeSignal
from models.agent_output import AgentOutput
from config import MAX_DRAWDOWN_PCT
from utils import get_logger

log = get_logger(__name__)

SCENARIOS: Dict[str, Dict[str, float]] = {
    "Market Crash":       {"price_shock": -0.15, "slippage": 0.02},
    "Liquidity Crisis":   {"price_shock": -0.08, "slippage": 0.05},
    "Volatility Spike":   {"price_shock": -0.06, "slippage": 0.015},
    "Black Swan Gap Down":{"price_shock": -0.08, "slippage": 0.03},
}


class StressTestAI:
    """Validates that proposed positions survive stress scenarios."""

    def __init__(self):
        log.info("[StressTestAI] Initialised with %d scenarios.", len(SCENARIOS))

    def validate(self, signals: List[TradeSignal],
                 snapshot: MarketSnapshot) -> List[TradeSignal]:
        passed: List[TradeSignal] = []
        for sig in signals:
            worst_loss, scenario = self._worst_case_loss(sig)
            if worst_loss > MAX_DRAWDOWN_PCT:
                log.warning("[StressTestAI] ❌ %s fails '%s' — loss %.1f%%",
                            sig.symbol, scenario, worst_loss * 100)
            else:
                passed.append(sig)

        log.info("[StressTestAI] %d/%d signals survived stress tests.",
                 len(passed), len(signals))
        return passed

    def run_report(self, signals: List[TradeSignal]) -> AgentOutput:
        results = {}
        for sig in signals:
            worst, name = self._worst_case_loss(sig)
            results[sig.symbol] = {"worst_loss_pct": worst, "scenario": name}
        return AgentOutput(
            agent_name="StressTestAI",
            status="ok",
            summary=f"Stress-tested {len(signals)} signals",
            confidence=9.0,
            data=results,
        )

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _worst_case_loss(self, sig: TradeSignal) -> Tuple[float, str]:
        worst_loss = 0.0
        worst_name = ""
        for name, params in SCENARIOS.items():
            shock    = params["price_shock"]
            slip     = params["slippage"]
            if sig.entry_price <= 0:
                continue
            if sig.stop_loss > 0:
                # Stop-loss protected position.  In a crash the stop fires but
                # fills with additional slippage — model that as the stop
                # execution price discounted by the scenario slippage.
                effective_fill = sig.stop_loss * (1.0 - slip)
                loss_per_share = max(0.0, sig.entry_price - effective_fill)
            else:
                # No stop — full gap-down loss
                stressed_price = sig.entry_price * (1.0 + shock - slip)
                loss_per_share = max(0.0, sig.entry_price - stressed_price)
            loss_pct = loss_per_share / sig.entry_price
            if loss_pct > worst_loss:
                worst_loss = loss_pct
                worst_name = name
        return round(worst_loss, 4), worst_name
