"""
Strategy Generator AI — Layer 4 Agent 1
=========================================
Assigns the optimal trading strategy to each signal based on the current
market regime, volatility environment, and signal characteristics.

Strategy catalogue:
  1. Breakout Strategy        — BULL_TREND + volume breakout
  2. Momentum Strategy        — BULL_TREND + RSI continuation
  3. Mean Reversion           — RANGE_MARKET + RSI extremes
  4. Options Spread (Bull CS) — BULL_TREND + options signal
  5. Iron Condor              — RANGE_MARKET + low IV
  6. Hedging Model            — BEAR_MARKET / VOLATILE
"""

from __future__ import annotations
import json
import os
from typing import List, Optional, Set

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

EVOLVED_STRATEGIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "evolved_strategies.json"
)

# ── Strategy parameter library (tuned by StrategyEvolutionAI) ──────────────
# Asymmetric payoff philosophy: every strategy targets at least 2:1 R:R.
# At 2:1, only 33% win rate is needed to break even.
# Strategies below 2.0 must rely on high frequency or premium capture.
STRATEGY_PARAMS = {
    "Breakout_Volume":        {"min_rr": 2.5, "max_loss_pct": 0.02},   # trend explosions → aim for fat tail
    "Momentum_Retest":        {"min_rr": 2.0, "max_loss_pct": 0.025},  # was 1.8
    "Trend_Pullback":         {"min_rr": 2.5, "max_loss_pct": 0.02},   # ATR-based pullback inside trend
    "Mean_Reversion":         {"min_rr": 2.0, "max_loss_pct": 0.015},  # was 1.5
    "Bull_Call_Spread":       {"min_rr": 2.0, "max_loss_pct": 0.01},   # was 1.5
    "Iron_Condor_Range":      {"min_rr": 1.5, "max_loss_pct": 0.01},   # premium income — needs consistency
    "Hedging_Model":          {"min_rr": 1.5, "max_loss_pct": 0.02},   # was 1.0 — hedges must still pay
    "Short_Straddle_IV_Spike":{"min_rr": 1.5, "max_loss_pct": 0.015},
    "Long_Straddle_Pre_Event":{"min_rr": 2.5, "max_loss_pct": 0.02},   # event plays → fat tail
    "Futures_Basis_Arb":      {"min_rr": 1.2, "max_loss_pct": 0.005},  # arb — tight spreads
    "ETF_NAV_Arb":            {"min_rr": 1.2, "max_loss_pct": 0.003},  # arb — tight spreads
}


