"""iios/investment/portfolio/risk/scenario_library.py

Built-in stress-test scenario definitions. All shocks are expressed as
fractional changes (e.g., -0.35 = 35% loss).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.risk.risk_types import StressTestSeverity


@dataclass(frozen=True)
class Scenario:
    """A single stress test scenario definition."""

    name:                str
    description:         str
    severity:            StressTestSeverity

    # Shocks to apply
    equity_shock:        float   = 0.0    # fractional portfolio loss for equity
    bond_shock:          float   = 0.0    # fractional loss for bonds
    currency_shock:      float   = 0.0    # FX depreciation (applied to foreign positions)
    rate_shock_bps:      float   = 0.0    # parallel rate shift in basis points
    liquidity_multiplier:float   = 1.0    # bid-ask spread widening multiple
    vol_multiplier:      float   = 1.0    # implied vol scaling

    # Sector-specific shock (override equity_shock for a specific sector)
    sector_shocked:      Optional[str] = None
    sector_shock:        float   = 0.0    # additional sector-specific shock

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":                self.name,
            "severity":            self.severity.value,
            "equity_shock":        self.equity_shock,
            "bond_shock":          self.bond_shock,
            "currency_shock":      self.currency_shock,
            "rate_shock_bps":      self.rate_shock_bps,
            "liquidity_multiplier":self.liquidity_multiplier,
            "vol_multiplier":      self.vol_multiplier,
        }


# ---------------------------------------------------------------------------
# Built-in scenario library
# ---------------------------------------------------------------------------

SCENARIOS: Dict[str, Scenario] = {
    "market_crash": Scenario(
        name="Market Crash",
        description="Global equity bear market: -35% equities, rising credit spreads",
        severity=StressTestSeverity.SEVERE,
        equity_shock=-0.35,
        bond_shock=-0.05,
        currency_shock=-0.08,
        rate_shock_bps=100,
        liquidity_multiplier=3.0,
        vol_multiplier=2.5,
    ),
    "volatility_shock": Scenario(
        name="Volatility Shock",
        description="VIX spike: VaR doubles, liquidity dries up",
        severity=StressTestSeverity.MODERATE,
        equity_shock=-0.15,
        bond_shock=0.02,
        rate_shock_bps=0,
        liquidity_multiplier=5.0,
        vol_multiplier=3.0,
    ),
    "rate_shock_up": Scenario(
        name="Rate Shock Up +200bps",
        description="Hawkish central bank: rates rise 200bps",
        severity=StressTestSeverity.MODERATE,
        equity_shock=-0.10,
        bond_shock=-0.12,
        rate_shock_bps=200,
        vol_multiplier=1.5,
    ),
    "rate_shock_down": Scenario(
        name="Rate Shock Down -100bps",
        description="Dovish cut: rates fall 100bps; duration positions rally",
        severity=StressTestSeverity.MILD,
        equity_shock=0.05,
        bond_shock=0.08,
        rate_shock_bps=-100,
        vol_multiplier=1.0,
    ),
    "inflation_shock": Scenario(
        name="Inflation Shock +300bps",
        description="Unexpected inflation surge: nominal bonds sell off, equities pressured",
        severity=StressTestSeverity.MODERATE,
        equity_shock=-0.12,
        bond_shock=-0.18,
        rate_shock_bps=300,
        vol_multiplier=1.8,
    ),
    "liquidity_crisis": Scenario(
        name="Liquidity Crisis",
        description="Market freeze: bid-ask widens 5×, fire-sale discounts",
        severity=StressTestSeverity.SEVERE,
        equity_shock=-0.20,
        bond_shock=-0.08,
        liquidity_multiplier=5.0,
        vol_multiplier=2.0,
    ),
    "currency_shock": Scenario(
        name="Currency Shock -20% FX",
        description="EM currency collapse: foreign holdings lose 20% in local terms",
        severity=StressTestSeverity.MODERATE,
        equity_shock=-0.08,
        currency_shock=-0.20,
        vol_multiplier=1.6,
    ),
    "sector_crash_tech": Scenario(
        name="Tech Sector Crash",
        description="Technology sector sell-off: -40% for technology/IT",
        severity=StressTestSeverity.SEVERE,
        equity_shock=-0.15,
        sector_shocked="technology",
        sector_shock=-0.40,
        vol_multiplier=2.0,
    ),
    "black_swan": Scenario(
        name="Black Swan Event",
        description="Extreme unexpected shock: -60% for high-risk positions, markets frozen",
        severity=StressTestSeverity.BLACK_SWAN,
        equity_shock=-0.50,
        bond_shock=-0.15,
        currency_shock=-0.25,
        rate_shock_bps=300,
        liquidity_multiplier=10.0,
        vol_multiplier=5.0,
    ),
    "covid_crash": Scenario(
        name="COVID-style Pandemic Crash",
        description="Rapid lockdown: -38% equities in 5 weeks, flight to safety",
        severity=StressTestSeverity.EXTREME,
        equity_shock=-0.38,
        bond_shock=0.05,
        currency_shock=-0.15,
        liquidity_multiplier=4.0,
        vol_multiplier=4.0,
    ),
    "gfc_crisis": Scenario(
        name="GFC-style Financial Crisis",
        description="2008-style: -55% equities, credit markets frozen, bank failures",
        severity=StressTestSeverity.EXTREME,
        equity_shock=-0.55,
        bond_shock=-0.10,
        currency_shock=-0.20,
        rate_shock_bps=200,
        liquidity_multiplier=8.0,
        vol_multiplier=4.5,
    ),
}
