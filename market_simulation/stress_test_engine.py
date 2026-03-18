"""
Market Simulation Engine — Stress Test Engine
===============================================
Runs individual TradeSignals through a set of Scenarios to determine
how each trade would perform under each hypothetical market condition.

For every (signal, scenario) pair the engine:
  1. Computes the simulated price of the underlying after the scenario shock
  2. Determines the trade outcome (stop hit, target hit, stable, unstable)
  3. Calculates the R-multiple outcome under that scenario

Signal-type sensitivity mapping
---------------------------------
EQUITY        → price change = scenario.price_change_pct × beta_amplifier
FUTURES       → price change = scenario.price_change_pct × 1.0 (tracks index)
OPTIONS (CE)  → price change = scenario.price_change_pct × delta(≈0.5)
OPTIONS (PE)  → price change = −scenario.price_change_pct × delta(≈0.5)  [inverse]
SPREAD / ARB  → price change = scenario.price_change_pct × 0.25  [near-neutral]
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List

from models import TradeSignal, SignalDirection
from models.trade_signal import SignalType
from .scenario_generator import Scenario
from .market_simulator import SimulatedSnapshot


class TradeOutcome(str, Enum):
    TARGET_HIT  = "target_hit"    # price reached target — full profit
    STOP_HIT    = "stop_hit"      # stop loss triggered — managed loss
    UNSTABLE    = "unstable"      # adverse move but stop not yet hit
    STABLE      = "stable"        # holding within acceptable range


@dataclass
class ScenarioTestResult:
    """
    Result of testing a single TradeSignal against a single Scenario.

    Attributes
    ----------
    scenario          : the Scenario applied
    outcome           : TradeOutcome enum value
    simulated_price   : underlying price after scenario shock
    r_multiple        : outcome in risk units (positive = profit, negative = loss)
                        −1.0 = 1R loss (stop hit), +2.0 = 2R gain (target hit)
    price_impact_pct  : percentage price change applied to the underlying
    """
    scenario:        Scenario
    outcome:         TradeOutcome
    simulated_price: float
    r_multiple:      float
    price_impact_pct: float

    def is_survived(self) -> bool:
        """Trade is considered 'survived' if the stop was NOT hit."""
        return self.outcome != TradeOutcome.STOP_HIT

    def short_label(self) -> str:
        icons = {
            TradeOutcome.TARGET_HIT: "✅ target hit",
            TradeOutcome.STOP_HIT:   "🛑 stop hit  ",
            TradeOutcome.UNSTABLE:   "⚠️  unstable  ",
            TradeOutcome.STABLE:     "💚 stable    ",
        }
        return icons.get(self.outcome, self.outcome.value)


class StressTestEngine:
    """
    Applies every scenario to a signal and returns a list of
    ScenarioTestResult objects — one per scenario.

    Usage
    -----
    engine = StressTestEngine()
    results = engine.test_signal(signal, scenarios, sim_snapshot)
    """

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def test_signal(
        self,
        signal: TradeSignal,
        scenarios: List[Scenario],
        sim_snapshot: SimulatedSnapshot | None = None,   # reserved for future use
    ) -> List[ScenarioTestResult]:
        """
        Test one TradeSignal against every supplied Scenario.

        Returns a list of ScenarioTestResult objects (one per scenario).
        """
        results: List[ScenarioTestResult] = []
        for scenario in scenarios:
            result = self._test_one(signal, scenario)
            results.append(result)
        return results

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────────────────────────────

    def _test_one(
        self,
        signal: TradeSignal,
        scenario: Scenario,
    ) -> ScenarioTestResult:
        """Evaluate a single (signal, scenario) pair."""
        price_impact = self._compute_price_impact(signal, scenario)
        sim_price    = signal.entry_price * (1.0 + price_impact)
        risk         = self._risk(signal)            # entry → stop distance
        rr_ratio     = signal.risk_reward_ratio      # cached property

        # ── Compute R-multiple ─────────────────────────────────────────
        if risk > 0:
            if signal.direction in (SignalDirection.BUY,):
                r = (sim_price - signal.entry_price) / risk
            elif signal.direction in (SignalDirection.SELL, SignalDirection.SHORT,
                                      SignalDirection.HEDGE):
                # profit = entry going down → inverse
                r = (signal.entry_price - sim_price) / risk
            else:
                r = (sim_price - signal.entry_price) / risk
        else:
            r = 0.0

        # ── Classify outcome ───────────────────────────────────────────
        outcome = self._classify(signal, sim_price, r, rr_ratio)

        # STOP_HIT: cap loss at −1R (stop executed at stop price)
        # TARGET_HIT: cap gain at +RR (target executed at target)
        if outcome == TradeOutcome.STOP_HIT:
            r = -1.0
        elif outcome == TradeOutcome.TARGET_HIT:
            r = +rr_ratio

        return ScenarioTestResult(
            scenario=scenario,
            outcome=outcome,
            simulated_price=round(sim_price, 2),
            r_multiple=round(r, 3),
            price_impact_pct=round(price_impact * 100, 2),
        )

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_price_impact(signal: TradeSignal, scenario: Scenario) -> float:
        """
        Map scenario market move to the specific instrument's price change.

        Each instrument type has a different sensitivity to index moves:
          • Equity         — amplified by stock beta (scenario.beta_amplifier)
          • Futures        — 1:1 with index (no amplification)
          • Call Option    — delta ~0.5 (gain half the underlying move)
          • Put Option     — delta ~−0.5 (gain when market falls)
          • Spread / Arb   — near market-neutral (0.25× sensitivity)
        """
        sig_type = signal.signal_type if signal.signal_type else SignalType.EQUITY

        if sig_type == SignalType.FUTURES:
            return scenario.price_change_pct                         # tracks index 1:1

        if sig_type == SignalType.SPREAD:
            return scenario.price_change_pct * 0.25                  # near-neutral arb

        if sig_type == SignalType.OPTIONS:
            opt = (signal.option_type or "CE").upper()
            if opt == "PE":
                # Put options gain when market falls (inverse delta)
                return -scenario.price_change_pct * 0.50
            else:
                # Call options move with market at ~0.5 delta
                return scenario.price_change_pct * 0.50

        # Default: EQUITY — stock amplifies index move by beta
        return scenario.price_change_pct * scenario.beta_amplifier

    @staticmethod
    def _risk(signal: TradeSignal) -> float:
        """Absolute entry→stop distance (always positive)."""
        return abs(signal.entry_price - signal.stop_loss)

    @staticmethod
    def _classify(
        signal: TradeSignal,
        sim_price: float,
        r: float,
        rr_ratio: float,
    ) -> TradeOutcome:
        """
        Determine TradeOutcome from simulated price and R.

        BUY logic:
          stop_loss < entry < target
          → stop hit if sim_price ≤ stop_loss
          → target hit if sim_price ≥ target_price
          → unstable if trailing toward stop (r < −0.4)
          → stable otherwise

        SELL / SHORT logic (inverted):
          target < entry < stop_loss
          → stop hit if sim_price ≥ stop_loss
          → target hit if sim_price ≤ target_price
        """
        direction = signal.direction

        if direction == SignalDirection.BUY:
            if sim_price <= signal.stop_loss:
                return TradeOutcome.STOP_HIT
            if sim_price >= signal.target_price and signal.target_price > 0:
                return TradeOutcome.TARGET_HIT
            if r < -0.40:
                return TradeOutcome.UNSTABLE
            return TradeOutcome.STABLE

        elif direction in (SignalDirection.SELL, SignalDirection.SHORT,
                           SignalDirection.HEDGE):
            # For short trades stop_loss is above entry
            stop   = signal.stop_loss
            target = signal.target_price
            if sim_price >= stop and stop > signal.entry_price:
                return TradeOutcome.STOP_HIT
            if sim_price <= target and target > 0:
                return TradeOutcome.TARGET_HIT
            if r < -0.40:
                return TradeOutcome.UNSTABLE
            return TradeOutcome.STABLE

        # EXIT or unknown — treat as stable
        return TradeOutcome.STABLE
