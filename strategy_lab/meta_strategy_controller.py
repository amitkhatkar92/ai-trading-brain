"""
Meta-Strategy Controller — Layer 4 Agent 0
============================================
Decides WHICH strategies are active for the current trading cycle
based on three inputs:

  1. Market Regime    — bull / range / bear / volatile
  2. Volatility Level — low / medium / high
  3. Backtest Quality — only strategies that pass quality gates are eligible

Regime → Strategy Mapping
──────────────────────────
  BULL_TREND    → Breakout_Volume, Momentum_Retest, Bull_Call_Spread,
                  Long_Straddle_Pre_Event
  RANGE_MARKET  → Mean_Reversion, Iron_Condor_Range, Futures_Basis_Arb,
                  ETF_NAV_Arb
  BEAR_MARKET   → Hedging_Model, Iron_Condor_Range, Futures_Basis_Arb
  VOLATILE      → Hedging_Model, Short_Straddle_IV_Spike,
                  Long_Straddle_Pre_Event

If an evolved variant exists for an active base strategy it is
automatically included alongside the base strategy.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Set

from models.market_data  import MarketSnapshot, RegimeLabel, VolatilityLevel
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

EVOLVED_STRATEGIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "evolved_strategies.json"
)

# ── Master regime → candidate strategy mapping ────────────────────────────────
_REGIME_MAP: Dict[str, List[str]] = {
    RegimeLabel.BULL_TREND.value: [
        "Breakout_Volume",
        "Momentum_Retest",
        "Trend_Pullback",         # ATR-based pullback — primary bull-market setup
        "Bull_Call_Spread",
        "Long_Straddle_Pre_Event",
    ],
    RegimeLabel.RANGE_MARKET.value: [
        # Primary range strategies
        "Mean_Reversion",
        "Iron_Condor_Range",
        "Futures_Basis_Arb",
        "ETF_NAV_Arb",
        # Secondary: trend-following setups work at range boundaries
        "Breakout_Volume",
        "Momentum_Retest",
        "Trend_Pullback",         # upper/lower range retests behave like trend pullbacks
    ],
    RegimeLabel.BEAR_MARKET.value: [
        "Hedging_Model",
        "Iron_Condor_Range",
        "Futures_Basis_Arb",
    ],
    RegimeLabel.VOLATILE.value: [
        "Hedging_Model",
        "Short_Straddle_IV_Spike",
        "Long_Straddle_Pre_Event",
    ],
}

# Extra high-volatility overlay (added on top of regime set when vol is HIGH)
_HIGH_VOL_EXTRAS: List[str] = ["Short_Straddle_IV_Spike", "Hedging_Model"]

# Also allow Short_Straddle in RANGE_MARKET when IV is elevated
# (selling premium in flat markets is institutionally standard)
_RANGE_VOL_EXTRAS: List[str] = ["Short_Straddle_IV_Spike"]


class MetaStrategyController:
    """
    Controls which strategies are live for the current cycle.

    Usage:
        active = meta.get_active_strategies(snapshot, passing_strategies)
        # active is a Set[str] — only assign strategies in this set
    """

    def __init__(self):
        self._evolved_bases: Dict[str, str] = {}   # variant_name → base_strategy
        self._ml_weights:    Dict[str, float] = {} # strategy → ML-predicted weight
        self._load_evolved_index()
        log.info("[MetaStrategyController] Initialised. Regime map loaded for %d regimes.",
                 len(_REGIME_MAP))

    def set_ml_weights(self, weights: Dict[str, float]) -> None:
        """
        Receive ML-predicted strategy weights from the MetaLearningEngine.
        These are used to rank / prioritise strategies within the active set.
        weights — {strategy_name: float 0–1}, should sum to ≈ 1.0
        """
        self._ml_weights = dict(weights)
        top = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:3]
        log.info("[MetaStrategyController] ML weights updated. Top-3: %s",
                 "  ".join(f"{s}={w*100:.0f}%" for s, w in top))

    def get_ml_weights(self) -> Dict[str, float]:
        """Return the most recently set ML allocation weights."""
        return dict(self._ml_weights)

    def get_ranked_active_strategies(
        self,
        snapshot,
        passing_strategies: Set[str],
    ) -> List[str]:
        """
        Like get_active_strategies() but returns a *ranked* list, with
        ML-weight-preferred strategies appearing first.
        Falls back to alphabetical when no ML weights are set.
        """
        active = self.get_active_strategies(snapshot, passing_strategies)
        if self._ml_weights:
            return sorted(active,
                          key=lambda s: self._ml_weights.get(s, 0.0),
                          reverse=True)
        return sorted(active)

    # ─────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────

    def get_active_strategies(
        self,
        snapshot: MarketSnapshot,
        passing_strategies: Set[str],
    ) -> Set[str]:
        """
        Returns the set of strategy names that may be used this cycle.

        A strategy is included if:
          - It belongs to the regime's candidate list (or is a high-vol overlay)
          - AND it passes backtest quality gates (is in passing_strategies)
        Evolved variants whose base strategy is in the regime candidate list
        are also included if they pass quality gates.
        """
        regime_key  = snapshot.regime.value
        candidates  = set(_REGIME_MAP.get(regime_key, []))

        # High-volatility overlay — add extra strategies regardless of regime
        if snapshot.volatility == VolatilityLevel.HIGH:
            candidates.update(_HIGH_VOL_EXTRAS)

        # Range-market IV overlay — allow short volatility whenever IV is elevated
        if snapshot.regime == RegimeLabel.RANGE_MARKET:
            candidates.update(_RANGE_VOL_EXTRAS)

        # Include evolved variants whose base is a candidate
        for variant, base in self._evolved_bases.items():
            if base in candidates:
                candidates.add(variant)

        # Intersect with strategies that actually pass quality gates
        active = candidates & passing_strategies

        # Always keep Hedging_Model as a safety net even if it fails gates
        # (better a weak hedge than nothing in bear/volatile conditions)
        if snapshot.regime in (RegimeLabel.BEAR_MARKET, RegimeLabel.VOLATILE):
            active.add("Hedging_Model")

        return active

    def print_activation_report(
        self,
        snapshot: MarketSnapshot,
        passing_strategies: Set[str],
        all_strategies: List[str],
    ) -> None:
        """Log a formatted activation report for the current regime."""
        active   = self.get_active_strategies(snapshot, passing_strategies)
        regime_k = snapshot.regime.value
        candidates = set(_REGIME_MAP.get(regime_k, []))
        if snapshot.volatility == VolatilityLevel.HIGH:
            candidates.update(_HIGH_VOL_EXTRAS)
        for v, b in self._evolved_bases.items():
            if b in candidates:
                candidates.add(v)

        w = 74
        log.info("═" * w)
        log.info("  META-STRATEGY CONTROLLER  |  Regime: %-12s  VIX: %.1f",
                 snapshot.regime.value, snapshot.vix)
        log.info("═" * w)
        log.info("  %-32s  %s", "Strategy", "Status")
        log.info("  " + "─" * (w - 2))
        for s in sorted(all_strategies):
            in_regime  = s in candidates
            passes_bt  = s in passing_strategies
            is_active  = s in active

            if is_active:
                status = "✅ ACTIVE    — in regime + passes backtest"
            elif in_regime and not passes_bt:
                status = "⚠️  DISABLED  — in regime but fails quality gate"
            elif not in_regime and passes_bt:
                status = "💤 DORMANT   — passes backtest but wrong regime"
            else:
                status = "❌ INACTIVE  — wrong regime + fails quality gate"

            log.info("  %-32s  %s", s, status)
        log.info("  " + "─" * (w - 2))
        log.info("  %d / %d strategies active this cycle", len(active), len(all_strategies))
        log.info("═" * w)

    def as_agent_output(self, snapshot: MarketSnapshot,
                         passing_strategies: Set[str]) -> AgentOutput:
        active = self.get_active_strategies(snapshot, passing_strategies)
        return AgentOutput(
            agent_name="MetaStrategyController",
            status="ok",
            summary=f"{len(active)} strategies active for {snapshot.regime.value}",
            confidence=9.0,
            data={"active_strategies": sorted(active),
                  "regime": snapshot.regime.value,
                  "volatility": snapshot.volatility.value},
        )

    # ─────────────────────────────────────────────
    # PRIVATE
    # ─────────────────────────────────────────────

    def _load_evolved_index(self) -> None:
        """Build variant→base map from persisted evolved strategies."""
        if not os.path.exists(EVOLVED_STRATEGIES_PATH):
            return
        try:
            with open(EVOLVED_STRATEGIES_PATH, "r", encoding="utf-8") as f:
                evolved = json.load(f)
            for name, params in evolved.items():
                if params.get("approved"):
                    base = params.get("base_strategy", "")
                    if base:
                        self._evolved_bases[name] = base
        except Exception as exc:
            log.warning("[MetaStrategyController] Could not load evolved index: %s", exc)
