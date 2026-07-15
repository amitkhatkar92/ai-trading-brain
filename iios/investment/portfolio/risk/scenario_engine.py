"""iios/investment/portfolio/risk/scenario_engine.py

Applies individual stress scenarios to a portfolio of positions and
computes expected losses per scenario.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.risk.risk_types import RiskPosition
from iios.investment.portfolio.risk.scenario_library import Scenario


# Duration proxy is defined in interest_rate_risk; we replicate a minimal
# version here to avoid circular imports.
_DURATION_PROXY: Dict[str, float] = {
    "bond":           7.0,
    "fixed_income":   7.0,
    "debt":           5.0,
    "reit":           4.0,
    "infrastructure": 4.0,
    "utility":        3.0,
    "equity":         0.0,
    "cash":           0.1,
}

EQUITY_LIKE = frozenset(
    {"equity", "stock", "shares", "reit", "infrastructure"}
)
BOND_LIKE   = frozenset({"bond", "fixed_income", "debt"})


@dataclass(frozen=True)
class PositionStressImpact:
    """Stress impact on a single position."""
    symbol:         str
    weight:         float
    asset_class:    str
    sector:         str
    position_loss:  float   # as fraction of portfolio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":        self.symbol,
            "weight":        round(self.weight, 4),
            "position_loss": round(self.position_loss, 4),
        }


@dataclass(frozen=True)
class ScenarioResult:
    """Stress scenario result for the entire portfolio."""

    result_id:           str                       = field(default_factory=lambda: str(uuid.uuid4()))
    scenario_name:       str                       = ""
    scenario_description:str                       = ""
    severity:            str                       = ""

    # Total portfolio impact (negative = loss)
    portfolio_impact:    float                     = 0.0
    portfolio_loss_pct:  float                     = 0.0    # as percentage

    # Position-level impacts
    position_impacts:    tuple                     = field(default_factory=tuple)

    # Best and worst outcomes
    worst_position_loss: float                     = 0.0
    worst_position:      str                       = ""
    best_position_gain:  float                     = 0.0
    best_position:       str                       = ""

    # Attribution
    equity_contribution: float                     = 0.0
    bond_contribution:   float                     = 0.0
    rate_contribution:   float                     = 0.0
    fx_contribution:     float                     = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name":       self.scenario_name,
            "severity":            self.severity,
            "portfolio_impact":    round(self.portfolio_impact, 4),
            "portfolio_loss_pct":  round(self.portfolio_loss_pct * 100, 2),
            "worst_position":      self.worst_position,
            "worst_position_loss": round(self.worst_position_loss, 4),
        }


class ScenarioEngine:
    """Applies a single scenario to a list of positions."""

    def run(
        self,
        positions:    List[RiskPosition],
        scenario:     Scenario,
        portfolio_id: str = "",
    ) -> ScenarioResult:
        if not positions:
            return ScenarioResult(
                scenario_name=scenario.name,
                severity=scenario.severity.value,
            )

        pos_impacts: List[PositionStressImpact] = []
        equity_contr = bond_contr = rate_contr = fx_contr = 0.0

        for pos in positions:
            ac = pos.asset_class.lower()
            shock = 0.0

            # Equity shock
            if ac in EQUITY_LIKE:
                base = scenario.equity_shock
                # Sector-specific override
                if (scenario.sector_shocked
                        and pos.sector
                        and pos.sector.lower() == scenario.sector_shocked.lower()):
                    base = scenario.sector_shock
                # Scale by position risk_score (high-risk positions hurt more)
                risk_amplifier = 0.7 + pos.risk_score * 0.6
                shock += base * risk_amplifier
                equity_contr += pos.weight * shock

            # Bond shock
            elif ac in BOND_LIKE:
                base_bond = scenario.bond_shock
                # Add duration-based rate sensitivity
                dur = _DURATION_PROXY.get(ac, 0.0)
                rate_impact = -dur * scenario.rate_shock_bps / 10_000.0
                shock = base_bond + rate_impact
                bond_contr  += pos.weight * base_bond
                rate_contr  += pos.weight * rate_impact

            else:
                # Other: take smaller fraction of equity shock
                shock = scenario.equity_shock * 0.50

            # FX shock for foreign currency positions
            if pos.is_foreign_currency and scenario.currency_shock != 0.0:
                fx_loss = scenario.currency_shock
                shock  += fx_loss
                fx_contr += pos.weight * fx_loss

            # Liquidity cost (bid-ask widening)
            liq_cost = (scenario.liquidity_multiplier - 1.0) * (1.0 - pos.liquidity) * 0.02
            shock    -= liq_cost

            position_loss = pos.weight * shock
            pos_impacts.append(PositionStressImpact(
                symbol        = pos.symbol,
                weight        = pos.weight,
                asset_class   = pos.asset_class,
                sector        = pos.sector,
                position_loss = round(position_loss, 6),
            ))

        total_impact = sum(pi.position_loss for pi in pos_impacts)

        worst = min(pos_impacts, key=lambda x: x.position_loss)
        best  = max(pos_impacts, key=lambda x: x.position_loss)

        return ScenarioResult(
            scenario_name        = scenario.name,
            scenario_description = scenario.description,
            severity             = scenario.severity.value,
            portfolio_impact     = round(total_impact, 6),
            portfolio_loss_pct   = round(total_impact, 6),   # same, already a fraction
            position_impacts     = tuple(pos_impacts),
            worst_position_loss  = round(worst.position_loss, 6),
            worst_position       = worst.symbol,
            best_position_gain   = round(best.position_loss, 6),
            best_position        = best.symbol,
            equity_contribution  = round(equity_contr, 6),
            bond_contribution    = round(bond_contr, 6),
            rate_contribution    = round(rate_contr, 6),
            fx_contribution      = round(fx_contr, 6),
        )
