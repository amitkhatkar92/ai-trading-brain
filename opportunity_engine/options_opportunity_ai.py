"""
Options Opportunity AI — Layer 3 Agent 2
==========================================
Scans options chains for high-probability options plays.

Looks for:
  • IV spikes (sell premium)
  • IV crush post-event (buy straddle before events)
  • Mispriced options (deep ITM time value inefficiency)
  • Spread opportunities: Bull Call, Bear Put, Iron Condor
  • Hedge opportunities against equity positions
"""

from __future__ import annotations
from typing import Any, Dict, List

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal, SignalDirection, SignalStrength, SignalType
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

# Simulated options data — replace with live options chain API
OPTIONS_WATCHLIST: List[Dict[str, Any]] = [
    {"symbol": "NIFTY",     "expiry": "2026-03-27", "atm_strike": 22500,
     "iv": 18.5, "historical_iv": 14.0, "pcr": 1.1, "ltp_index": 22500},

    {"symbol": "BANKNIFTY", "expiry": "2026-03-27", "atm_strike": 48000,
     "iv": 22.0, "historical_iv": 16.0, "pcr": 0.85, "ltp_index": 48000},
]


def _estimate_straddle_premium(atm: float, iv: float, dte_days: int = 17) -> float:
    """
    Black-Scholes approximation for ATM straddle premium.
    For ATM straddles: premium ≈ ATM × IV × sqrt(T) × (2/sqrt(2π)) ≈ ATM × IV × sqrt(T) × 0.798
    where T = dte / 252.
    Returns per-unit premium (not lot value).
    """
    import math
    T = max(dte_days, 1) / 252.0
    # ATM put + call each ≈ ATM × IV × sqrt(T) × 0.40 (simplified dual)
    premium = atm * (iv / 100.0) * math.sqrt(T) * 0.80
    return round(max(premium, 10.0), 2)


class OptionsOpportunityAI:
    """Identifies actionable options strategies."""

    IV_SPIKE_THRESHOLD    = 1.20   # IV > 120% of historical → sell premium
    IV_LOW_THRESHOLD      = 0.90   # IV < 90% of historical → buy options

    def __init__(self):
        log.info("[OptionsOpportunityAI] Initialised.")

    def scan(self, snapshot: MarketSnapshot) -> List[TradeSignal]:
        signals: List[TradeSignal] = []

        for opt in OPTIONS_WATCHLIST:
            iv_ratio = opt["iv"] / opt["historical_iv"] if opt["historical_iv"] else 1.0

            # ── Strategy 1: Sell premium on IV spike ─────────────────
            if iv_ratio >= self.IV_SPIKE_THRESHOLD:
                signals.append(self._sell_straddle(opt, iv_ratio))

            # ── Strategy 2: Buy straddle on low IV before event ───────
            elif iv_ratio <= self.IV_LOW_THRESHOLD and snapshot.events_today:
                signals.append(self._buy_straddle(opt, iv_ratio))

            # ── Strategy 3: Iron Condor in range market ───────────────
            elif (snapshot.regime == RegimeLabel.RANGE_MARKET
                  and snapshot.volatility in (VolatilityLevel.LOW, VolatilityLevel.MEDIUM)):
                signals.append(self._iron_condor(opt))

        log.info("[OptionsOpportunityAI] Found %d options setups.", len(signals))
        return signals

    # ─────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────

    def _sell_straddle(self, opt: Dict, iv_ratio: float) -> TradeSignal:
        strike  = opt["atm_strike"]
        premium = _estimate_straddle_premium(opt["ltp_index"], opt["iv"])
        # For a SHORT straddle (sell premium):
        #   entry_price  = premium received per unit
        #   stop_loss    = 2.0 × premium (stop if premium doubles against us)
        #   target_price = 0.2 × premium (close at 80% profit)
        # This gives R:R ≈ (premium - 0.2×premium) / (2×premium - premium) = 0.8:1
        # which is correct for premium-selling (high win-rate, small average win)
        return TradeSignal(
            symbol       = opt["symbol"],
            direction    = SignalDirection.SELL,
            signal_type  = SignalType.OPTIONS,
            strength     = SignalStrength.STRONG,
            entry_price  = premium,
            stop_loss    = round(premium * 2.0, 2),   # max loss: premium doubles
            target_price = round(premium * 0.20, 2),  # target: 80% premium decay
            confidence   = min(5.0 + iv_ratio * 2, 9.0),
            source_agent = "OptionsOpportunityAI",
            strike_price = float(strike),
            option_type  = "STRADDLE",
            notes        = f"IV ratio {iv_ratio:.2f}x — sell premium",
        )

    def _buy_straddle(self, opt: Dict, iv_ratio: float) -> TradeSignal:
        strike  = opt["atm_strike"]
        premium = _estimate_straddle_premium(opt["ltp_index"], opt["iv"])
        # For a LONG straddle (buy gamma before event):
        #   entry_price  = premium paid per unit
        #   stop_loss    = 0.5 × premium (cut loss if premium halves)
        #   target_price = 3.0 × premium (profit on a large event move)
        return TradeSignal(
            symbol       = opt["symbol"],
            direction    = SignalDirection.BUY,
            signal_type  = SignalType.OPTIONS,
            strength     = SignalStrength.MODERATE,
            entry_price  = premium,
            stop_loss    = round(premium * 0.50, 2),
            target_price = round(premium * 3.00, 2),
            confidence   = 6.5,
            source_agent = "OptionsOpportunityAI",
            strike_price = float(strike),
            option_type  = "STRADDLE",
            notes        = f"Low IV {iv_ratio:.2f}x before event — buy vol",
        )

    def _iron_condor(self, opt: Dict) -> TradeSignal:
        strike  = opt["atm_strike"]
        # Approximate IC credit = ~50% of ATM straddle premium (simplified)
        straddle_prem = _estimate_straddle_premium(opt["ltp_index"], opt["iv"])
        ic_credit     = round(straddle_prem * 0.50, 2)
        # For Iron Condor (SELL direction, SPREAD type):
        #   entry_price  = net credit received
        #   stop_loss    = 2.5 × credit (max loss if market breaks out)
        #   target_price = 0.20 × credit (close at 80% retained)
        return TradeSignal(
            symbol       = opt["symbol"],
            direction    = SignalDirection.SELL,
            signal_type  = SignalType.SPREAD,
            strength     = SignalStrength.MODERATE,
            entry_price  = ic_credit,
            stop_loss    = round(ic_credit * 2.50, 2),
            target_price = round(ic_credit * 0.20, 2),
            confidence   = 7.0,
            source_agent = "OptionsOpportunityAI",
            strike_price = float(strike),
            option_type  = "IRON_CONDOR",
            notes        = "Range market — collect theta via Iron Condor",
        )
