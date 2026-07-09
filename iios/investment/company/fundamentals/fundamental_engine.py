"""iios/investment/company/fundamentals/fundamental_engine.py
Coordinates valuation, ownership, governance, and corporate actions engines.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.fundamentals.valuation_engine import (
    ValuationAnalysis,
    ValuationEngine,
)
from iios.investment.company.fundamentals.ownership_engine import (
    OwnershipAnalysis,
    OwnershipEngine,
)
from iios.investment.company.fundamentals.governance_engine import (
    GovernanceAnalysis,
    GovernanceEngine,
)
from iios.investment.company.fundamentals.corporate_action_engine import (
    CorporateActionsAnalysis,
    CorporateActionEngine,
)


@dataclass
class FundamentalAnalysis:
    """Composite fundamental analysis."""

    valuation:         ValuationAnalysis      = field(default_factory=ValuationAnalysis)
    ownership:         OwnershipAnalysis       = field(default_factory=OwnershipAnalysis)
    governance:        GovernanceAnalysis      = field(default_factory=GovernanceAnalysis)
    corporate_actions: CorporateActionsAnalysis = field(default_factory=CorporateActionsAnalysis)
    attractiveness_score: float               = 50.0    # 0–100 higher = more attractive
    risk_score:           float               = 50.0    # 0–100 higher = more risky
    metadata:             dict[str, Any]      = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valuation":            self.valuation.to_dict(),
            "ownership":            self.ownership.to_dict(),
            "governance":           self.governance.to_dict(),
            "corporate_actions":    self.corporate_actions.to_dict(),
            "attractiveness_score": self.attractiveness_score,
            "risk_score":           self.risk_score,
            "metadata":             self.metadata,
        }


class FundamentalEngine:
    """
    Orchestrates all fundamental sub-engines.

    Inputs (all optional dicts / lists):
      valuation_data, ownership_data, governance_data, corporate_actions_raw
    """

    def __init__(
        self,
        valuation_engine:       ValuationEngine      | None = None,
        ownership_engine:       OwnershipEngine       | None = None,
        governance_engine:      GovernanceEngine      | None = None,
        corporate_action_engine: CorporateActionEngine | None = None,
    ) -> None:
        self._lock             = threading.RLock()
        self._valuation        = valuation_engine        or ValuationEngine()
        self._ownership        = ownership_engine        or OwnershipEngine()
        self._governance       = governance_engine       or GovernanceEngine()
        self._corp_actions     = corporate_action_engine or CorporateActionEngine()

    def analyze(
        self,
        company_id:            str,
        valuation_data:        dict[str, Any]       = {},    # noqa: B006
        ownership_data:        dict[str, Any]       = {},    # noqa: B006
        governance_data:       dict[str, Any]       = {},    # noqa: B006
        corporate_actions_raw: list[dict[str, Any]] = [],   # noqa: B006
    ) -> FundamentalAnalysis:
        valuation       = self._valuation.analyze(valuation_data)
        ownership       = self._ownership.analyze(ownership_data)
        governance      = self._governance.analyze(governance_data)
        corp_actions    = self._corp_actions.analyze(company_id, corporate_actions_raw)

        attractiveness  = self._attractiveness(valuation, ownership, governance)
        risk            = self._risk(ownership, governance)

        return FundamentalAnalysis(
            valuation            = valuation,
            ownership            = ownership,
            governance           = governance,
            corporate_actions    = corp_actions,
            attractiveness_score = round(attractiveness, 2),
            risk_score           = round(risk, 2),
            metadata             = {"company_id": company_id},
        )

    @staticmethod
    def _attractiveness(
        val: ValuationAnalysis,
        own: OwnershipAnalysis,
        gov: GovernanceAnalysis,
    ) -> float:
        # Higher valuation_score = cheaper = more attractive
        return (
            val.valuation_score  * 0.50
            + own.ownership_score  * 0.30
            + gov.governance_score * 0.20
        )

    @staticmethod
    def _risk(
        own: OwnershipAnalysis,
        gov: GovernanceAnalysis,
    ) -> float:
        # Invert ownership_score and governance_score (lower score = higher risk)
        own_risk = 100 - own.ownership_score
        gov_risk = 100 - gov.governance_score
        return own_risk * 0.50 + gov_risk * 0.50
