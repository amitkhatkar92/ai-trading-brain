"""
Market Simulation Engine — Scenario Generator
================================================
Generates predefined and random market scenarios used to stress-test
trade signals before they reach the Debate / Decision layer.

Standard scenarios cover the most historically significant market events
that could invalidate a trade plan:
  • Market Crash         — broad index selloff
  • Volatility Spike     — VIX surge, premium explosion
  • Liquidity Shock      — FII outflow, bid-ask widening
  • Sector Rotation      — money exits active sector
  • Gap Down             — overnight adverse gap
  • Trend Continuation   — market moves in trade direction
  • Rate Shock           — sudden RBI policy change impact
  • Black Swan           — tail-risk scenario
  • Sideways Chop        — choppy, no direction (good for range strategies)

Each scenario carries a probability_weight used by the Monte Carlo
engine to bias random sampling toward realistic market conditions.
"""

from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class Scenario:
    """
    A hypothetical market environment applied to the current snapshot.

    Attributes
    ----------
    name                   : machine-readable key
    label                  : display name
    price_change_pct       : expected Nifty move (e.g. -0.08 = -8 %)
    banknifty_change_pct   : expected BankNifty move
    vix_change             : absolute VIX point change (+12 = VIX surges)
    pcr_change             : absolute Put-Call-Ratio change
    breadth_change         : market breadth shift (-1 .. +1)
    description            : human-readable summary
    probability_weight     : relative weight for MC sampling (higher = more probable)
    beta_amplifier         : how much individual stocks amplify the index move
                             (1.0 = tracks index, 1.3 = high-beta stock)
    is_adverse             : True for bear scenarios (used in threshold logic)
    """
    name:                  str
    label:                 str
    price_change_pct:      float           # Nifty change
    banknifty_change_pct:  float
    vix_change:            float           # absolute
    pcr_change:            float           # absolute
    breadth_change:        float           # -1 to +1
    description:           str
    probability_weight:    float = 1.0
    beta_amplifier:        float = 1.2     # stock moves ~20 % more than index
    is_adverse:            bool  = True


