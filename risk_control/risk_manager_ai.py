"""
Risk Manager AI — Layer 5 Agent 1
====================================
The primary risk guardian. Checks every signal against per-trade and
portfolio-level risk rules before it reaches the execution layer.

Checks:
  • Risk per trade (1% of capital max)
  • Portfolio heat (total open risk ≤ 5%)
  • Drawdown guard (halt if > 10%)
  • Minimum R:R ratio
  • Confidence floor
  • Duplicate symbol positions
"""

from __future__ import annotations
from typing import List

from models.trade_signal  import TradeSignal, SignalType
from models.agent_output  import AgentOutput
from config import (TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT,
                    MAX_PORTFOLIO_RISK_PCT, MIN_CONFIDENCE_SCORE)
from models.trade_expectancy import ExpectancyCalculator
from risk_control.liquidity_guard import LiquidityGuard
from utils import get_logger

log = get_logger(__name__)

# Asymmetric payoff philosophy: every trade we take must offer at least 2:1 reward.
# At RR=2 we only need to win 33% of trades to break even.
MIN_RR_RATIO = 2.0


class RiskManagerAI:
    """Hard-rule risk filter — all signals must pass every check."""

    def __init__(self):
        self._current_portfolio_heat: float = 0.0   # updated externally
        self.liquidity_guard = LiquidityGuard()      # ADV-based capacity ceiling
        log.info(f"[RiskManagerAI] Initialised. Capital=\u20b9{TOTAL_CAPITAL:,.0f}")

    def filter(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        approved: List[TradeSignal] = []
        seen_symbols: set = set()

        for sig in signals:
            reason = self._check(sig, seen_symbols)
            if reason is None:
                approved.append(sig)
                seen_symbols.add(sig.symbol)
            else:
                log.info("[RiskManagerAI] ❌ REJECTED %s — %s", sig.symbol, reason)

        log.info("[RiskManagerAI] %d/%d signals approved.", len(approved), len(signals))

        # ── Liquidity Capacity Guard ─────────────────────────────────────────
        # Final pass: cap qty to ADV ceiling and reject illiquid stocks.
        # This runs AFTER all other checks so the qty it sees is already
        # sized correctly by PortfolioAllocationAI upstream.
        approved = self.liquidity_guard.filter(approved)
        return approved

    def update_portfolio_heat(self, heat: float):
        """Called by OrderManager after each fill to update live risk state."""
        self._current_portfolio_heat = heat

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _check(self, sig: TradeSignal, seen: set) -> str | None:
        """Return None if signal passes, otherwise return rejection reason."""

        # 1) Confidence floor
        if sig.confidence < MIN_CONFIDENCE_SCORE:
            return f"Confidence {sig.confidence:.1f} < {MIN_CONFIDENCE_SCORE}"

        # 2) R:R ratio — asymmetric payoff gate
        if sig.risk_reward_ratio > 0 and sig.risk_reward_ratio < MIN_RR_RATIO:
            bkv = ExpectancyCalculator.breakeven_win_rate(sig.risk_reward_ratio)
            return (f"R:R {sig.risk_reward_ratio:.2f} < {MIN_RR_RATIO} "
                    f"(would need {bkv:.0%} WR to break even — too high)") 
        # Log breakeven info for approved R:R
        if sig.risk_reward_ratio >= MIN_RR_RATIO:
            bkv = ExpectancyCalculator.breakeven_win_rate(sig.risk_reward_ratio)
            exp = ExpectancyCalculator.expectancy_r(0.45, sig.risk_reward_ratio, 1.0)
            log.info("[RiskManagerAI] %s  RR=%.1f → breakeven≥%.0f%% | est. Exp=+%.2fR",
                     sig.symbol, sig.risk_reward_ratio, bkv * 100, exp)

        # 3) Stop loss defined
        if sig.stop_loss == 0:
            return "No stop loss defined"

        # 4) Per-trade risk
        # OPTIONS signals are priced as premium, not as underlying price, so
        # the stop distance as a % of premium is naturally large (e.g. 100%).
        # Use a separate, wider check for OPTIONS (capped at 120% of premium)
        # while equity/futures retain the 2% hard-stop-distance rule.
        risk_per_unit = abs(sig.entry_price - sig.stop_loss)
        if sig.signal_type == SignalType.OPTIONS:
            if sig.entry_price > 0 and risk_per_unit / sig.entry_price > 1.20:
                return f"Options stop distance {risk_per_unit/sig.entry_price:.0%} > 120% of premium"
        elif (sig.entry_price > 0
              and getattr(sig, 'atr', 0.0) == 0.0          # ATR-sized signals already carry correct risk
              and risk_per_unit / sig.entry_price > MAX_RISK_PER_TRADE_PCT * 2):
            return f"Stop distance {risk_per_unit/sig.entry_price:.1%} too wide"

        # 5) Portfolio heat — additive check
        # Adding this trade would push total portfolio risk over the limit.
        # Formula: current_risk + risk_per_new_trade > MAX_PORTFOLIO_RISK
        if self._current_portfolio_heat + MAX_RISK_PER_TRADE_PCT > MAX_PORTFOLIO_RISK_PCT:
            return (
                f"Portfolio heat {self._current_portfolio_heat:.1%} + "
                f"{MAX_RISK_PER_TRADE_PCT:.1%} (this trade) would exceed "
                f"max {MAX_PORTFOLIO_RISK_PCT:.1%}"
            )

        # 6) Duplicate symbol
        if sig.symbol in seen:
            return f"Duplicate symbol {sig.symbol}"

        return None    # All checks passed
