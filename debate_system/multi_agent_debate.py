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

# ── TechnicalAnalyst structural-validator governance constants (DTA-DEBATE-AUTHORITY-002C) ──
# Deliberately wide sanity envelope — NOT an empirically optimized trading
# parameter. Catches gross stop-distance errors relative to the stock's own
# ATR; expresses no opinion on ideal stop placement. Revisit only after Debate
# telemetry repair produces enough real outcome evidence to calibrate empirically.
TA_ATR_RATIO_MIN = 0.5
TA_ATR_RATIO_MAX = 4.0


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
        """
        Technical Analyst validates STRUCTURAL COHERENCE of the proposed trade —
        it is not a second conviction/intelligence score (DTA-DEBATE-AUTHORITY-002C).
        Checks: (1) directional geometry — stop/target on the correct side of
        entry, (2) ATR-vs-stop-distance sanity when ATR is available, (3)
        KDA_EMPIRICAL vs ATR_FALLBACK provenance as a secondary, non-invalidating
        indicator. Contains zero references to confidence, kda_conviction (for
        scoring), the assigned label field, upstream approval labels, or
        scanner_score.
        """
        entry, stop, target = sig.entry_price, sig.stop_loss, sig.target_price

        # 1) Directional geometry — malformed/inverted trades are structurally invalid
        if sig.direction == SignalDirection.BUY:
            geometry_valid = stop < entry < target
        elif sig.direction in (SignalDirection.SELL, SignalDirection.SHORT):
            geometry_valid = target < entry < stop
        else:
            geometry_valid = True   # HEDGE/EXIT — directional geometry not applicable

        if not geometry_valid:
            return DebateVote(
                agent_name="TechnicalAnalystAI",
                vote="reject", score=3.0,
                reasoning=(f"Structurally invalid geometry: entry={entry:.2f} "
                           f"stop={stop:.2f} target={target:.2f} dir={sig.direction.value}"),
                suggested_position_modifier=0.0,
            )

        # 2) ATR-vs-stop-distance sanity — only judged when ATR is available;
        # missing ATR is neutral, never a penalty.
        weak_reasons = []
        atr = getattr(sig, "atr", 0.0) or 0.0
        if atr > 0:
            atr_ratio = abs(entry - stop) / atr
            if atr_ratio < TA_ATR_RATIO_MIN or atr_ratio > TA_ATR_RATIO_MAX:
                weak_reasons.append(
                    f"ATR ratio {atr_ratio:.2f}x outside sane "
                    f"[{TA_ATR_RATIO_MIN}-{TA_ATR_RATIO_MAX}]x envelope"
                )

        # 3) Provenance — secondary indicator only, never invalidates by itself
        if getattr(sig, "target_source", None) == "ATR_FALLBACK" or \
           getattr(sig, "stop_source", None) == "ATR_FALLBACK":
            weak_reasons.append("target/stop derived from ATR_FALLBACK, not KDA_EMPIRICAL")

        # KDA conviction is context for the reasoning trail only — never scored.
        _kda_conv = getattr(sig, "kda_conviction", None)
        kda_note  = f" | KDA context: kda_conviction={_kda_conv:.1f} (not used for scoring)" \
                    if _kda_conv is not None else ""

        if weak_reasons:
            return DebateVote(
                agent_name="TechnicalAnalystAI",
                vote="reduce_size", score=5.0,
                reasoning="Structurally weak: " + "; ".join(weak_reasons) + kda_note,
                suggested_position_modifier=0.7,
            )

        return DebateVote(
            agent_name="TechnicalAnalystAI",
            vote="approve", score=8.0,
            reasoning=f"Structurally sound. R:R={sig.risk_reward_ratio:.1f}" + kda_note,
            suggested_position_modifier=1.0,
        )

    def _macro_vote(self, sig: TradeSignal,
                    snapshot: MarketSnapshot) -> DebateVote:
        """Macro Analyst checks global market conditions + global sentiment."""
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

        # Use global_sentiment_score (−1 → +1) to calibrate macro score (5–9).
        # A positive global bias (US/Asia green) adds conviction; negative subtracts.
        gs = getattr(snapshot, "global_sentiment_score", 0.0)  # −1 → +1
        base_score = 7.0 + gs * 2.0   # gs=+1 → 9.0, gs=0 → 7.0, gs=-1 → 5.0
        base_score = round(max(5.0, min(9.0, base_score)), 2)
        size_mod   = 1.0 if gs >= -0.3 else 0.75
        sentiment_label = "positive" if gs > 0.1 else ("negative" if gs < -0.1 else "neutral")
        return DebateVote(
            agent_name="MacroAnalystAI",
            vote="approve",
            score=base_score,
            reasoning=f"Macro {sentiment_label} (gs={gs:+.2f}) → score={base_score}",
            suggested_position_modifier=size_mod,
        )

    def _risk_vote(self, sig: TradeSignal,
                   snapshot: MarketSnapshot) -> DebateVote:
        """Risk agent adjusts size based on VIX, volatility, and signal R:R."""
        vix        = snapshot.vix
        rr         = sig.risk_reward_ratio
        size_mod   = 1.0
        vote_label = "approve"
        reasoning  = f"Risk acceptable. VIX={vix:.1f} R:R={rr:.1f}"

        # VIX component: 7.0 base, penalise for elevated volatility
        if vix >= 22:
            vix_score = 4.5
            size_mod  = 0.5
            vote_label = "reduce_size"
        elif vix >= 18:
            vix_score = 6.0
            size_mod  = 0.75
            vote_label = "reduce_size"
        else:
            vix_score = 7.0

        # R:R component: reward asymmetric setups
        if rr >= 4.0:
            rr_bonus = 1.5
        elif rr >= 3.0:
            rr_bonus = 1.0
        elif rr >= 2.0:
            rr_bonus = 0.5
        elif rr < 1.5:
            rr_bonus = -1.5
            size_mod = min(size_mod, 0.5)
            vote_label = "reduce_size"
        else:
            rr_bonus = 0.0

        score = round(min(9.5, max(3.0, vix_score + rr_bonus)), 2)
        reasoning = f"VIX={vix:.1f} R:R={rr:.1f} → score={score}"

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

        # DTA-DEBATE-AUTHORITY-003: canonical KDA-authoritative population,
        # identical to CapitalRiskEngine/RiskManagerAI/PortfolioAllocationAI —
        # not a label proxy. Covers KDA-only signals AND StrategyLab+KDA
        # ("BOTH") signals that retain their original scanner label.
        _kda_authoritative = (
            getattr(sig, "kda_decision", None) in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL")
            and getattr(sig, "authorization_source", None) in ("KDA", "BOTH")
            and getattr(sig, "kda_evidence_state", None) in ("VALIDATED", "DECISION_ELIGIBLE")
        )

        # KDA-authoritative signals have already passed regime-aware evidence
        # evaluation: HBE queries include regime as a parameter, so the KDA
        # decision implicitly encodes regime compatibility. Applying the
        # strategy matrix here would double-count regime analysis using the
        # wrong proxy (label instead of evidence quality).
        if _kda_authoritative:
            ev_state = getattr(sig, "kda_evidence_state", "") or ""
            return DebateVote(
                agent_name="RegimeDebateAI", vote="approve", score=8.0,
                reasoning=f"KDA authority ({ev_state}) — regime verified by HBE evidence",
                suggested_position_modifier=1.0,
            )

        # Confirm strategy is appropriate for regime
        regime_strategy_matrix = {
            RegimeLabel.BULL_TREND:   ["Breakout_Volume", "Momentum_Retest",
                                       "Bull_Call_Spread"],
            RegimeLabel.RANGE_MARKET: ["Mean_Reversion", "Iron_Condor_Range", "Momentum_Retest"],
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
