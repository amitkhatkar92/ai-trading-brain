"""
Candidate Strategy Generator — Edge Discovery Engine Module 3
=============================================================
Converts a DiscoveredPattern into a fully-specified strategy template
that is compatible with the existing StrategyGeneratorAI / BacktestingAI
pipeline.

A discovered pattern has the form:

  IF  volume_spike > 0.5
  AND rsi_oversold > 0.5
  AND sector_strength > 0.4
  THEN positive move with 63% probability

This module translates that into:

  EDG_momentum_volume_0012:
    base_strategy:   Breakout_Volume
    entry_condition: volume_ratio > 2.0 AND rsi < 35 AND sector_strength > 0.4
    direction:       BUY
    stop_loss_pct:   0.020
    target_multiplier: 2.5
    min_rr:          2.0
    source:          EdgeDiscoveryEngine
    pattern_id:      TREE_0012

The generated strategy is registered in:
  1. STRATEGY_PARAMS   (in-memory — for immediate use this cycle)
  2. data/evolved_strategies.json  (persisted — survives restart)
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .pattern_miner import DiscoveredPattern, PatternCondition
from utils import get_logger

log = get_logger(__name__)

EVOLVED_STRATEGIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "evolved_strategies.json"
)

# ── Base strategy templates keyed by edge category ─────────────────────────
_CATEGORY_TO_BASE = {
    "momentum_volume":  "Breakout_Volume",
    "momentum_trend":   "Momentum_Retest",
    "mean_reversion":   "Mean_Reversion",
    "volatility":       "Short_Straddle_IV_Spike",
    "macro_flow":       "Breakout_Volume",
    "gap":              "Breakout_Volume",
    "composite":        "Breakout_Volume",
}

# ── Parameter bounds derived by category ───────────────────────────────────
_CATEGORY_PARAMS = {
    "momentum_volume":  {"min_rr": 2.0, "max_loss_pct": 0.020, "stop_mult": 1.0,  "tgt_mult": 2.5},
    "momentum_trend":   {"min_rr": 1.8, "max_loss_pct": 0.025, "stop_mult": 1.2,  "tgt_mult": 2.2},
    "mean_reversion":   {"min_rr": 1.5, "max_loss_pct": 0.015, "stop_mult": 0.8,  "tgt_mult": 1.8},
    "volatility":       {"min_rr": 1.5, "max_loss_pct": 0.015, "stop_mult": 1.0,  "tgt_mult": 2.0},
    "macro_flow":       {"min_rr": 2.0, "max_loss_pct": 0.020, "stop_mult": 1.0,  "tgt_mult": 2.5},
    "gap":              {"min_rr": 1.6, "max_loss_pct": 0.018, "stop_mult": 0.9,  "tgt_mult": 2.0},
    "composite":        {"min_rr": 1.8, "max_loss_pct": 0.020, "stop_mult": 1.0,  "tgt_mult": 2.2},
}


@dataclass
class CandidateStrategy:
    """
    A strategy generated from a DiscoveredPattern.

    This is the bridge between EDE and the Strategy Lab — once
    strategy_tester validates it we persist it to the shared
    evolved_strategies.json.
    """
    name:            str
    base_strategy:   str
    pattern_id:      str
    category:        str
    direction:       str                    # "BUY" | "SELL" | "BOTH"
    entry_conditions: List[Dict[str, Any]]  # human-readable conditions
    stop_loss_pct:   float
    target_multiplier: float
    min_rr:          float
    max_loss_pct:    float
    precision:       float                  # pattern precision from miner
    support:         int                    # pattern support from miner
    expected_return: float
    description:     str
    created_at:      str                    = field(
        default_factory=lambda: datetime.now().isoformat())
    approved:        bool                   = False   # set by strategy_tester

    def to_strategy_params(self) -> Dict[str, Any]:
        """Return a STRATEGY_PARAMS-compatible dict."""
        return {
            "min_rr":           self.min_rr,
            "max_loss_pct":     self.max_loss_pct,
            "stop_loss_pct":    self.stop_loss_pct,
            "target_multiplier":self.target_multiplier,
            "base_strategy":    self.base_strategy,
            "source":           "EdgeDiscoveryEngine",
            "pattern_id":       self.pattern_id,
            "category":         self.category,
            "direction":        self.direction,
            "entry_conditions": self.entry_conditions,
            "precision":        self.precision,
            "support":          self.support,
            "expected_return":  self.expected_return,
            "description":      self.description,
            "approved":         self.approved,
            "created_at":       self.created_at,
        }


class CandidateStrategyGenerator:
    """
    Converts DiscoveredPattern objects into CandidateStrategy objects.
    """

    def __init__(self) -> None:
        log.info("[CandidateStrategyGenerator] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(self, patterns: List[DiscoveredPattern]) -> List[CandidateStrategy]:
        """
        Convert a list of patterns → candidate strategies.
        One pattern → at most one candidate.
        """
        candidates: List[CandidateStrategy] = []
        seen_names: set = set()

        for pat in patterns:
            try:
                cand = self._convert(pat)
                if cand.name not in seen_names:
                    seen_names.add(cand.name)
                    candidates.append(cand)
            except Exception as exc:
                log.debug("[CandidateStrategyGenerator] Skipped pattern %s: %s",
                          pat.pattern_id, exc)

        log.info("[CandidateStrategyGenerator] Generated %d candidates from %d patterns.",
                 len(candidates), len(patterns))
        return candidates

    def persist_approved(self, candidates: List[CandidateStrategy]) -> int:
        """
        Write approved candidates to evolved_strategies.json so that
        StrategyGeneratorAI picks them up on the next cycle.
        Returns the number of new strategies written.
        """
        approved = [c for c in candidates if c.approved]
        if not approved:
            return 0

        existing: Dict[str, Any] = {}
        if os.path.exists(EVOLVED_STRATEGIES_PATH):
            try:
                with open(EVOLVED_STRATEGIES_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        added = 0
        for cand in approved:
            if cand.name not in existing:
                existing[cand.name] = cand.to_strategy_params()
                added += 1
            else:
                # Update if our new version has higher precision
                prev = existing[cand.name]
                if cand.precision > prev.get("precision", 0):
                    existing[cand.name] = cand.to_strategy_params()

        os.makedirs(os.path.dirname(EVOLVED_STRATEGIES_PATH), exist_ok=True)
        with open(EVOLVED_STRATEGIES_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        log.info("[CandidateStrategyGenerator] Persisted %d new approved "
                 "strategies to evolved_strategies.json.", added)
        return added

    # ── Internal ───────────────────────────────────────────────────────────

    def _convert(self, pat: DiscoveredPattern) -> CandidateStrategy:
        base  = _CATEGORY_TO_BASE.get(pat.category, "Breakout_Volume")
        parms = _CATEGORY_PARAMS.get(pat.category, _CATEGORY_PARAMS["composite"])

        # Name: EDG_<category prefix>_<precision%>_<pid suffix>
        short_cat = pat.category[:6].upper()
        prec_pct  = int(pat.precision * 100)
        pid_suf   = pat.pattern_id.replace("_", "")[-6:]
        name      = f"EDG_{short_cat}_{prec_pct}_{pid_suf}"

        # Determine direction from conditions
        direction = self._infer_direction(pat.conditions, pat.category)

        # Human-readable entry conditions
        entry_conds = [
            {"feature": c.feature, "operator": c.operator,
             "threshold": round(c.threshold, 4)}
            for c in pat.conditions
        ]

        return CandidateStrategy(
            name              = name,
            base_strategy     = base,
            pattern_id        = pat.pattern_id,
            category          = pat.category,
            direction         = direction,
            entry_conditions  = entry_conds,
            stop_loss_pct     = parms["stop_mult"] * parms["max_loss_pct"],
            target_multiplier = parms["tgt_mult"],
            min_rr            = parms["min_rr"],
            max_loss_pct      = parms["max_loss_pct"],
            precision         = pat.precision,
            support           = pat.support,
            expected_return   = pat.expected_return,
            description       = pat.description or
                                 f"EDE-discovered {pat.category} edge (prec={pat.precision:.0%})",
        )

    @staticmethod
    def _infer_direction(conditions: List[PatternCondition], category: str) -> str:
        feats  = {c.feature.lower() for c in conditions}
        if category in ("mean_reversion",):
            # Could be either — check if RSI oversold (BUY) or overbought (SELL)
            for c in conditions:
                if "rsi_oversold" in c.feature.lower() and c.operator == ">":
                    return "BUY"
                if "rsi_overbought" in c.feature.lower() and c.operator == ">":
                    return "SELL"
        if any(k in feats for k in ("gap_down", "macd_bear", "regime_bear")):
            return "SELL"
        # Default: bullish edge
        return "BUY"
