"""
Validation Engine — Parameter Sensitivity Analysis
===================================================
An overfit strategy is typically fragile: it performs well only at an exact
parameter value and degrades sharply as soon as that value is moved even
slightly.  A robust system shows a smooth performance landscape.

This module grid-searches each key parameter ±N steps and builds a
sensitivity map.  It then:
  1. Detects "cliff" drops — any adjacent steps where Sharpe falls > 50%
  2. Computes a Stability Score (0–100) based on std-dev of the performance
     surface (lower variance = more stable)
  3. Identifies the optimal parameter set (highest Sharpe in inner region)

Institutional threshold:
  • Stability Score  ≥ 60
  • No cliff detected in any parameter

A signal_fn is optional.  When provided, real signals are regenerated for each
parameter combination.  When absent (default), performance is simulated from
the base P&L with additive perturbation — useful for quick sanity checks.
"""

from __future__ import annotations
import math
import random
import statistics as _stats
from dataclasses import dataclass, field
from typing import Callable, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
MIN_STABILITY_SCORE = 60.0     # 0–100
CLIFF_THRESHOLD     = 0.50     # 50% drop between adjacent steps = cliff
N_STEPS_PER_SIDE    = 4        # test ±4 steps around nominal


@dataclass
class ParamGrid:
    name:     str
    nominal:  float            # current "best" value
    step:     float            # how much to move per step
    n_steps:  int = N_STEPS_PER_SIDE


@dataclass
class ParamVariantResult:
    param_name:  str
    param_value: float
    sharpe:      float
    return_pct:  float


