"""
Market Simulation Engine — Simulation Report
=============================================
Formats and logs the full simulation output for each trade signal.

Output layers:
  1. Per-signal header (symbol, strategy, entry/SL/target/RR)
  2. Scenario results table (one row per scenario)
  3. Resilience metrics block (survival %, MC results, stability)
  4. Accept / Reject verdict

At cycle end a compact summary table is logged showing all signals
and their simulation verdict at a glance.
"""

from __future__ import annotations
from typing import List

from utils import get_logger
from .stress_test_engine import ScenarioTestResult, TradeOutcome
from .strategy_resilience_ai import ResilienceScore

log = get_logger(__name__)

# Column widths
_W_SCENARIO  = 22
_W_OUTCOME   = 14
_W_PRICE     = 11
_W_IMPACT    = 10
_W_R         = 8


class SimulationReporter:
    """
    Produces log output for simulation results.

    Usage
    -----
    reporter = SimulationReporter()
    reporter.print_signal_report(score)          # per-signal detail
    reporter.print_cycle_summary(scores)         # end-of-cycle table
    """

    # ──────────────────────────────────────────────────────────────────
    # PER-SIGNAL DETAIL REPORT
    # ──────────────────────────────────────────────────────────────────

    def print_signal_report(self, score: ResilienceScore) -> None:
        """Log the full simulation report for one trade signal."""
        sig = score.signal
        sep  = "═" * 76
        thin = "─" * 76

        log.info(sep)
        log.info(
            "  MARKET SIMULATION  |  %s  |  %s  |  Entry: %.2f  SL: %.2f  Target: %.2f",
            sig.symbol,
            sig.strategy_name,
            sig.entry_price,
            sig.stop_loss,
            sig.target_price,
        )
        log.info(
            "  Direction: %-6s  |  R:R ratio: %.2f  |  Confidence: %.1f/10",
            sig.direction.value,
            sig.risk_reward_ratio,
            sig.confidence,
        )
        log.info(thin)

        # ── Scenario results table header ──────────────────────────────
        log.info(
            "  %-*s  %-*s  %-*s  %-*s  %s",
            _W_SCENARIO, "Scenario",
            _W_OUTCOME,  "Outcome",
            _W_PRICE,    "Sim Price",
            _W_IMPACT,   "Δ%",
            "R",
        )
        log.info("  %s", "─" * 72)

        # ── Scenario rows ──────────────────────────────────────────────
        for r in score.scenario_results:
            log.info(
                "  %-*s  %-*s  %-*s  %-*s  %s",
                _W_SCENARIO, r.scenario.label,
                _W_OUTCOME,  r.short_label(),
                _W_PRICE,    f"₹{r.simulated_price:,.2f}",
                _W_IMPACT,   f"{r.price_impact_pct:+.2f}%",
                f"{r.r_multiple:+.2f}R",
            )

        log.info("  %s", "─" * 72)

        # ── Deterministic metrics block ────────────────────────────────
        survival_bar = self._bar(score.survival_rate, width=20)
        stability_bar = self._bar(score.stability_score, width=20)
        log.info(
            "  Survival Rate    : %s  %d/%d scenarios survived  (%.0f%%)",
            survival_bar,
            int(score.survival_rate * len(score.scenario_results)),
            len(score.scenario_results),
            score.survival_rate * 100,
        )
        log.info(
            "  Stability Score  : %s  %.2f / 1.00",
            stability_bar,
            score.stability_score,
        )
        log.info(
            "  Expected R       : %+.2fR   |   Worst: %+.2fR   |   Best: %+.2fR",
            score.expected_r,
            score.worst_loss_r,
            score.best_gain_r,
        )

        # ── Monte Carlo block ──────────────────────────────────────────
        mc_bar = self._bar(score.monte_carlo_profit_prob, width=20)
        log.info(thin)
        log.info(
            "  Monte Carlo (%d runs):",
            score.monte_carlo_runs,
        )
        log.info(
            "    Profit Probability : %s  %.0f%%",
            mc_bar,
            score.monte_carlo_profit_prob * 100,
        )
        log.info(
            "    Expected Return    : %+.2fR",
            score.monte_carlo_expected_r,
        )
        log.info(
            "    Worst Case (5%%ile): %+.2fR   |   Best Case (95%%ile): %+.2fR",
            score.monte_carlo_worst_r,
            score.monte_carlo_best_r,
        )

        # ── Verdict ────────────────────────────────────────────────────
        log.info("  %s", "─" * 72)
        if score.approved:
            log.info(
                "  ✅ SIMULATION APPROVED  |  Resilience Score: %.1f/10",
                score.overall_score(),
            )
        else:
            log.info(
                "  ❌ SIMULATION REJECTED  |  Reason: %s",
                score.rejection_reason,
            )
        log.info(sep)

    # ──────────────────────────────────────────────────────────────────
    # CYCLE SUMMARY TABLE
    # ──────────────────────────────────────────────────────────────────

    def print_cycle_summary(self, scores: List[ResilienceScore]) -> None:
        """
        Print a compact table summarising all signals' simulation results
        at the end of the simulation step.
        """
        if not scores:
            return

        sep  = "═" * 88
        thin = "─" * 88
        log.info(sep)
        log.info("  MARKET SIMULATION ENGINE — CYCLE SUMMARY  |  %d signal(s) evaluated",
                 len(scores))
        log.info(thin)
        log.info(
            "  %-12s  %-28s  %-8s  %-8s  %-8s  %-6s  %s",
            "Symbol", "Strategy",
            "Surviv%", "Stab", "MC Prob%",
            "Score", "Verdict",
        )
        log.info("  %s", "─" * 84)

        approved = 0
        for s in scores:
            verdict = "✅ PASS" if s.approved else "❌ FAIL"
            if s.approved:
                approved += 1
            log.info(
                "  %-12s  %-28s  %-8s  %-8s  %-8s  %-6s  %s",
                s.signal.symbol,
                s.signal.strategy_name,
                f"{s.survival_rate*100:.0f}%",
                f"{s.stability_score:.2f}",
                f"{s.monte_carlo_profit_prob*100:.0f}%",
                f"{s.overall_score():.1f}",
                verdict,
            )

        log.info("  %s", "─" * 84)
        log.info(
            "  %d/%d signals passed simulation  |  %d rejected",
            approved, len(scores), len(scores) - approved,
        )
        log.info(sep)

    # ──────────────────────────────────────────────────────────────────
    # HELPER
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _bar(value: float, width: int = 20) -> str:
        """Draw a simple ASCII progress bar for a 0-1 value."""
        filled = int(round(value * width))
        return "[" + "█" * filled + "░" * (width - filled) + "]"
