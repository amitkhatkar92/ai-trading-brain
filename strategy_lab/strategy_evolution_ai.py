"""
Strategy Evolution AI — Layer 4 Agent 2
=========================================
Uses a genetic algorithm to discover better strategy parameter combinations.

For each base strategy (e.g. Breakout_Volume), the GA generates variants
with different technical filter combinations:

  Genes mutated per variant:
    • lookback_days        — 10, 15, 20, 25, 30 …
    • volume_ratio         — 1.5×, 2.0×, 2.5×, 3.0×
    • use_rsi_filter       — True / False
    • rsi_min / rsi_max    — entry RSI band
    • stop_loss_pct        — 1% – 4%
    • target_multiplier    — 1.5× – 4.0×

After the GA, every elite variant is sent through the full
BacktestingAI pipeline (WFT + OOS + Cross-market).  Variants that
pass all quality gates are:
  1. Named automatically     e.g. Breakout_Volume_RSI, Breakout_Volume_HiVol
  2. Logged with a before/after comparison table
  3. Persisted to data/evolved_strategies.json
  4. Registered in _BACKTEST_CACHE so StrategyGeneratorAI can use them

This runs on EOD or weekly basis (not every cycle).
"""

from __future__ import annotations
import copy
import json
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models.trade_signal import TradeSignal
from models.agent_output import AgentOutput
from config import EVOLUTION_GENERATIONS, EVOLUTION_POPULATION
from utils import get_logger

log = get_logger(__name__)

EVOLVED_STRATEGIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "evolved_strategies.json"
)

# Shared mutable parameter store (updated by evolution, read by StrategyGeneratorAI)
EVOLVED_PARAMS: Dict[str, Dict[str, Any]] = {}


# ── Variant dataclass ─────────────────────────────────────────────────────────

@dataclass
class StrategyVariant:
    """One candidate strategy configuration produced by the GA."""
    base_strategy:    str
    lookback_days:    int          = 20
    volume_ratio:     float        = 1.5
    use_rsi_filter:   bool         = False
    rsi_min:          int          = 50
    rsi_max:          int          = 65
    stop_loss_pct:    float        = 0.02
    target_multiplier: float       = 2.0
    confidence_modifier: float     = 0.0
    # Filled after backtesting
    variant_name:     str          = ""
    approved:         bool         = False
    cross_market_rate: float       = 0.0
    wf_consistency:   float        = 0.0
    overfitting_ratio: float       = 1.0
    approved_at:      str          = ""

    def auto_name(self) -> str:
        """Generate a human-readable variant name from its active filters."""
        parts: List[str] = []
        if self.use_rsi_filter:
            parts.append("RSI")
        if self.volume_ratio >= 2.0:
            parts.append("HiVol")
        if self.lookback_days <= 15:
            parts.append("Fast")
        elif self.lookback_days >= 25:
            parts.append("Slow")
        if not parts:
            parts.append("v1")
        return f"{self.base_strategy}_{'_'.join(parts)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_strategy":    self.base_strategy,
            "lookback_days":    self.lookback_days,
            "volume_ratio":     self.volume_ratio,
            "use_rsi_filter":   self.use_rsi_filter,
            "rsi_min":          self.rsi_min,
            "rsi_max":          self.rsi_max,
            "stop_loss_pct":    self.stop_loss_pct,
            "target_multiplier":self.target_multiplier,
            "confidence_modifier": self.confidence_modifier,
            "variant_name":     self.variant_name,
            "approved":         self.approved,
            "cross_market_rate":self.cross_market_rate,
            "wf_consistency":   self.wf_consistency,
            "overfitting_ratio":self.overfitting_ratio,
            "approved_at":      self.approved_at,
        }