@dataclass
class SensitivityResult:
    strategy_name:   str
    params_tested:   list[str] = field(default_factory=list)
    stability_score: float     = 0.0   # 0–100 (higher = more robust)
    cliff_detected:  bool      = False
    cliff_details:   list[str] = field(default_factory=list)
    optimal_params:  dict      = field(default_factory=dict)
    sensitivity_map: dict      = field(default_factory=dict)  # name → list[ParamVariantResult]
    passed:          bool      = False

    def summary(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ FAILED"
        cliff   = "⚠️  CLIFF DETECTED" if self.cliff_detected else "No cliff"
        return (f"[Sensitivity] {verdict} | {self.strategy_name} | "
                f"Stability: {self.stability_score:.1f}/100  {cliff}")


class ParameterSensitivityAnalyzer:
    """
    Analyses sensitivity of strategy performance to parameter changes.

    Usage (with explicit signal function)::
        grids  = [ParamGrid("rsi_period", 14, 1), ParamGrid("stop_pct", 2.0, 0.25)]
        result = ParameterSensitivityAnalyzer().run(
                     "RSI_Strategy", base_pnl, 1_000_000,
                     param_grids=grids,
                     signal_fn=my_signal_fn,
                 )

    Usage (without signal function — perturbation mode)::
        result = ParameterSensitivityAnalyzer().run(
                     "RSI_Strategy", base_pnl, 1_000_000,
                     param_grids=grids,
                 )
    """

    def __init__(self, seed: int = 13) -> None:
        self._rng = random.Random(seed)
        log.info("[ParameterSensitivity] Initialised.")

    # ── Public API ────────────────────────────────────────────────────────
    def run(self,
            strategy_name: str,
            base_pnl:      list[float],
            capital:       float = 1_000_000,
            param_grids:   Optional[list[ParamGrid]] = None,
            signal_fn:     Optional[Callable]        = None,
            ) -> SensitivityResult:

        if not param_grids:
            # Default: two synthetic parameters for demonstration
            param_grids = [
                ParamGrid("rsi_period",    14,  1.0),
                ParamGrid("stop_pct",       2.0, 0.25),
                ParamGrid("lookback_days", 20,  2.0),
            ]

        base_sharpe  = self._sharpe(base_pnl, capital)
        sensitivity_map: dict[str, list[ParamVariantResult]] = {}
        all_sharpes:  list[float] = []
        cliff_details: list[str]  = []
        optimal_params: dict      = {}

        for pg in param_grids:
            variants: list[ParamVariantResult] = []
            for step in range(-pg.n_steps, pg.n_steps + 1):
                param_val = pg.nominal + step * pg.step
                if param_val <= 0:
                    continue
                if signal_fn is not None:
                    pnl_series = signal_fn(pg.name, param_val)
                else:
                    pnl_series = self._perturb(base_pnl, step, pg.n_steps)

                sh  = self._sharpe(pnl_series, capital)
                ret = sum(pnl_series) / capital * 100
                variants.append(ParamVariantResult(
                    param_name  = pg.name,
                    param_value = round(param_val, 4),
                    sharpe      = round(sh,  3),
                    return_pct  = round(ret, 3),
                ))
                all_sharpes.append(sh)

            sensitivity_map[pg.name] = variants

            # Cliff detection on sharpe curve
            for i in range(1, len(variants)):
                prev = variants[i-1].sharpe
                curr = variants[i].sharpe
                if prev > 0 and curr < prev * (1 - CLIFF_THRESHOLD):
                    detail = (f"{pg.name}: cliff from {prev:.2f} → {curr:.2f} "
                              f"at value {variants[i].param_value}")
                    cliff_details.append(detail)
                    log.warning("[Sensitivity] CLIFF detected: %s", detail)

            # Best variant for this param (near nominal, i.e. inner region)
            inner = [v for v in variants
                     if abs(v.param_value - pg.nominal) <= 2 * pg.step]
            if inner:
                best = max(inner, key=lambda v: v.sharpe)
                optimal_params[pg.name] = best.param_value

        # Stability score — lower sharpe variance = more stable
        stability = self._stability_score(all_sharpes, base_sharpe)
        cliff_det = len(cliff_details) > 0
        passed    = stability >= MIN_STABILITY_SCORE and not cliff_det

        result = SensitivityResult(
            strategy_name   = strategy_name,
            params_tested   = [pg.name for pg in param_grids],
            stability_score = round(stability, 1),
            cliff_detected  = cliff_det,
            cliff_details   = cliff_details,
            optimal_params  = optimal_params,
            sensitivity_map = sensitivity_map,
            passed          = passed,
        )
        log.info(result.summary())
        if cliff_details:
            for cd in cliff_details:
                log.warning("[Sensitivity]   → %s", cd)
        return result

    # ── Private helpers ───────────────────────────────────────────────────
    def _perturb(self, base_pnl: list[float], step: int,
                 n_steps: int) -> list[float]:
        """
        Simulate performance degradation as we move away from nominal.
        Center (step=0) = base.  Outer steps get increasing noise + drift.
        """
        rng       = self._rng
        dist_frac = abs(step) / max(n_steps, 1)   # 0..1
        noise_std = dist_frac * 0.08               # 8% noise at extremes
        drift     = -dist_frac * 0.05              # mild deterioration away

        perturbed = []
        for p in base_pnl:
            noise   = rng.gauss(0, abs(p) * noise_std) if p != 0 else 0
            adjusted = p * (1 + drift) + noise
            perturbed.append(adjusted)
        return perturbed

    @staticmethod
    def _sharpe(pnl: list[float], capital: float) -> float:
        if len(pnl) < 2:
            return 0.0
        rets = [p / capital for p in pnl]
        mu   = _stats.mean(rets)
        std  = _stats.stdev(rets)
        return (mu / std) * math.sqrt(252) if std > 0 else 0.0

    @staticmethod
    def _stability_score(sharpes: list[float], base_sharpe: float) -> float:
        """
        Score = 100 × (1 – coefficient_of_variation).
        Clamped to [0, 100].
        """
        if not sharpes or len(sharpes) < 2:
            return 50.0
        positive = [s for s in sharpes if s > 0]
        if not positive:
            return 0.0
        mean_sh = _stats.mean(positive)
        std_sh  = _stats.stdev(positive) if len(positive) > 1 else 0.0
        if mean_sh <= 0:
            return 0.0
        cv      = std_sh / mean_sh
        score   = (1 - cv) * 100
        return max(0.0, min(100.0, score))