class StrategyGeneratorAI:
    """
    Maps each TradeSignal to the most appropriate strategy,
    guided by the current market regime.

    On startup, loads any approved evolved variants from
    data/evolved_strategies.json and registers them so that
    signals can be assigned to them instead of the base strategy.

    When a MetaStrategyController is provided, only strategies
    that are both regime-appropriate AND pass quality gates are
    eligible for assignment.
    """

    def __init__(self, meta_controller=None):
        self._meta = meta_controller   # MetaStrategyController | None
        self._load_evolved_strategies()
        log.info("[StrategyGeneratorAI] Initialised with %d strategies.",
                 len(STRATEGY_PARAMS))

    def _load_evolved_strategies(self):
        """Load approved evolved variants and add to STRATEGY_PARAMS."""
        if not os.path.exists(EVOLVED_STRATEGIES_PATH):
            return
        try:
            with open(EVOLVED_STRATEGIES_PATH, "r", encoding="utf-8") as f:
                evolved = json.load(f)
            added = 0
            for name, params in evolved.items():
                if params.get("approved") and name not in STRATEGY_PARAMS:
                    # Inherit min_rr and max_loss_pct from the base strategy,
                    # but honour any explicit values stored in the JSON first.
                    base = params.get("base_strategy", "Breakout_Volume")
                    base_params = STRATEGY_PARAMS.get(base, {"min_rr": 2.0, "max_loss_pct": 0.02})
                    STRATEGY_PARAMS[name] = {
                        "min_rr":         params.get("min_rr") or base_params["min_rr"],
                        "max_loss_pct":   params.get("max_loss_pct") or base_params["max_loss_pct"],
                        "base_strategy":  base,
                        "use_rsi_filter": params.get("use_rsi_filter", False),
                        "volume_ratio":   params.get("volume_ratio", 1.5),
                    }
                    added += 1
            if added:
                log.info("[StrategyGeneratorAI] Loaded %d evolved variants from disk.", added)
        except Exception as exc:
            log.warning("[StrategyGeneratorAI] Could not load evolved strategies: %s", exc)

    def assign_strategy(self, signals: List[TradeSignal],
                        snapshot: MarketSnapshot) -> List[TradeSignal]:
        """
        Validates and/or overrides each signal's strategy_name based on regime.
        Re-calculates minimum required confidence.
        """
        # Ask MetaStrategyController which strategies are live this cycle
        passing = set(STRATEGY_PARAMS.keys())   # default: all
        active: Set[str] | None = None
        if self._meta is not None:
            # passing = all known strategy names (gate filtering happens in BacktestingAI)
            active = self._meta.get_active_strategies(snapshot, passing)
            log.info("[StrategyGeneratorAI] MetaController active set (%d): %s",
                     len(active), ", ".join(sorted(active)))

        enriched: List[TradeSignal] = []
        for signal in signals:
            assigned = self._assign(signal, snapshot, active)
            if assigned:
                enriched.append(assigned)

        log.info("[StrategyGeneratorAI] %d/%d signals assigned strategies.",
                 len(enriched), len(signals))
        return enriched

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _assign(self, signal: TradeSignal,
                snapshot: MarketSnapshot,
                active: Optional[Set[str]] = None) -> TradeSignal | None:
        regime    = snapshot.regime
        vol_level = snapshot.volatility

        # ── Reject equity longs in bear market ───────────────────────
        if (regime == RegimeLabel.BEAR_MARKET
                and signal.signal_type == SignalType.EQUITY
                and signal.direction == SignalDirection.BUY):
            log.debug("[StrategyGeneratorAI] Rejected %s — bear market.", signal.symbol)
            return None

        # ── Override strategy if already correctly named ──────────────
        if signal.strategy_name in STRATEGY_PARAMS:
            rr = signal.risk_reward_ratio
            # Upgrade to the best evolved variant the signal's R:R can actually satisfy.
            # IMPORTANT: pass rr so we never upgrade to a variant with min_rr > signal.rr.
            evolved = self._best_evolved_variant(signal.strategy_name, active,
                                                  min_signal_rr=rr)
            if evolved:
                signal.strategy_name = evolved
            # If MetaController says this strategy is inactive, skip it
            if active is not None and signal.strategy_name not in active:
                log.debug("[StrategyGeneratorAI] %s strategy %s not in active set — skipped.",
                          signal.symbol, signal.strategy_name)
                return None
            # Validate R:R against whichever strategy (evolved or original) is selected
            params = STRATEGY_PARAMS[signal.strategy_name]
            if rr < params["min_rr"]:
                log.debug("[StrategyGeneratorAI] %s RR %.1f < min %.1f — skipped.",
                          signal.symbol, rr, params["min_rr"])
                return None
            return signal

        # ── Auto-assign based on regime + signal type ─────────────────
        strategy = self._pick_strategy(signal, regime, vol_level, active)
        if strategy:
            signal.strategy_name = strategy
        return signal

    def _pick_strategy(self, signal: TradeSignal,
                       regime: RegimeLabel,
                       vol: VolatilityLevel,
                       active: Optional[Set[str]] = None) -> str:
        """Pick best regime-appropriate strategy that is also in the active set."""

        rr = signal.risk_reward_ratio

        def _choose(candidates: List[str]) -> str:
            """Return first candidate that is in the active set, or first if no filter."""
            for c in candidates:
                if active is None or c in active:
                    return c
            return ""

        # Prefer approved evolved variants over base strategies
        if regime in (RegimeLabel.BULL_TREND,):
            if signal.signal_type == SignalType.EQUITY:
                evolved = self._best_evolved_variant("Breakout_Volume", active,
                                                      min_signal_rr=rr)
                return evolved or _choose(["Breakout_Volume"])
            elif signal.signal_type in (SignalType.OPTIONS, SignalType.SPREAD):
                return _choose(["Bull_Call_Spread"])

        elif regime == RegimeLabel.RANGE_MARKET:
            if signal.signal_type == SignalType.EQUITY:
                evolved = self._best_evolved_variant("Mean_Reversion", active,
                                                      min_signal_rr=rr)
                return evolved or _choose(["Mean_Reversion"])
            elif signal.signal_type in (SignalType.OPTIONS, SignalType.SPREAD):
                return _choose(["Iron_Condor_Range"])
            elif signal.signal_type == SignalType.FUTURES:
                return _choose(["Futures_Basis_Arb"])
            elif signal.signal_type == SignalType.ETF:
                return _choose(["ETF_NAV_Arb"])

        elif regime in (RegimeLabel.BEAR_MARKET, RegimeLabel.VOLATILE):
            return _choose(["Hedging_Model"])

        return _choose(["Breakout_Volume"])   # default fallback

    def _best_evolved_variant(self, base_strategy: str,
                              active: Optional[Set[str]] = None,
                              min_signal_rr: float = 0.0) -> str:
        """
        Return the name of the best evolved variant for a base strategy
        that is also in the active set (if provided) AND whose min_rr the
        signal can actually satisfy (min_rr <= min_signal_rr).

        Among qualifying variants, picks the one with the highest min_rr
        (i.e. the highest-quality bar the signal can still clear).
        Returns empty string if none qualify.
        """
        candidates = [
            (name, params) for name, params in STRATEGY_PARAMS.items()
            if params.get("base_strategy") == base_strategy
            and (active is None or name in active)
            and (min_signal_rr == 0.0 or params["min_rr"] <= min_signal_rr)
        ]
        if candidates:
            return max(candidates, key=lambda x: x[1]["min_rr"])[0]
        return ""