class StrategyEvolutionAI:
    """
    Genetic algorithm–based strategy parameter optimiser.

    Main flow
    ---------
    run_evolution(strategy_name)
      → generate 30 variants (population)
      → evolve for 50 generations
      → score by heuristic fitness
      → take top-5 elite variants
      → run each through BacktestingAI (full WFT + OOS + cross-market)
      → print before/after table
      → persist approved variants to disk
    """

    ELITE_SIZE        = 5    # How many elite variants get sent to BacktestingAI

    def __init__(self):
        self.generations   = EVOLUTION_GENERATIONS
        self.pop_size      = EVOLUTION_POPULATION
        self.mutation_rate = 0.15
        # Lazy-imported to avoid circular imports
        self._backtesting_ai = None
        log.info("[StrategyEvolutionAI] Initialised. Generations=%d Pop=%d",
                 self.generations, self.pop_size)

    def _get_backtesting_ai(self):
        if self._backtesting_ai is None:
            from strategy_lab.backtesting_ai import BacktestingAI
            self._backtesting_ai = BacktestingAI()
        return self._backtesting_ai

    # ─────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────

    def apply_evolved_params(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Apply best-known evolved parameters to signals (confidence boost/penalty)."""
        for signal in signals:
            params = EVOLVED_PARAMS.get(signal.strategy_name)
            if params and "confidence_modifier" in params:
                signal.confidence = min(
                    10.0,
                    signal.confidence + params["confidence_modifier"]
                )
        return signals

    def run_evolution(self, strategy_name: str) -> List[StrategyVariant]:
        """
        Run full GA + backtest pipeline for one base strategy.
        Returns list of approved variants.
        """
        log.info("[StrategyEvolutionAI] ═══ Starting evolution: '%s' ═══", strategy_name)

        # ── 1. Fetch base strategy backtest (the "before" benchmark) ─────
        bt = self._get_backtesting_ai()
        base_result = bt.run_full_backtest(strategy_name)

        # ── 2. Run GA ────────────────────────────────────────────────────
        population = self._init_population(strategy_name)

        for gen in range(self.generations):
            scored = [(v, self._evaluate(v)) for v in population]
            scored.sort(key=lambda x: x[1], reverse=True)
            elite_variants = [v for v, _ in scored[:max(2, self.pop_size // 5)]]

            if gen % 10 == 0:
                log.debug("[StrategyEvolutionAI] Gen %d | Best fitness=%.3f",
                          gen, scored[0][1])

            population = self._next_generation(elite_variants)

        # Top-N go to full backtesting
        scored_final = sorted(
            [(v, self._evaluate(v)) for v in population],
            key=lambda x: x[1], reverse=True
        )
        top_variants = [v for v, _ in scored_final[:self.ELITE_SIZE]]

        # ── 3. Backtest every elite variant ──────────────────────────────
        approved: List[StrategyVariant] = []
        tested_names: set = set()

        for variant in top_variants:
            name = variant.auto_name()
            # Deduplicate identical variant names
            if name in tested_names:
                continue
            tested_names.add(name)
            variant.variant_name = name

            result = bt.backtest_variant(name, variant.to_dict())
            variant.cross_market_rate = result.cross_market_pass_rate
            variant.wf_consistency    = result.wf_consistency
            variant.overfitting_ratio = result.overfitting_ratio

            if result.passes_gate:
                variant.approved   = True
                variant.approved_at = datetime.now().isoformat()
                variant.confidence_modifier = round(
                    (0.5 * result.sharpe) / max(result.overfitting_ratio, 1.0), 2
                )
                EVOLVED_PARAMS[name] = variant.to_dict()
                approved.append(variant)
                log.info("[StrategyEvolutionAI] ✅ APPROVED: %s | "
                         "XMkt=%.0f%% WF=%.0f%% OvFit=%.2f",
                         name, result.cross_market_pass_rate * 100,
                         result.wf_consistency * 100, result.overfitting_ratio)
            else:
                log.info("[StrategyEvolutionAI] ❌ REJECTED: %s | %s",
                         name, "; ".join(result.failure_reasons))

        # ── 4. Print before/after table ──────────────────────────────────
        self._print_evolution_table(strategy_name, base_result, top_variants)

        # ── 5. Persist approved variants to disk ─────────────────────────
        if approved:
            self._persist(approved)

        return approved

    # ─────────────────────────────────────────────
    # PRIVATE — GENETIC ALGORITHM
    # ─────────────────────────────────────────────

    def _init_population(self, strategy_name: str) -> List[StrategyVariant]:
        population: List[StrategyVariant] = []
        for _ in range(self.pop_size):
            v = StrategyVariant(
                base_strategy    = strategy_name,
                lookback_days    = random.choice([10, 15, 20, 25, 30]),
                volume_ratio     = round(random.uniform(1.5, 3.0), 1),
                use_rsi_filter   = random.random() > 0.5,
                rsi_min          = random.randint(45, 55),
                rsi_max          = random.randint(60, 72),
                stop_loss_pct    = round(random.uniform(0.01, 0.04), 3),
                target_multiplier= round(random.uniform(1.5, 4.0), 2),
                confidence_modifier = round(random.uniform(-1.0, 1.0), 2),
            )
            population.append(v)
        return population

    def _evaluate(self, v: StrategyVariant) -> float:
        """
        Heuristic fitness — higher is better.
        Rewards: high target multiplier, RSI filter, tight stops,
                 sensible RSI band, high volume threshold.
        """
        score = v.target_multiplier * 2.0
        score -= v.stop_loss_pct * 50
        score += 1.5 if v.use_rsi_filter else 0.0
        score += 0.5 if 48 <= v.rsi_min <= 55 else 0.0
        score += 0.5 if v.volume_ratio >= 2.0 else 0.0
        score += 0.3 if v.lookback_days in (15, 20) else 0.0
        return round(score, 4)

    def _next_generation(self, elite: List[StrategyVariant]) -> List[StrategyVariant]:
        new_pop: List[StrategyVariant] = list(elite)
        while len(new_pop) < self.pop_size:
            p1, p2 = random.sample(elite, 2)
            child  = self._crossover(p1, p2)
            child  = self._mutate(child)
            new_pop.append(child)
        return new_pop

    def _crossover(self, p1: StrategyVariant,
                   p2: StrategyVariant) -> StrategyVariant:
        pick = lambda a, b: a if random.random() < 0.5 else b
        return StrategyVariant(
            base_strategy    = p1.base_strategy,
            lookback_days    = pick(p1.lookback_days,    p2.lookback_days),
            volume_ratio     = pick(p1.volume_ratio,     p2.volume_ratio),
            use_rsi_filter   = pick(p1.use_rsi_filter,   p2.use_rsi_filter),
            rsi_min          = pick(p1.rsi_min,          p2.rsi_min),
            rsi_max          = pick(p1.rsi_max,          p2.rsi_max),
            stop_loss_pct    = pick(p1.stop_loss_pct,    p2.stop_loss_pct),
            target_multiplier= pick(p1.target_multiplier,p2.target_multiplier),
            confidence_modifier = pick(p1.confidence_modifier, p2.confidence_modifier),
        )

    def _mutate(self, v: StrategyVariant) -> StrategyVariant:
        v = copy.copy(v)
        if random.random() < self.mutation_rate:
            v.lookback_days     = random.choice([10, 15, 20, 25, 30])
        if random.random() < self.mutation_rate:
            v.volume_ratio      = round(random.uniform(1.5, 3.0), 1)
        if random.random() < self.mutation_rate:
            v.use_rsi_filter    = not v.use_rsi_filter
        if random.random() < self.mutation_rate:
            v.stop_loss_pct     = round(random.uniform(0.01, 0.04), 3)
        if random.random() < self.mutation_rate:
            v.target_multiplier = round(random.uniform(1.5, 4.0), 2)
        if random.random() < self.mutation_rate:
            v.confidence_modifier = round(random.uniform(-1.0, 1.0), 2)
        return v

    # ─────────────────────────────────────────────
    # PRIVATE — REPORTING
    # ─────────────────────────────────────────────

    def _print_evolution_table(self, base_name: str, base_result,
                                tested: List[StrategyVariant]):
        """Print a before/after comparison table to stdout."""
        w = 100
        print("\n" + "═" * w)
        print(f"  EVOLUTION RESULTS  |  Base strategy: {base_name}")
        print("═" * w)

        # Header
        print(f"  {'Variant':<38} {'Lookback':>8} {'Vol':>5} {'RSI':>5} "
              f"{'XMkt%':>6} {'WF%':>5} {'OvFit':>6} {'Status':>10}")
        print("─" * w)

        # Base (before)
        base_status = "PASS ✅" if base_result.passes_gate else "FAIL ❌"
        print(f"  {base_name + ' [BASE]':<38} {'20':>8} {'1.5x':>5} {'No':>5} "
              f"{base_result.cross_market_pass_rate:>6.0%} "
              f"{base_result.wf_consistency:>5.0%} "
              f"{base_result.overfitting_ratio:>6.2f} "
              f"{base_status:>10}")

        print("  " + "·" * (w - 4))

        # Each tested variant (after)
        for v in tested:
            status = "APPROVED ✅" if v.approved else "REJECTED ❌"
            rsi_str = f"{v.rsi_min}-{v.rsi_max}" if v.use_rsi_filter else "Off"
            print(f"  {v.variant_name:<38} {v.lookback_days:>8}d "
                  f"{v.volume_ratio:>4.1f}x {rsi_str:>5} "
                  f"{v.cross_market_rate:>6.0%} "
                  f"{v.wf_consistency:>5.0%} "
                  f"{v.overfitting_ratio:>6.2f} "
                  f"{status:>10}")

        print("═" * w + "\n")

    # ─────────────────────────────────────────────
    # PRIVATE — PERSISTENCE
    # ─────────────────────────────────────────────

    def _persist(self, variants: List[StrategyVariant]):
        """Save approved variants to data/evolved_strategies.json."""
        os.makedirs(os.path.dirname(EVOLVED_STRATEGIES_PATH), exist_ok=True)

        # Load existing
        existing: Dict[str, Any] = {}
        if os.path.exists(EVOLVED_STRATEGIES_PATH):
            try:
                with open(EVOLVED_STRATEGIES_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        for v in variants:
            existing[v.variant_name] = v.to_dict()

        with open(EVOLVED_STRATEGIES_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        log.info("[StrategyEvolutionAI] Persisted %d approved variants → %s",
                 len(variants), EVOLVED_STRATEGIES_PATH)

