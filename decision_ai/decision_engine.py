"""
Decision Engine — Layer 7
============================
Aggregates all debate votes into a final binary decision:
APPROVE → forward to Execution Engine, or REJECT → discard signal.

Algorithm:
  1.  Weight each agent's score by its importance weight
  2.  Apply position modifier as the geometric mean of all modifiers
  3.  If any agent HARD-REJECTS, overall decision = REJECT
  4.  If weighted score ≥ MIN_CONFIDENCE_SCORE, APPROVE

Example output:
  ─────────────────────────────────────────────────
  Agent               Score  Weight  Modifier
  TechnicalAnalystAI  8.0    0.30    100%
  MacroAnalystAI      7.5    0.20    100%
  RiskDebateAI        6.5    0.25     75%
  SentimentAI         7.0    0.15    100%
  RegimeDebateAI      8.0    0.10    100%
  ─────────────────────────────────────────────────
  Weighted Score: 7.45 / 10
  Position Modifier: 75%
  Decision: APPROVED ✅
"""

from __future__ import annotations
from typing import List

from models.market_data      import MarketSnapshot
from models.trade_signal     import TradeSignal
from models.agent_output     import DebateVote, DecisionResult
from models.trade_expectancy import ExpectancyCalculator, FAT_TAIL_THRESHOLD_R
from config import MIN_CONFIDENCE_SCORE
from utils import get_logger

log = get_logger(__name__)

AGENT_WEIGHTS = {
    "TechnicalAnalystAI": 0.30,
    "MacroAnalystAI":     0.20,
    "RiskDebateAI":       0.25,
    "SentimentAI":        0.15,
    "RegimeDebateAI":     0.10,
}


class DecisionEngine:
    """
    Aggregates debate votes into a final trade decision.
    Acts as the Chief Investment Officer — final authority.
    """

    def __init__(self):
        log.info("[DecisionEngine] Initialised. Score threshold=%.1f", MIN_CONFIDENCE_SCORE)

    def decide(self, signal: TradeSignal,
               votes: List[DebateVote],
               snapshot: MarketSnapshot) -> DecisionResult:
        # ── Check for hard rejects ─────────────────────────────────────
        hard_rejects = [v for v in votes if v.vote == "reject"]
        if hard_rejects:
            reasons = "; ".join(v.reasoning for v in hard_rejects)
            return DecisionResult(
                approved=False,
                confidence_score=0.0,
                votes=votes,
                position_size_modifier=0.0,
                reasoning=f"Hard reject(s): {reasons}",
            )

        # ── Weighted confidence score ──────────────────────────────────
        total_weight  = 0.0
        weighted_sum  = 0.0
        modifier_product = 1.0

        for vote in votes:
            w = AGENT_WEIGHTS.get(vote.agent_name, 0.1)
            weighted_sum     += vote.score * w
            total_weight     += w
            modifier_product *= vote.suggested_position_modifier

        confidence = weighted_sum / total_weight if total_weight else 0.0
        modifier   = round(modifier_product ** (1 / len(votes)), 3) if votes else 0.0

        # ── Regime-aware base threshold ────────────────────────────────
        # In volatile markets, good setups score ~6.4–6.6 but still pass all
        # prior layers (risk, simulation, position sizing). Lower the bar
        # slightly so the system maintains participation without increasing risk.
        from models.market_data import RegimeLabel
        regime_value = snapshot.regime if isinstance(snapshot.regime, str) else snapshot.regime.value
        if regime_value == RegimeLabel.VOLATILE.value:
            effective_threshold = MIN_CONFIDENCE_SCORE - 0.3   # 6.8 → 6.5
            log.info("[DecisionEngine] Dynamic Threshold Applied: regime=volatile, threshold=%.1f",
                     effective_threshold)
        else:
            effective_threshold = MIN_CONFIDENCE_SCORE

        # ── Asymmetry Bonus: high R:R lowers effective confidence threshold ──
        # A trade with RR≥3 needs far fewer wins to be profitable.
        # RR=3 → breakeven at only 25% WR; we reward this structurally.
        rr = signal.risk_reward_ratio
        asymmetry_note = ""
        if rr >= 4.0:
            effective_threshold -= 1.0   # −1.0 pt threshold reduction for fat-tail setups
            modifier = min(modifier * 1.1, 1.0)   # 10% size boost — let winners run
            bkv = ExpectancyCalculator.breakeven_win_rate(rr)
            asymmetry_note = (f" | 🎯 Fat-tail RR={rr:.1f}: breakeven≥{bkv:.0%} "
                              f"(size+10%, threshold-1pt)")
        elif rr >= 3.0:
            effective_threshold -= 0.5   # −0.5 pt reduction for strong asymmetry
            bkv = ExpectancyCalculator.breakeven_win_rate(rr)
            asymmetry_note = (f" | ⚡ Asymmetric RR={rr:.1f}: breakeven≥{bkv:.0%} "
                              f"(threshold-0.5pt)")

        # ── Tiered execution decision ──────────────────────────────────
        # FULL    : score >= effective_threshold           → 100% size
        # PARTIAL : effective_threshold - 0.2 <= score <  effective_threshold → 50% size
        # REJECT  : score < effective_threshold - 0.2
        PARTIAL_LOWER = effective_threshold - 0.2

        if confidence >= effective_threshold and modifier > 0.0:
            trade_type = "FULL"
            approved   = True
            final_modifier = modifier
        elif confidence >= PARTIAL_LOWER and modifier > 0.0:
            trade_type = "PARTIAL"
            approved   = True
            final_modifier = modifier * 0.5   # Cap at 50% for partial trades
        else:
            trade_type = "REJECT"
            approved   = False
            final_modifier = 0.0

        result = DecisionResult(
            approved=approved,
            confidence_score=round(confidence, 2),
            votes=votes,
            position_size_modifier=round(final_modifier, 3),
            trade_type=trade_type,
            reasoning=(
                f"Weighted score {confidence:.2f} | Threshold {effective_threshold:.1f} "
                f"(partial≥{PARTIAL_LOWER:.1f}) | Trade type: {trade_type} | "
                f"Size modifier: {final_modifier:.0%}"
                + asymmetry_note
            ),
        )

        self._log_scorecard(signal, votes, result)
        return result

    # ─────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────

    def _log_scorecard(self, sig: TradeSignal,
                       votes: List[DebateVote],
                       result: DecisionResult):
        log.info("[DecisionEngine] ── Scorecard: %s ──", sig.symbol)
        log.info("  %-25s  %s  %s", "Agent", "Score", "Weight")
        log.info("  " + "─" * 45)
        for vote in votes:
            w = AGENT_WEIGHTS.get(vote.agent_name, 0.1)
            log.info("  %-25s  %.1f   %.2f", vote.agent_name, vote.score, w)
        log.info("  " + "─" * 45)
        log.info("  Weighted Score: %.2f / 10", result.confidence_score)
        log.info("  Position Modifier: %.0f%%", result.position_size_modifier * 100)
        _type_labels = {
            "FULL":    "✅ FULL TRADE    | Position Size: 100%",
            "PARTIAL": "⚡ PARTIAL TRADE | Position Size:  50%",
            "REJECT":  "❌ REJECTED      | Position Size:   0%",
        }
        log.info("  Symbol   : %s", sig.symbol)
        log.info("  Score    : %.2f", result.confidence_score)
        log.info("  Decision : %s", _type_labels.get(result.trade_type, result.trade_type))
        log.info("  Reason   : %s", result.reasoning)
