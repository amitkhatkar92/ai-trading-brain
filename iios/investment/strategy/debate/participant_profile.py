"""iios/investment/strategy/debate/participant_profile.py
ParticipantProfile and default agent weights.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import ParticipantRole


DEFAULT_WEIGHTS: Dict[ParticipantRole, float] = {
    ParticipantRole.RISK_ANALYST:         2.0,
    ParticipantRole.MACRO_ANALYST:        1.8,
    ParticipantRole.TECHNICAL_ANALYST:    1.5,
    ParticipantRole.FUNDAMENTAL_ANALYST:  1.5,
    ParticipantRole.STRATEGY_LEARNING:    1.4,
    ParticipantRole.MARKET_INTELLIGENCE:  1.3,
    ParticipantRole.COMPANY_INTELLIGENCE: 1.2,
    ParticipantRole.PORTFOLIO_ANALYST:    1.2,
    ParticipantRole.EXECUTION_ANALYST:    1.0,
    ParticipantRole.SENTIMENT_ANALYST:    0.8,
    ParticipantRole.CUSTOM:               1.0,
}


@dataclass(frozen=True)
class ParticipantProfile:
    """Immutable profile for a debate participant."""
    participant_id:      str
    role:                ParticipantRole
    display_name:        str
    weight:              float                 # 0–3.0
    expertise_areas:     tuple[str, ...]
    analytical_frameworks: tuple[str, ...]
    bias_flags:          tuple[str, ...]       # known systematic biases
    created_at:          datetime
    version:             str = "1.0"

    def to_dict(self) -> dict:
        return {
            "participant_id":       self.participant_id,
            "role":                 self.role.value,
            "display_name":         self.display_name,
            "weight":               round(self.weight, 4),
            "expertise_areas":      list(self.expertise_areas),
            "analytical_frameworks": list(self.analytical_frameworks),
            "bias_flags":           list(self.bias_flags),
            "created_at":           self.created_at.isoformat(),
            "version":              self.version,
        }


def build_profile(
    role:                  ParticipantRole,
    participant_id:        Optional[str]    = None,
    display_name:          Optional[str]    = None,
    weight:                Optional[float]  = None,
    expertise_areas:       Optional[List[str]] = None,
    analytical_frameworks: Optional[List[str]] = None,
    bias_flags:            Optional[List[str]] = None,
    version:               str              = "1.0",
) -> ParticipantProfile:
    return ParticipantProfile(
        participant_id=participant_id or str(uuid.uuid4()),
        role=role,
        display_name=display_name or role.display_name,
        weight=weight if weight is not None else DEFAULT_WEIGHTS.get(role, 1.0),
        expertise_areas=tuple(expertise_areas or _DEFAULT_EXPERTISE.get(role, [])),
        analytical_frameworks=tuple(analytical_frameworks or _DEFAULT_FRAMEWORKS.get(role, [])),
        bias_flags=tuple(bias_flags or _DEFAULT_BIASES.get(role, [])),
        created_at=datetime.now(timezone.utc),
        version=version,
    )


_DEFAULT_EXPERTISE: Dict[ParticipantRole, List[str]] = {
    ParticipantRole.TECHNICAL_ANALYST:    ["chart_patterns", "rsi", "moving_averages", "volume_analysis"],
    ParticipantRole.FUNDAMENTAL_ANALYST:  ["eps", "pe_ratio", "debt_equity", "free_cash_flow"],
    ParticipantRole.MARKET_INTELLIGENCE:  ["market_regime", "sector_rotation", "liquidity"],
    ParticipantRole.COMPANY_INTELLIGENCE: ["company_fundamentals", "management", "competitive_moat"],
    ParticipantRole.MACRO_ANALYST:        ["interest_rates", "gdp", "inflation", "currency"],
    ParticipantRole.RISK_ANALYST:         ["var", "drawdown", "volatility", "tail_risk"],
    ParticipantRole.PORTFOLIO_ANALYST:    ["correlation", "diversification", "position_sizing"],
    ParticipantRole.EXECUTION_ANALYST:    ["liquidity", "spread", "market_impact", "slippage"],
    ParticipantRole.SENTIMENT_ANALYST:    ["news_sentiment", "social_sentiment", "insider_activity"],
    ParticipantRole.STRATEGY_LEARNING:    ["historical_performance", "regime_transitions", "win_rate"],
}

_DEFAULT_FRAMEWORKS: Dict[ParticipantRole, List[str]] = {
    ParticipantRole.TECHNICAL_ANALYST:    ["price_action", "trend_following"],
    ParticipantRole.FUNDAMENTAL_ANALYST:  ["dcf", "comparable_analysis"],
    ParticipantRole.MARKET_INTELLIGENCE:  ["regime_classification", "breadth_analysis"],
    ParticipantRole.COMPANY_INTELLIGENCE: ["porter_five_forces", "swot"],
    ParticipantRole.MACRO_ANALYST:        ["macro_factor_model", "taylor_rule"],
    ParticipantRole.RISK_ANALYST:         ["var_cvar", "monte_carlo", "stress_test"],
    ParticipantRole.PORTFOLIO_ANALYST:    ["mean_variance", "risk_parity"],
    ParticipantRole.EXECUTION_ANALYST:    ["market_microstructure", "vwap"],
    ParticipantRole.SENTIMENT_ANALYST:    ["contrarian_analysis", "sentiment_index"],
    ParticipantRole.STRATEGY_LEARNING:    ["reinforcement_learning", "walk_forward_test"],
}

_DEFAULT_BIASES: Dict[ParticipantRole, List[str]] = {
    ParticipantRole.TECHNICAL_ANALYST:    ["recency_bias", "pattern_overfit"],
    ParticipantRole.FUNDAMENTAL_ANALYST:  ["anchoring_to_fair_value"],
    ParticipantRole.MACRO_ANALYST:        ["macro_overemphasis"],
    ParticipantRole.RISK_ANALYST:         ["risk_aversion_excess"],
    ParticipantRole.SENTIMENT_ANALYST:    ["contrarian_over_reaction"],
    ParticipantRole.STRATEGY_LEARNING:    ["survivorship_bias"],
}
