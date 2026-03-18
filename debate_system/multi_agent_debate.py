"""
Multi-Agent Debate System — Layer 6
=======================================
The most powerful layer in the system. Each specialist AI agent
independently evaluates the trade proposal and casts a vote with
reasoning. The aggregate of these votes determines whether the
Decision AI approves or rejects the trade.

Debate agents:
  ┌─────────────────────────────────────────────────────┐
  │  TechnicalAnalystAI  — chart patterns & indicators  │
  │  MacroAnalystAI      — global macro context         │
  │  RiskDebateAI        — position risk assessment     │
  │  SentimentAI         — news & options sentiment     │
  │  RegimeDebateAI      — market regime compatibility  │
  └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations
from typing import List

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal, SignalDirection
from models.agent_output import DebateVote
from utils import get_logger

log = get_logger(__name__)

# ── Debate agent weights ──────────────────────────────────────────────────────
AGENT_WEIGHTS = {
    "TechnicalAnalystAI": 0.30,
    "MacroAnalystAI":     0.20,
    "RiskDebateAI":       0.25,
    "SentimentAI":        0.15,
    "RegimeDebateAI":     0.10,
}


class MultiAgentDebate:
    """
    Runs each specialist AI and collects their vote on the proposed signal.
    Returns the full list of votes for the DecisionEngine.
    """

    def __init__(self):
        log.info("[MultiAgentDebate] Initialised with %d debaters.", len(AGENT_WEIGHTS))

    def run(self, signal: TradeSignal,
            snapshot: MarketSnapshot) -> List[DebateVote]:
        votes: List[DebateVote] = []

        votes.append(self._technical_vote(signal, snapshot))
        votes.append(self._macro_vote(signal, snapshot))
        votes.append(self._risk_vote(signal, snapshot))
        votes.append(self._sentiment_vote(signal, snapshot))
        votes.append(self._regime_vote(signal, snapshot))

        self._log_debate(signal, votes)
        return votes

    # ─────────────────────────────────────────────────────────────────
    # INDIVIDUAL DEBATER AGENTS
    # ─────────────────────────────────────────────────────────────────

    def _technical_vote(self, sig: TradeSignal,
                        snapshot: MarketSnapshot) -> DebateVote:
        """Technical Analyst evaluates chart structure and momentum."""
        score      = sig.confidence * 0.9
        rr         = sig.risk_reward_ratio
        vote_label = "approve"
        reasoning  = f"Entry valid, R:R={rr:.1f}"
        size_mod   = 1.0

        if rr < 1.5:
            vote_label = "reduce_size"
            score      = max(score * 0.7, 3.0)
            reasoning  = f"R:R={rr:.1f} below ideal — halve size"
            size_mod   = 0.5
        elif rr >= 3.0:
            score = min(score * 1.1, 9.5)
            reasoning = f"Excellent R:R={rr:.1f}"

        return DebateVote(
            agent_name="TechnicalAnalystAI",
            vote=vote_label, score=round(score, 2),
            reasoning=reasoning,
            suggested_position_modifier=size_mod,
        )

    def _macro_vote(self, sig: TradeSignal,
                    snapshot: MarketSnapshot) -> DebateVote:
        """Macro Analyst checks global market conditions."""
        if snapshot.events_today:
            return DebateVote(
                agent_name="MacroAnalystAI",
                vote="hedge",
                score=5.0,
                reasoning=f"Event risk: {snapshot.events_today[0]} — prefer hedge",
                suggested_position_modifier=0.6,
            )

        if snapshot.regime == RegimeLabel.BEAR_MARKET:
            return DebateVote(
                agent_name="MacroAnalystAI",
                vote="reject",
                score=3.0,
                reasoning="Global macro weak — bear market, avoid longs",
                suggested_position_modifier=0.0,
            )

        return DebateVote(
            agent_name="MacroAnalystAI",
            vote="approve",
            score=7.5,
            reasoning="Macro environment supportive",
            suggested_position_modifier=1.0,
        )

    def _risk_vote(self, sig: TradeSignal,
                   snapshot: MarketSnapshot) -> DebateVote:
        """Risk agent adjusts size based on VIX and volatility."""
        vix        = snapshot.vix
        size_mod   = 1.0
        vote_label = "approve"
        score      = 7.0
        reasoning  = f"Risk acceptable. VIX={vix:.1f}"

        if vix >= 22:
            size_mod   = 0.5
            vote_label = "reduce_size"
            score      = 5.5
            reasoning  = f"High VIX={vix:.1f} — halve position size"
        elif vix >= 18:
            size_mod   = 0.75
            vote_label = "reduce_size"
            score      = 6.5
            reasoning  = f"Elevated VIX={vix:.1f} — reduce to 75%"

        return DebateVote(
            agent_name="RiskDebateAI",
            vote=vote_label, score=score,
            reasoning=reasoning,
            suggested_position_modifier=size_mod,
        )

    def _sentiment_vote(self, sig: TradeSignal,
                        snapshot: MarketSnapshot) -> DebateVote:
        """Sentiment AI uses PCR and breadth as proxy for crowd sentiment."""
        pcr     = snapshot.pcr
        breadth = snapshot.market_breadth
        is_long = sig.direction == SignalDirection.BUY

        if is_long:
            if pcr > 1.2:       # High put buying = fear = contrarian buy signal
                return DebateVote(
                    agent_name="SentimentAI", vote="approve", score=7.0,
                    reasoning=f"PCR={pcr:.2f} elevated — contrarian bullish",
                    suggested_position_modifier=1.0,
                )
            elif breadth < 0.35:  # Very weak breadth = risk off
                return DebateVote(
                    agent_name="SentimentAI", vote="reduce_size", score=5.5,
                    reasoning=f"Breadth={breadth:.0%} weak — reduce size",
                    suggested_position_modifier=0.6,
                )
        return DebateVote(
            agent_name="SentimentAI", vote="approve", score=7.0,
            reasoning=f"Sentiment neutral. PCR={pcr:.2f} Breadth={breadth:.0%}",
            suggested_position_modifier=1.0,
        )

    def _regime_vote(self, sig: TradeSignal,
                     snapshot: MarketSnapshot) -> DebateVote:
        """Regime AI checks strategy–regime compatibility."""
        regime = snapshot.regime.value
        strat  = sig.strategy_name

        # Confirm strategy is appropriate for regime
        regime_strategy_matrix = {
            RegimeLabel.BULL_TREND:   ["Breakout_Volume", "Momentum_Retest",
                                       "Bull_Call_Spread"],
            RegimeLabel.RANGE_MARKET: ["Mean_Reversion", "Iron_Condor_Range"],
            RegimeLabel.BEAR_MARKET:  ["Hedging_Model", "Short_Straddle_IV_Spike"],
            RegimeLabel.VOLATILE:     ["Hedging_Model", "Iron_Condor_Range"],
        }

        allowed = regime_strategy_matrix.get(snapshot.regime, [])
        if strat in allowed:
            return DebateVote(
                agent_name="RegimeDebateAI", vote="approve", score=8.0,
                reasoning=f"'{strat}' is correct for {regime} regime",
                suggested_position_modifier=1.0,
            )
        else:
            return DebateVote(
                agent_name="RegimeDebateAI", vote="reduce_size", score=5.0,
                reasoning=f"'{strat}' sub-optimal for {regime} regime",
                suggested_position_modifier=0.7,
            )

    # ─────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────

    def _log_debate(self, sig: TradeSignal, votes: List[DebateVote]):
        log.info("[Debate] ── %s %s ──", sig.symbol, sig.direction.value)
        for v in votes:
            flag = "✅" if v.vote == "approve" else ("⚠" if "reduce" in v.vote else "❌")
            log.info("  %s %-22s  score=%.1f  modifier=%.0f%%  %s",
                     flag, v.agent_name, v.score,
                     v.suggested_position_modifier * 100, v.reasoning)
