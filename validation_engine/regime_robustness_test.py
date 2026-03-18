"""
Validation Engine — Regime Robustness Test
==========================================
A strategy that only works in bull markets will blow up during bear runs.
Institutional-grade strategies must be stress-tested across every regime.

Regimes tested (Indian equity market context):
  • BULL_TRENDING   — rising market, low VIX (~14), positive breadth
  • BEAR_TRENDING   — falling market, elevated VIX (~28), negative breadth
  • SIDEWAYS_CHOP   — range-bound, normal VIX (~18), mixed breadth
  • HIGH_VOLATILITY — spike events (Budget day, FOMC), VIX >30
  • RECOVERY        — post-crash recovery, improving breadth
  • ELECTION_RALLY  — pre/post election, extreme directional moves

Each regime applies a realistic P&L transformation to the base series,
simulating how the strategy would have fared in that environment.

Institutional standard:
  • Must be profitable in ≥ 4 of 6 regimes
  • No regime with return < –15% of capital (catastrophic failure threshold)
"""

from __future__ import annotations
import random
import statistics as _stats
from dataclasses import dataclass, field

from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
MIN_REGIMES_PASS    = 4        # must pass at least 4 of 6
CATASTROPHIC_LOSS   = -15.0   # % of capital — instant fail if any regime this bad
MIN_REGIME_RETURN   = 0.0     # profitable in regime = passed

# ── Regime definitions ─────────────────────────────────────────────────────
# Each regime has characteristic P&L transformation parameters:
#   drift      — daily directional bias (positive = helps trend strategies)
#   noise_mult — amplifies P&L randomness
#   win_bias   — shifts win/loss probability
REGIMES: dict[str, dict] = {
    "BULL_TRENDING": {
        "drift":       0.004,
        "noise_mult":  0.90,
        "win_bias":    0.08,
        "description": "Sustained uptrend, VIX ~14, positive breadth",
    },
    "BEAR_TRENDING": {
        "drift":       -0.006,
        "noise_mult":  1.30,
        "win_bias":    -0.12,
        "description": "Sustained downtrend, VIX ~28, negative breadth",
    },
    "SIDEWAYS_CHOP": {
        "drift":       0.000,
        "noise_mult":  1.10,
        "win_bias":    -0.05,
        "description": "Range-bound, VIX ~18, oscillating breadth",
    },
    "HIGH_VOLATILITY": {
        "drift":       -0.002,
        "noise_mult":  2.00,
        "win_bias":    -0.10,
        "description": "Spike events, VIX >30 (Budget day, FOMC, FII selloff)",
    },
    "RECOVERY": {
        "drift":       0.003,
        "noise_mult":  1.15,
        "win_bias":    0.05,
        "description": "Post-crash recovery, improving breadth & sentiment",
    },
    "ELECTION_RALLY": {
        "drift":       0.005,
        "noise_mult":  1.50,
        "win_bias":    0.10,
        "description": "Pre/post election — extreme moves, heightened VIX",
    },
}


@dataclass
class RegimePeriodResult:
    regime:       str
    n_trades:     int   = 0
    total_pnl:    float = 0.0
    return_pct:   float = 0.0
    win_rate:     float = 0.0
    passed:       bool  = False
    catastrophic: bool  = False
    description:  str   = ""


@dataclass
class RegimeRobustnessResult:
    strategy_name:    str
    regime_results:   list[RegimePeriodResult] = field(default_factory=list)
    pass_count:       int   = 0
    total_regimes:    int   = 0
    pass_rate_pct:    float = 0.0
    weakest_regime:   str   = ""
    best_regime:      str   = ""
    any_catastrophic: bool  = False
    passed:           bool  = False

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        cat     = "  ⚠️  CATASTROPHIC LOSS in some regime" if self.any_catastrophic else ""
        return (f"[RegimeRobust] {verdict} | {self.strategy_name} | "
                f"Regimes passed: {self.pass_count}/{self.total_regimes} "
                f"({self.pass_rate_pct:.0f}%)  "
                f"Weakest: {self.weakest_regime}{cat}")