class ScenarioGenerator:
    """
    Produces the set of deterministic scenarios for standard stress-testing,
    plus random scenarios for the Monte Carlo extension.
    """

    # ──────────────────────────────────────────────────────────────────
    # STANDARD SCENARIO CATALOGUE
    # ──────────────────────────────────────────────────────────────────

    SCENARIOS: List[Scenario] = [
        Scenario(
            name="crash",
            label="Market Crash",
            price_change_pct=-0.08,
            banknifty_change_pct=-0.10,
            vix_change=+12.0,
            pcr_change=+0.30,
            breadth_change=-0.40,
            description="Nifty -8%, BankNifty -10%, VIX +12 — broad selloff",
            probability_weight=0.08,
            beta_amplifier=1.4,
            is_adverse=True,
        ),
        Scenario(
            name="vol_spike",
            label="Volatility Spike",
            price_change_pct=-0.03,
            banknifty_change_pct=-0.04,
            vix_change=+10.0,
            pcr_change=+0.20,
            breadth_change=-0.25,
            description="VIX surges +10, moderate selloff, premium explosion",
            probability_weight=0.12,
            beta_amplifier=1.3,
            is_adverse=True,
        ),
        Scenario(
            name="liquidity_shock",
            label="Liquidity Shock",
            price_change_pct=-0.04,
            banknifty_change_pct=-0.05,
            vix_change=+7.0,
            pcr_change=+0.15,
            breadth_change=-0.20,
            description="Heavy FII outflow, bid-ask spread widens, Nifty -4%",
            probability_weight=0.10,
            beta_amplifier=1.25,
            is_adverse=True,
        ),
        Scenario(
            name="sector_rotation",
            label="Sector Rotation",
            price_change_pct=-0.01,
            banknifty_change_pct=-0.02,
            vix_change=+2.0,
            pcr_change=+0.05,
            breadth_change=-0.10,
            description="Money rotates sectors; active sector underperforms",
            probability_weight=0.15,
            beta_amplifier=1.5,    # sector stocks amplified more
            is_adverse=True,
        ),
        Scenario(
            name="gap_down",
            label="Gap Down Open",
            price_change_pct=-0.03,
            banknifty_change_pct=-0.035,
            vix_change=+5.0,
            pcr_change=+0.10,
            breadth_change=-0.15,
            description="Overnight news causes adverse gap, Nifty opens -3%",
            probability_weight=0.12,
            beta_amplifier=1.2,
            is_adverse=True,
        ),
        Scenario(
            name="trend_continuation",
            label="Trend Continuation",
            price_change_pct=+0.025,
            banknifty_change_pct=+0.030,
            vix_change=-1.5,
            pcr_change=-0.05,
            breadth_change=+0.15,
            description="Market rallies further, momentum continues",
            probability_weight=0.20,
            beta_amplifier=1.2,
            is_adverse=False,
        ),
        Scenario(
            name="rate_shock",
            label="Rate Shock",
            price_change_pct=-0.025,
            banknifty_change_pct=-0.045,
            vix_change=+6.0,
            pcr_change=+0.12,
            breadth_change=-0.18,
            description="Surprise RBI rate hike / global rate spike; banks hit hard",
            probability_weight=0.07,
            beta_amplifier=1.3,
            is_adverse=True,
        ),
        Scenario(
            name="black_swan",
            label="Black Swan",
            price_change_pct=-0.15,
            banknifty_change_pct=-0.18,
            vix_change=+25.0,
            pcr_change=+0.50,
            breadth_change=-0.60,
            description="Tail-risk event — extreme circuit-breaker-level selloff",
            probability_weight=0.03,
            beta_amplifier=1.6,
            is_adverse=True,
        ),
        Scenario(
            name="sideways_chop",
            label="Sideways Chop",
            price_change_pct=-0.005,
            banknifty_change_pct=-0.005,
            vix_change=+0.5,
            pcr_change=0.0,
            breadth_change=0.0,
            description="No direction, choppy action — trend trades struggle",
            probability_weight=0.13,
            beta_amplifier=1.1,
            is_adverse=True,    # adverse for trend trades, good for mean-reversion
        ),
        # ── Positive / neutral scenarios (calibrated to realistic bull-market
        #    probabilities so the scenario set is balanced) ─────────────────
        Scenario(
            name="bull_breakout_continuation",
            label="Bull Breakout Continuation",
            price_change_pct=+0.015,
            banknifty_change_pct=+0.018,
            vix_change=-1.0,
            pcr_change=-0.05,
            breadth_change=+0.10,
            description="Breakout holds, moderate follow-through (+1.5%)",
            probability_weight=0.18,
            beta_amplifier=1.2,
            is_adverse=False,
        ),
        Scenario(
            name="momentum_rally",
            label="Momentum Rally",
            price_change_pct=+0.030,
            banknifty_change_pct=+0.035,
            vix_change=-2.0,
            pcr_change=-0.08,
            breadth_change=+0.20,
            description="Strong momentum day — broad rally (+3%)",
            probability_weight=0.12,
            beta_amplifier=1.3,
            is_adverse=False,
        ),
        Scenario(
            name="positive_catalyst",
            label="Positive Catalyst",
            price_change_pct=+0.008,
            banknifty_change_pct=+0.010,
            vix_change=-0.5,
            pcr_change=-0.02,
            breadth_change=+0.08,
            description="Mild positive news — gentle upward drift (+0.8%)",
            probability_weight=0.10,
            beta_amplifier=1.1,
            is_adverse=False,
        ),
        Scenario(
            name="normal_buy_session",
            label="Normal Buy Session",
            price_change_pct=+0.004,
            banknifty_change_pct=+0.005,
            vix_change=0.0,
            pcr_change=0.0,
            breadth_change=+0.05,
            description="Quiet positive session, small cap-rotation (+0.4%)",
            probability_weight=0.10,
            beta_amplifier=1.0,
            is_adverse=False,
        ),
        Scenario(
            name="medium_rally",
            label="Medium Rally",
            price_change_pct=+0.020,
            banknifty_change_pct=+0.025,
            vix_change=-1.5,
            pcr_change=-0.06,
            breadth_change=+0.15,
            description="Above-average buy day — solid follow-through (+2%)",
            probability_weight=0.08,
            beta_amplifier=1.2,
            is_adverse=False,
        ),
    ]

    # ------------------------------------------------------------------

    def get_standard_scenarios(self) -> List[Scenario]:
        """Return the full deterministic scenario catalog."""
        return list(self.SCENARIOS)

    def get_adverse_scenarios(self) -> List[Scenario]:
        """Return only bear / stress scenarios (excluding trend_continuation)."""
        return [s for s in self.SCENARIOS if s.is_adverse]

    def generate_monte_carlo_scenarios(
        self,
        n: int = 1000,
        vix: float = 16.0,
        regime: str = "range_market",
    ) -> List[Scenario]:
        """
        Generate N random scenarios for Monte Carlo analysis.

        Price changes are drawn from a normal distribution where:
          • sigma is derived from current VIX (annualised vol)
          • scaled to a 5-trading-day horizon
          • bull regimes have a positive drift; bear regime a negative drift

        Returns a list of N lightweight Scenario objects.
        """
        annual_vol = vix / 100.0                  # e.g. VIX 16 → 16 % annual vol
        horizon_days = 5
        sigma = annual_vol * math.sqrt(horizon_days / 252.0)

        # Regime-based drift
        drift_map = {
            "bull_trend":    +0.004,
            "range_market":   0.000,
            "bear_market":   -0.005,
            "volatile":      -0.002,
        }
        drift = drift_map.get(regime, 0.0)

        scenarios: List[Scenario] = []
        for i in range(n):
            price_chg = random.gauss(drift, sigma)
            bnf_chg   = price_chg * random.uniform(1.0, 1.3)   # BNF slightly worse
            vix_chg   = -price_chg * random.uniform(4.0, 8.0)  # inverse VIX relationship
            pcr_chg   = -price_chg * random.uniform(0.5, 2.0)
            breadth_chg = price_chg * random.uniform(0.5, 1.5)

            scenarios.append(
                Scenario(
                    name=f"mc_{i:04d}",
                    label=f"MC-{i:04d}",
                    price_change_pct=price_chg,
                    banknifty_change_pct=bnf_chg,
                    vix_change=round(vix_chg, 2),
                    pcr_change=round(pcr_chg, 3),
                    breadth_change=round(breadth_chg, 3),
                    description=f"Monte Carlo run {i}",
                    probability_weight=1.0 / n,
                    beta_amplifier=random.uniform(1.0, 1.5),
                    is_adverse=price_chg < 0,
                )
            )
        return scenarios
