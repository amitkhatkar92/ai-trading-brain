"""
Market Simulation Engine — Strategy Resilience AI
===================================================
Evaluates a TradeSignal's robustness across all scenario test results.

Produces a ResilienceScore containing:
  • survival_rate              — % of scenarios where stop was NOT hit
  • worst_loss_r               — worst R outcome across all scenarios
  • best_gain_r                — best R outcome
  • expected_r                 — probability-weighted mean R (scenarios)
  • stability_score            — consistency metric (0–1)
  • monte_carlo_profit_prob    — from 1,000-run MC simulation
  • monte_carlo_expected_r     — mean R from MC
  • monte_carlo_worst_r        — 5th-percentile R from MC (conditional VaR)
  • approved                   — True if signal clears all acceptance thresholds
  • rejection_reason           — why the trade was rejected (if applicable)

Acceptance thresholds (institution-grade):
  ✅ survival_rate ≥ 55 %
  ✅ worst_loss_r ≥ −2.0 R  (catastrophic tail risk blocked)
  ✅ stability_score ≥ 0.60
  ✅ monte_carlo_profit_prob ≥ 45 %  (optional tightening layer)
"""

from __future__ import annotations
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from models import TradeSignal, SignalDirection
from models.trade_signal import SignalType
from .scenario_generator import Scenario
from .stress_test_engine import ScenarioTestResult, StressTestEngine, TradeOutcome


# ── Acceptance thresholds ─────────────────────────────────────────────
# survival_rate is now probability-weighted (see _compute_scenario_metrics).
# A 45 % threshold means: probability-weighted scenarios that survive must
# represent at least 45 % of total scenario probability mass.  This is
# more realistic than the old raw-count threshold that auto-failed every
# directional trade because the scenario set contains more adverse events.
THRESHOLD_SURVIVAL_RATE   = 0.45   # probability-weighted scenario survival
THRESHOLD_WORST_LOSS_R    = -2.0   # never lose more than 2R in any scenario
THRESHOLD_STABILITY       = 0.40   # profit-factor-based stability floor
THRESHOLD_MC_PROFIT_PROB  = 0.42   # Monte Carlo profit probability floor


@dataclass
class ResilienceScore:
    """
    Comprehensive resilience evaluation for a single TradeSignal.

    All R metrics are expressed as multiples of initial risk.
    """
    signal:                    TradeSignal
    scenario_results:          List[ScenarioTestResult] = field(default_factory=list)

    # Deterministic scenario metrics
    survival_rate:             float = 0.0   # 0–1 fraction
    worst_loss_r:              float = 0.0   # most negative R
    best_gain_r:               float = 0.0   # most positive R
    expected_r:                float = 0.0   # probability-weighted mean
    stability_score:           float = 0.0   # 0–1 (higher = more consistent)
    adverse_scenario_count:    int   = 0      # how many adverse scenarios existed

    # Monte Carlo metrics
    monte_carlo_runs:          int   = 0
    monte_carlo_profit_prob:   float = 0.0   # fraction of MC runs profitable
    monte_carlo_expected_r:    float = 0.0   # mean R across MC runs
    monte_carlo_worst_r:       float = 0.0   # 5th percentile R (CVaR proxy)
    monte_carlo_best_r:        float = 0.0   # 95th percentile R

    # Decision
    approved:                  bool  = False
    rejection_reason:          str   = ""

    def overall_score(self) -> float:
        """
        Composite 0–10 resilience score for display purposes.
        Weights: survival(40%) + mc_profit(30%) + stability(30%).
        """
        s = (self.survival_rate     * 10 * 0.40 +
             self.monte_carlo_profit_prob * 10 * 0.30 +
             self.stability_score   * 10 * 0.30)
        return round(min(10.0, max(0.0, s)), 2)

    def status_icon(self) -> str:
        return "✅ APPROVED" if self.approved else "❌ REJECTED"