class RegimeRobustnessTester:
    """
    Simulates strategy P&L in 6 market regimes and assesses robustness.

    Usage::
        tester = RegimeRobustnessTester()
        result = tester.run("MyStrategy", base_pnl_series, capital)
    """

    def __init__(self, seed: int = 17) -> None:
        self._rng = random.Random(seed)
        log.info("[RegimeRobustness] Initialised. Testing %d regimes.",
                 len(REGIMES))

    # ── Public API ────────────────────────────────────────────────────────
    def run(self, strategy_name: str, base_pnl: list[float],
            capital: float = 1_000_000) -> RegimeRobustnessResult:
        """
        Apply regime transformations to base P&L and evaluate each.
        """
        regime_results: list[RegimePeriodResult] = []

        for regime_name, profile in REGIMES.items():
            regime_pnl = self._transform(base_pnl, profile)
            rr         = self._evaluate(regime_name, regime_pnl, capital,
                                        profile["description"])
            regime_results.append(rr)
            tick  = "✅" if rr.passed else ("💀" if rr.catastrophic else "❌")
            log.info("[RegimeRobust] %s %-20s Return=%+.2f%%  WinRate=%.0f%%",
                     tick, regime_name, rr.return_pct, rr.win_rate)

        pass_count  = sum(1 for r in regime_results if r.passed)
        total       = len(regime_results)
        pass_rate   = pass_count / total * 100 if total else 0.0
        any_cat     = any(r.catastrophic for r in regime_results)

        worst = min(regime_results, key=lambda r: r.return_pct)
        best  = max(regime_results, key=lambda r: r.return_pct)

        passed = (pass_count >= MIN_REGIMES_PASS and not any_cat)

        result = RegimeRobustnessResult(
            strategy_name    = strategy_name,
            regime_results   = regime_results,
            pass_count       = pass_count,
            total_regimes    = total,
            pass_rate_pct    = round(pass_rate, 1),
            weakest_regime   = worst.regime,
            best_regime      = best.regime,
            any_catastrophic = any_cat,
            passed           = passed,
        )
        log.info(result.summary())
        return result

    # ── Private helpers ───────────────────────────────────────────────────
    def _transform(self, base_pnl: list[float],
                   profile: dict) -> list[float]:
        """Apply regime-specific scaling to the base P&L series."""
        rng        = self._rng
        drift      = profile["drift"]
        noise_mult = profile["noise_mult"]
        win_bias   = profile["win_bias"]

        transformed = []
        for p in base_pnl:
            bias_factor = 1 + win_bias if p > 0 else (1 - win_bias)
            noise       = rng.gauss(0, abs(p) * noise_mult * 0.12)
            p_new       = p * bias_factor * noise_mult + noise
            # Apply drift as additive term proportional to position size
            p_new      += abs(p) * drift * 10
            transformed.append(p_new)
        return transformed

    @staticmethod
    def _evaluate(regime: str, pnls: list[float],
                  capital: float, description: str) -> RegimePeriodResult:
        if not pnls:
            return RegimePeriodResult(regime=regime, description=description)

        total_pnl  = sum(pnls)
        return_pct = total_pnl / capital * 100
        wins       = [p for p in pnls if p > 0]
        win_rate   = len(wins) / len(pnls) * 100

        catastrophic = return_pct <= CATASTROPHIC_LOSS
        passed       = return_pct >= MIN_REGIME_RETURN and not catastrophic

        return RegimePeriodResult(
            regime       = regime,
            n_trades     = len(pnls),
            total_pnl    = round(total_pnl,  2),
            return_pct   = round(return_pct, 3),
            win_rate     = round(win_rate,   1),
            passed       = passed,
            catastrophic = catastrophic,
            description  = description,
        )
