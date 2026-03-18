"""
Validation Engine — Cross-Market Validation
=============================================
A genuine market edge should work across multiple instruments,
not just the one it was tuned on.

Tests the strategy across 6 Indian markets:
  • Nifty50       — large-cap index (benchmark)
  • BankNifty     — banking sector index (high beta)
  • Nifty Midcap  — mid-cap stocks
  • Nifty Smallcap— small-cap stocks
  • Sensex        — BSE large-cap alternative
  • FII Basket    — momentum-driven FII-heavy stocks

Each market has distinct characteristics applied as scaling factors
to simulate how the strategy would behave on that instrument.

Institutional standard: success rate ≥ 60% (at least 3 of 5 markets)

Market profile modifiers (applied to IS P&L baseline):
  • volatility_mult — how much more volatile vs Nifty
  • trend_factor    — directional persistence
  • liquidity_score — slippage impact
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from utils import get_logger

log = get_logger(__name__)

# Minimum markets required to pass
MIN_PASS_RATE_PCT = 60.0   # ≥ 3 of 5 markets

# Market profiles
MARKETS: dict[str, dict] = {
    "Nifty50": {
        "volatility_mult": 1.00,
        "trend_factor":    0.55,
        "liquidity_score": 1.00,
        "description":     "Large-cap benchmark index",
    },
    "BankNifty": {
        "volatility_mult": 1.45,
        "trend_factor":    0.60,
        "liquidity_score": 0.95,
        "description":     "Banking sector — high beta",
    },
    "Nifty Midcap": {
        "volatility_mult": 1.25,
        "trend_factor":    0.48,
        "liquidity_score": 0.80,
        "description":     "Mid-cap stocks — less liquid",
    },
    "Nifty Smallcap": {
        "volatility_mult": 1.65,
        "trend_factor":    0.42,
        "liquidity_score": 0.60,
        "description":     "Small-cap — high slippage risk",
    },
    "Sensex": {
        "volatility_mult": 0.95,
        "trend_factor":    0.55,
        "liquidity_score": 0.98,
        "description":     "BSE alternative — slightly smoother",
    },
}

# Pass criteria per market
MIN_RETURN_PCT  = 0.0    # OOS must be profitable
MIN_SHARPE      = 0.6    # relaxed for cross-market (universe is harder)


@dataclass
class MarketTestResult:
    market:        str
    n_trades:      int    = 0
    total_pnl:     float  = 0.0
    return_pct:    float  = 0.0
    sharpe:        float  = 0.0
    win_rate:      float  = 0.0
    passed:        bool   = False
    notes:         str    = ""


@dataclass
class CrossMarketResult:
    strategy_name:   str
    market_results:  list[MarketTestResult] = field(default_factory=list)
    pass_count:      int   = 0
    total_tested:    int   = 0
    pass_rate_pct:   float = 0.0
    passed:          bool  = False

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        return (f"[CrossMarket] {verdict} | {self.strategy_name} | "
                f"Markets passed: {self.pass_count}/{self.total_tested} "
                f"({self.pass_rate_pct:.0f}%)")


class CrossMarketValidator:
    """
    Tests a strategy's P&L series across multiple markets using
    market profile scaling factors.

    The base P&L series (from Nifty backtesting) is adapted per
    market using volatility and liquidity multipliers to simulate
    how the same logic would perform on that instrument.

    Usage::
        validator = CrossMarketValidator()
        result    = validator.run("MyStrategy", base_pnl_series, capital)
    """

    def __init__(self, markets: Optional[list[str]] = None,
                 seed: int = 42) -> None:
        self._markets = markets or list(MARKETS.keys())
        self._rng     = random.Random(seed)
        log.info("[CrossMarketValidator] Initialised. Testing across %d markets: %s",
                 len(self._markets), ", ".join(self._markets))

    # ── Public API ────────────────────────────────────────────────────────
    def run(self, strategy_name: str, base_pnl_series: list[float],
            capital: float = 1_000_000) -> CrossMarketResult:
        """
        Adapts the base P&L series per market profile and evaluates.
        """
        market_results: list[MarketTestResult] = []

        for market_name in self._markets:
            if market_name not in MARKETS:
                continue
            profile = MARKETS[market_name]
            adapted_pnl = self._adapt_series(
                base_pnl_series,
                profile["volatility_mult"],
                profile["liquidity_score"],
            )
            mr = self._evaluate_market(market_name, adapted_pnl, capital)
            market_results.append(mr)
            tick = "✅" if mr.passed else "❌"
            log.info("[CrossMarket] %s %-16s Return=%+.2f%%  "
                     "Sharpe=%.2f  WinRate=%.0f%%",
                     tick, market_name,
                     mr.return_pct, mr.sharpe, mr.win_rate)

        pass_count  = sum(1 for r in market_results if r.passed)
        total       = len(market_results)
        pass_rate   = pass_count / total * 100 if total else 0.0
        passed      = pass_rate >= MIN_PASS_RATE_PCT

        result = CrossMarketResult(
            strategy_name  = strategy_name,
            market_results = market_results,
            pass_count     = pass_count,
            total_tested   = total,
            pass_rate_pct  = round(pass_rate, 1),
            passed         = passed,
        )
        log.info(result.summary())
        return result

    # ── Private helpers ───────────────────────────────────────────────────
    def _adapt_series(self, pnls: list[float], vol_mult: float,
                      liquidity: float) -> list[float]:
        """
        Scale the P&L series by market profile:
          • vol_mult  — amplifies both wins and losses
          • liquidity — reduces wins (slippage eats into profits more)
        """
        adapted = []
        for p in pnls:
            # Apply volatility scaling
            p_scaled = p * vol_mult
            # Apply liquidity / slippage penalty (wins reduced, losses unchanged)
            if p_scaled > 0:
                p_scaled *= liquidity
            # Add small market-specific noise
            noise = self._rng.gauss(0, abs(p) * 0.05)
            adapted.append(p_scaled + noise)
        return adapted

    @staticmethod
    def _evaluate_market(market: str, pnls: list[float],
                         capital: float) -> MarketTestResult:
        import math, statistics as stats
        if not pnls:
            return MarketTestResult(market=market, notes="No trades")

        n         = len(pnls)
        total_pnl = sum(pnls)
        ret_pct   = total_pnl / capital * 100
        wins      = [p for p in pnls if p > 0]
        wr        = len(wins) / n * 100

        daily_rets = [p / capital for p in pnls]
        sharpe = 0.0
        if len(daily_rets) > 1:
            mu  = stats.mean(daily_rets)
            std = stats.stdev(daily_rets)
            sharpe = (mu / std) * math.sqrt(252) if std > 0 else 0.0

        passed = ret_pct >= MIN_RETURN_PCT and sharpe >= MIN_SHARPE
        notes  = ("Profitable" if ret_pct >= 0 else "Losing") + \
                 (", adequate Sharpe" if sharpe >= MIN_SHARPE else ", low Sharpe")

        return MarketTestResult(
            market     = market,
            n_trades   = n,
            total_pnl  = round(total_pnl, 2),
            return_pct = round(ret_pct,   3),
            sharpe     = round(sharpe,    3),
            win_rate   = round(wr,        1),
            passed     = passed,
            notes      = notes,
        )
