"""
Arbitrage AI — Layer 3 Agent 3
================================
Detects market inefficiencies that can be exploited with near-zero risk.

Scans for:
  • Futures basis arbitrage (Futures > Fair Value → sell futures / buy spot)
  • ETF NAV arbitrage (ETF price ≠ NAV)
  • Index constituent divergence (stock lagging index)
"""

from __future__ import annotations
from typing import Any, Dict, List

from models.market_data  import MarketSnapshot
from models.trade_signal import TradeSignal, SignalDirection, SignalStrength, SignalType
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

# Simulated data
FUTURES_DATA: List[Dict[str, Any]] = [
    {"symbol": "NIFTY", "spot": 22500, "futures": 22610, "fair_value": 22560, "lot": 50},
    {"symbol": "BANKNIFTY", "spot": 48000, "futures": 48200, "fair_value": 48120, "lot": 15},
]

ETF_DATA: List[Dict[str, Any]] = [
    {"symbol": "NIFTYBEES", "etf_price": 224.8, "nav": 225.3, "lot": 1},
    {"symbol": "BANKBEES",  "etf_price": 481.5, "nav": 480.0, "lot": 1},
]


class ArbitrageAI:
    """Detects and signals low-risk arbitrage opportunities."""

    MIN_BASIS_POINTS = 5   # Minimum edge in basis points to signal

    def __init__(self):
        log.info("[ArbitrageAI] Initialised.")

    def scan(self, snapshot: MarketSnapshot) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        signals.extend(self._futures_basis_arb())
        signals.extend(self._etf_nav_arb())
        log.info("[ArbitrageAI] Found %d arbitrage opportunities.", len(signals))
        return signals

    # ─────────────────────────────────────────────
    # FUTURES BASIS ARBITRAGE
    # ─────────────────────────────────────────────

    def _futures_basis_arb(self) -> List[TradeSignal]:
        results = []
        for item in FUTURES_DATA:
            basis     = item["futures"] - item["fair_value"]
            basis_bps = (basis / item["spot"]) * 10_000

            if abs(basis_bps) < self.MIN_BASIS_POINTS:
                continue

            if basis > 0:   # Futures overpriced → sell futures / buy spot
                direction = SignalDirection.SHORT
                notes     = f"Sell futures | Basis: +{basis_bps:.1f} bps"
            else:           # Futures underpriced → buy futures / sell spot
                direction = SignalDirection.BUY
                notes     = f"Buy futures | Basis: {basis_bps:.1f} bps"

            results.append(TradeSignal(
                symbol       = item["symbol"],
                direction    = direction,
                signal_type  = SignalType.FUTURES,
                strength     = SignalStrength.MODERATE,
                entry_price  = item["futures"],
                stop_loss    = item["futures"] * (1.01 if direction == SignalDirection.SHORT else 0.99),
                target_price = item["fair_value"],
                strategy_name= "Futures_Basis_Arb",
                confidence   = 8.0,
                source_agent = "ArbitrageAI",
                notes        = notes,
            ))
        return results

    # ─────────────────────────────────────────────
    # ETF NAV ARBITRAGE
    # ─────────────────────────────────────────────

    def _etf_nav_arb(self) -> List[TradeSignal]:
        results = []
        for item in ETF_DATA:
            diff_bps = ((item["etf_price"] - item["nav"]) / item["nav"]) * 10_000

            if abs(diff_bps) < self.MIN_BASIS_POINTS:
                continue

            if item["etf_price"] < item["nav"]:    # ETF cheap → buy ETF
                direction = SignalDirection.BUY
                notes     = f"ETF discount | Diff: {diff_bps:.1f} bps"
            else:                                   # ETF expensive → buy NAV
                direction = SignalDirection.SELL
                notes     = f"ETF premium | Diff: {diff_bps:.1f} bps"

            results.append(TradeSignal(
                symbol       = item["symbol"],
                direction    = direction,
                signal_type  = SignalType.EQUITY,
                strength     = SignalStrength.WEAK,
                entry_price  = item["etf_price"],
                stop_loss    = item["etf_price"] * (0.995 if direction == SignalDirection.BUY else 1.005),
                target_price = item["nav"],
                strategy_name= "ETF_NAV_Arb",
                confidence   = 7.5,
                source_agent = "ArbitrageAI",
                notes        = notes,
            ))
        return results
