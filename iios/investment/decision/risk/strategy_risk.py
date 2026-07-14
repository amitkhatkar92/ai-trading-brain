"""iios/investment/decision/risk/strategy_risk.py
StrategyRiskEvaluator — derives strategy-specific risk from EvidenceSnapshot.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot


@dataclass(frozen=True)
class StrategyRiskResult:
    item_count:      int
    win_rate:        float   # 0–1 or -1 if unavailable
    sharpe_ratio:    float   # or -99 if unavailable
    signal_strength: float   # 0–100 or 0 if unavailable
    performance_risk: float  # 0–100 from win_rate/sharpe
    coverage_risk:   float   # 0–100 from missing strategy evidence
    strategy_risk:   float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_count":       self.item_count,
            "win_rate":         round(self.win_rate, 4),
            "sharpe_ratio":     round(self.sharpe_ratio, 4),
            "signal_strength":  round(self.signal_strength, 2),
            "performance_risk": round(self.performance_risk, 2),
            "coverage_risk":    round(self.coverage_risk, 2),
            "strategy_risk":    round(self.strategy_risk, 2),
        }


class StrategyRiskEvaluator:
    """Derives strategy dimension risk from EvidenceSnapshot."""

    _WIN_RATE_MIN    = 0.50   # below this = elevated risk
    _WIN_RATE_SAFE   = 0.60   # above this = lower risk
    _SHARPE_SAFE     = 1.0    # above this = acceptable
    _SIGNAL_STR_MIN  = 50.0   # below this = weak signal

    def evaluate(self, snapshot: EvidenceSnapshot) -> StrategyRiskResult:
        items = [i for i in snapshot.items if i.source_type == EvidenceSourceType.STRATEGY]

        win_rate      = -1.0
        sharpe_ratio  = -99.0
        signal_strength = 0.0

        for item in items:
            try:
                v = float(item.value)
                if item.key == "win_rate":
                    win_rate = v
                elif item.key == "sharpe_ratio":
                    sharpe_ratio = v
                elif item.key == "signal_strength":
                    signal_strength = v
            except (TypeError, ValueError):
                pass

        if not items:
            return StrategyRiskResult(
                item_count=0, win_rate=win_rate, sharpe_ratio=sharpe_ratio,
                signal_strength=signal_strength,
                performance_risk=70.0, coverage_risk=80.0, strategy_risk=75.0,
            )

        # Performance risk from win_rate
        if win_rate >= 0:
            if win_rate >= self._WIN_RATE_SAFE:
                perf_risk = 0.0
            elif win_rate >= self._WIN_RATE_MIN:
                perf_risk = (self._WIN_RATE_SAFE - win_rate) / (self._WIN_RATE_SAFE - self._WIN_RATE_MIN) * 40.0
            else:
                perf_risk = 40.0 + (self._WIN_RATE_MIN - win_rate) * 200.0
            perf_risk = min(100.0, perf_risk)
        else:
            perf_risk = 50.0   # no data = moderate risk

        # Sharpe adjustment
        if sharpe_ratio > self._SHARPE_SAFE:
            perf_risk = max(0.0, perf_risk - 10.0)
        elif sharpe_ratio >= 0.0:
            perf_risk = min(100.0, perf_risk + 10.0)

        # Signal strength risk
        sig_risk = max(0.0, self._SIGNAL_STR_MIN - signal_strength)

        coverage_risk = max(0.0, 60.0 - len(items) * 10.0)

        strategy_risk = (
            perf_risk    * 0.50
            + sig_risk   * 0.25
            + coverage_risk * 0.25
        )
        strategy_risk = max(0.0, min(100.0, strategy_risk))

        return StrategyRiskResult(
            item_count=len(items),
            win_rate=round(win_rate, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            signal_strength=round(signal_strength, 4),
            performance_risk=round(perf_risk, 4),
            coverage_risk=round(coverage_risk, 4),
            strategy_risk=round(strategy_risk, 4),
        )