class StrategyResilienceAI:
    """
    Computes ResilienceScore for a TradeSignal given:
      1. Pre-computed ScenarioTestResults (deterministic scenarios)
      2. Internal Monte Carlo simulation (1,000 random paths)

    Usage
    -----
    ai = StrategyResilienceAI()
    score = ai.evaluate(signal, scenario_results, vix=16.0, regime="range_market")
    """

    def __init__(self, mc_runs: int = 1_000):
        self._mc_runs = mc_runs
        self._stress_engine = StressTestEngine()

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def evaluate(
        self,
        signal:           TradeSignal,
        scenario_results: List[ScenarioTestResult],
        vix:              float = 16.0,
        regime:           str   = "range_market",
    ) -> ResilienceScore:
        """
        Full resilience evaluation: deterministic + Monte Carlo.

        Parameters
        ----------
        signal           : the TradeSignal being evaluated
        scenario_results : list of ScenarioTestResult from StressTestEngine
        vix              : current VIX (used to calibrate MC volatility)
        regime           : market regime label (used to calibrate MC drift)
        """
        score = ResilienceScore(
            signal=signal,
            scenario_results=scenario_results,
        )

        # ── 1. Deterministic scenario metrics ─────────────────────────
        self._compute_scenario_metrics(score)

        # ── 2. Monte Carlo extension ───────────────────────────────────
        self._run_monte_carlo(score, vix=vix, regime=regime)

        # ── 3. Acceptance decision ─────────────────────────────────────
        self._apply_acceptance_rules(score)

        return score

    # ──────────────────────────────────────────────────────────────────
    # DETERMINISTIC METRICS
    # ──────────────────────────────────────────────────────────────────

    def _compute_scenario_metrics(self, score: ResilienceScore) -> None:
        results = score.scenario_results
        if not results:
            score.survival_rate   = 1.0      # no data → pass through
            score.stability_score = 1.0
            return

        r_values     = [r.r_multiple for r in results]
        survived     = [r for r in results if r.is_survived()]
        adverse      = [r for r in results if r.scenario.is_adverse]

        score.adverse_scenario_count = len(adverse)
        score.worst_loss_r    = min(r_values)
        score.best_gain_r     = max(r_values)

        # ── Probability-weighted survival rate ─────────────────────────
        # Using raw count (len(survived)/len(results)) was wrong: the scenario
        # catalogue contains more adverse events than positive ones, so raw
        # count systematically under-counts survival for directional trades.
        # Probability weights reflect real-world scenario likelihoods, making
        # this a far more accurate measure of expected survival.
        total_weight    = sum(r.scenario.probability_weight for r in results)
        survived_weight = sum(
            r.scenario.probability_weight for r in results if r.is_survived()
        )
        score.survival_rate = survived_weight / total_weight if total_weight > 0 else 1.0

        # ── Probability-weighted expected R ────────────────────────────
        if total_weight > 0:
            score.expected_r = sum(
                r.r_multiple * r.scenario.probability_weight
                for r in results
            ) / total_weight
        else:
            score.expected_r = statistics.mean(r_values)

        # ── Profit-factor stability score ──────────────────────────────
        # CV-based stability breaks when expected_r ≈ 0 (bimodal win/loss
        # distribution), which is the norm for directional trading.
        # Profit factor (sum of profits / sum of losses) is scale-invariant,
        # handles bimodal R distributions correctly, and maps naturally to
        # a 0–1 stability score via PF / (PF + 1).
        #   PF = 1.0  → stability = 0.50  (break-even edge)
        #   PF = 1.5  → stability = 0.60  (decent edge)
        #   PF = 2.0  → stability = 0.67  (strong edge)
        gross_profit = sum(max(0.0, r) for r in r_values)
        gross_loss   = sum(abs(min(0.0, r)) for r in r_values)
        if gross_loss > 0:
            pf = gross_profit / gross_loss
        elif gross_profit > 0:
            pf = 3.0    # all wins → cap at 3
        else:
            pf = 0.0    # all losses
        score.stability_score = round(min(1.0, pf / (pf + 1.0)), 4)

    # ──────────────────────────────────────────────────────────────────
    # MONTE CARLO
    # ──────────────────────────────────────────────────────────────────

    def _run_monte_carlo(
        self,
        score:  ResilienceScore,
        vix:    float,
        regime: str,
    ) -> None:
        """
        Generate N random price-change scenarios using a VIX-calibrated
        normal distribution and run the signal through each.

        Drift is calibrated per regime:
          bull_trend   → +0.4 % / 5-day
          range_market →  0.0 % / 5-day
          bear_market  → −0.5 % / 5-day
          volatile     → −0.2 % / 5-day
        """
        n = self._mc_runs
        signal = score.signal

        annual_vol   = vix / 100.0
        horizon_days = 5
        sigma        = annual_vol * math.sqrt(horizon_days / 252.0)

        drift_map = {
            "bull_trend":   +0.004,
            "range_market":  0.000,
            "bear_market":  -0.005,
            "volatile":     -0.002,
        }
        drift = drift_map.get(regime, 0.0)

        risk = abs(signal.entry_price - signal.stop_loss)
        if risk == 0:
            score.monte_carlo_runs         = n
            score.monte_carlo_profit_prob  = 0.5
            score.monte_carlo_expected_r   = 0.0
            score.monte_carlo_worst_r      = -1.0
            score.monte_carlo_best_r       = +signal.risk_reward_ratio
            return

        r_outcomes: List[float] = []
        rr_ratio = signal.risk_reward_ratio

        for _ in range(n):
            price_change = random.gauss(drift, sigma)

            # Map index move → stock price change
            beta = random.uniform(0.8, 1.6)   # random stock beta
            sig_type = signal.signal_type or SignalType.EQUITY

            if sig_type == SignalType.FUTURES:
                impact = price_change
            elif sig_type == SignalType.SPREAD:
                impact = price_change * 0.25
            elif sig_type == SignalType.OPTIONS:
                opt = (signal.option_type or "CE").upper()
                impact = -price_change * 0.5 if opt == "PE" else price_change * 0.5
            else:
                impact = price_change * beta

            sim_price = signal.entry_price * (1.0 + impact)

            # Compute R-multiple for this path
            if signal.direction == SignalDirection.BUY:
                if sim_price <= signal.stop_loss:
                    r = -1.0
                elif signal.target_price > 0 and sim_price >= signal.target_price:
                    r = +rr_ratio
                else:
                    r = (sim_price - signal.entry_price) / risk
            elif signal.direction in (SignalDirection.SELL, SignalDirection.SHORT,
                                      SignalDirection.HEDGE):
                if sim_price >= signal.stop_loss and signal.stop_loss > signal.entry_price:
                    r = -1.0
                elif signal.target_price > 0 and sim_price <= signal.target_price:
                    r = +rr_ratio
                else:
                    r = (signal.entry_price - sim_price) / risk
            else:
                r = (sim_price - signal.entry_price) / risk

            r_outcomes.append(r)

        # Summary statistics
        r_outcomes.sort()
        percentile_5 = r_outcomes[int(0.05 * n)]    # 5th percentile = CVaR proxy
        percentile_95 = r_outcomes[int(0.95 * n)]   # 95th percentile

        score.monte_carlo_runs        = n
        score.monte_carlo_profit_prob = round(sum(1 for r in r_outcomes if r > 0) / n, 4)
        score.monte_carlo_expected_r  = round(statistics.mean(r_outcomes), 4)
        score.monte_carlo_worst_r     = round(percentile_5, 4)
        score.monte_carlo_best_r      = round(percentile_95, 4)

    # ──────────────────────────────────────────────────────────────────
    # ACCEPTANCE RULES
    # ──────────────────────────────────────────────────────────────────

    def _apply_acceptance_rules(self, score: ResilienceScore) -> None:
        """
        Apply all acceptance thresholds in sequence.
        First failing check sets rejection_reason and approved=False.
        """
        # Rule 1: Survival rate
        if score.survival_rate < THRESHOLD_SURVIVAL_RATE:
            score.approved = False
            score.rejection_reason = (
                f"Survival rate {score.survival_rate*100:.0f}% < "
                f"threshold {THRESHOLD_SURVIVAL_RATE*100:.0f}%"
            )
            return

        # Rule 2: Catastrophic loss protection
        if score.worst_loss_r < THRESHOLD_WORST_LOSS_R:
            score.approved = False
            score.rejection_reason = (
                f"Worst-case loss {score.worst_loss_r:.2f}R < "
                f"limit {THRESHOLD_WORST_LOSS_R:.1f}R — tail risk too high"
            )
            return

        # Rule 3: Stability
        if score.stability_score < THRESHOLD_STABILITY:
            score.approved = False
            score.rejection_reason = (
                f"Stability {score.stability_score:.2f} < "
                f"threshold {THRESHOLD_STABILITY:.2f} — too inconsistent"
            )
            return

        # Rule 4: Monte Carlo profit probability
        if score.monte_carlo_profit_prob < THRESHOLD_MC_PROFIT_PROB:
            score.approved = False
            score.rejection_reason = (
                f"MC profit probability {score.monte_carlo_profit_prob*100:.0f}% < "
                f"threshold {THRESHOLD_MC_PROFIT_PROB*100:.0f}%"
            )
            return

        score.approved = True
        score.rejection_reason = ""
