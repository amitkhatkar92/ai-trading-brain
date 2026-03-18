"""
Market Simulation Engine — Market Simulator
=============================================
Applies a Scenario to the current MarketSnapshot to produce a
SimulatedSnapshot representing what market conditions would look like
if that scenario materialised.

This allows downstream components (StressTestEngine, StrategyResilienceAI)
to evaluate a trade signal in the hypothetical environment rather than
the current one.

Key transformation:
  original_nifty   * (1 + scenario.price_change_pct) → simulated_nifty
  original_vix     + scenario.vix_change              → simulated_vix
  original_pcr     + scenario.pcr_change              → simulated_pcr
  original_breadth + scenario.breadth_change          → simulated_breadth (clamped 0-1)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional

from models import MarketSnapshot, RegimeLabel
from .scenario_generator import Scenario


@dataclass
class SimulatedSnapshot:
    """
    A hypothetical market state produced by applying a Scenario to a
    real MarketSnapshot.

    Attributes
    ----------
    original         : the real MarketSnapshot this was derived from
    scenario         : the Scenario that was applied
    nifty_price      : simulated Nifty LTP
    banknifty_price  : simulated BankNifty LTP
    vix              : simulated VIX level
    pcr              : simulated Put-Call Ratio
    breadth          : simulated market breadth (0–1)
    simulated_regime : inferred regime label in the simulated environment
    """
    original:          MarketSnapshot
    scenario:          Scenario
    nifty_price:       float
    banknifty_price:   float
    vix:               float
    pcr:               float
    breadth:           float
    simulated_regime:  RegimeLabel = RegimeLabel.RANGE_MARKET

    def summary(self) -> str:
        orig_nifty = self.original.indices.get("NIFTY", {}).get("ltp", 0)
        return (
            f"[SimSnapshot] Scenario={self.scenario.label} | "
            f"Nifty {orig_nifty:.0f}→{self.nifty_price:.0f} "
            f"({self.scenario.price_change_pct*100:+.1f}%) | "
            f"VIX {self.original.vix:.1f}→{self.vix:.1f} | "
            f"Regime={self.simulated_regime.value}"
        )


class MarketSimulator:
    """
    Transforms a real MarketSnapshot into a SimulatedSnapshot by
    applying a given Scenario's parameter shifts.

    Usage
    -----
    sim = MarketSimulator()
    sim_snap = sim.apply(snapshot, scenario)
    """

    # If there is no Nifty data, fall back to this base price
    _NIFTY_FALLBACK     = 22_000.0
    _BANKNIFTY_FALLBACK = 48_000.0

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def apply(
        self,
        snapshot: MarketSnapshot,
        scenario: Scenario,
    ) -> SimulatedSnapshot:
        """
        Apply scenario shocks to the snapshot.

        Returns a SimulatedSnapshot capturing the hypothetical state.
        """
        # Extract base prices
        nifty_ltp = self._extract_index(snapshot, "NIFTY", self._NIFTY_FALLBACK)
        bnf_ltp   = self._extract_index(snapshot, "BANKNIFTY", self._BANKNIFTY_FALLBACK)

        # Apply shocks
        sim_nifty  = nifty_ltp * (1.0 + scenario.price_change_pct)
        sim_bnf    = bnf_ltp   * (1.0 + scenario.banknifty_change_pct)
        sim_vix    = max(8.0, snapshot.vix + scenario.vix_change)
        sim_pcr    = max(0.3, min(3.0, snapshot.pcr + scenario.pcr_change))
        sim_breadth = max(0.0, min(1.0,
                          (snapshot.market_breadth or 0.5) + scenario.breadth_change))

        # Infer regime in the simulated environment
        sim_regime = self._infer_regime(
            orig_regime=snapshot.regime,
            price_change_pct=scenario.price_change_pct,
            sim_vix=sim_vix,
        )

        return SimulatedSnapshot(
            original=snapshot,
            scenario=scenario,
            nifty_price=round(sim_nifty, 2),
            banknifty_price=round(sim_bnf, 2),
            vix=round(sim_vix, 2),
            pcr=round(sim_pcr, 3),
            breadth=round(sim_breadth, 3),
            simulated_regime=sim_regime,
        )

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_index(
        snapshot: MarketSnapshot,
        key: str,
        fallback: float,
    ) -> float:
        """Pull LTP from snapshot.indices dict; fall back to a default if missing."""
        idx = snapshot.indices.get(key)
        if idx is None:
            return fallback
        if isinstance(idx, dict):
            return float(idx.get("ltp", fallback))
        return float(getattr(idx, "ltp", fallback))

    @staticmethod
    def _infer_regime(
        orig_regime: RegimeLabel,
        price_change_pct: float,
        sim_vix: float,
    ) -> RegimeLabel:
        """
        Heuristically classify the simulated regime.

        Rules (in priority order):
          1. VIX > 30                → VOLATILE
          2. price change < -5 %    → BEAR_MARKET
          3. price change > +2 %    → BULL_TREND
          4. abs(change) < 1 %      → RANGE_MARKET
          5. otherwise              → inherit original regime
        """
        if sim_vix >= 30:
            return RegimeLabel.VOLATILE
        if price_change_pct <= -0.05:
            return RegimeLabel.BEAR_MARKET
        if price_change_pct >= 0.02:
            return RegimeLabel.BULL_TREND
        if abs(price_change_pct) < 0.01:
            return RegimeLabel.RANGE_MARKET
        return orig_regime
