"""
risk_assessment_context.py — iios.risk.assessment
===================================================
Operational context for a risk assessment run.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Tuple

from .constants import (
    AssessmentCapability,
    AssessmentDomain,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_VAR_HORIZON_DAYS,
    OptimizationObjective,
    VERSION,
)


@dataclass(frozen=True)
class RiskAssessmentContext:
    """
    Immutable operational context for a single risk assessment run.

    Carries the configuration parameters that govern which calculations are
    performed, at what confidence levels, and with which objectives.

    Fields
    ------
    context_id :          Unique identifier for this context.
    assessment_id :       Links context to the parent assessment.
    portfolio_id :        Target portfolio.
    risk_id :             Originating risk workflow identifier.
    domains :             Set of risk domains to assess.
    capabilities :        Set of assessment capabilities to execute.
    objectives :          Optimization objectives to pursue.
    confidence_level :    VaR/ES confidence level.
    var_horizon_days :    VaR horizon in trading days.
    lookback_days :       Historical lookback period.
    created_at :          Wall-clock creation time.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    context_id:        str
    assessment_id:     str
    portfolio_id:      str
    risk_id:           str
    domains:           FrozenSet[AssessmentDomain]
    capabilities:      FrozenSet[AssessmentCapability]
    objectives:        FrozenSet[OptimizationObjective]
    confidence_level:  float = DEFAULT_CONFIDENCE_LEVEL
    var_horizon_days:  int   = DEFAULT_VAR_HORIZON_DAYS
    lookback_days:     int   = DEFAULT_LOOKBACK_DAYS
    created_at:        float = field(default_factory=time.time)
    metadata:          Dict[str, Any] = field(default_factory=dict)
    framework_version: str  = VERSION

    @classmethod
    def create(
        cls,
        assessment_id: str,
        portfolio_id:  str,
        risk_id:       str,
        *,
        context_id:       Optional[str]                             = None,
        domains:          Optional[Tuple[AssessmentDomain, ...]]    = None,
        capabilities:     Optional[Tuple[AssessmentCapability, ...]] = None,
        objectives:       Optional[Tuple[OptimizationObjective, ...]] = None,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        var_horizon_days: int   = DEFAULT_VAR_HORIZON_DAYS,
        lookback_days:    int   = DEFAULT_LOOKBACK_DAYS,
        metadata:         Optional[Dict[str, Any]] = None,
    ) -> "RiskAssessmentContext":
        return cls(
            context_id       = context_id or str(uuid.uuid4()),
            assessment_id    = assessment_id,
            portfolio_id     = portfolio_id,
            risk_id          = risk_id,
            domains          = frozenset(domains or AssessmentDomain),
            capabilities     = frozenset(capabilities or AssessmentCapability),
            objectives       = frozenset(objectives or OptimizationObjective),
            confidence_level = confidence_level,
            var_horizon_days = var_horizon_days,
            lookback_days    = lookback_days,
            metadata         = dict(metadata or {}),
        )

    def has_domain(self, domain: AssessmentDomain) -> bool:
        return domain in self.domains

    def has_capability(self, capability: AssessmentCapability) -> bool:
        return capability in self.capabilities

    def has_objective(self, objective: OptimizationObjective) -> bool:
        return objective in self.objectives

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "assessment_id":     self.assessment_id,
            "portfolio_id":      self.portfolio_id,
            "risk_id":           self.risk_id,
            "domains":           [d.value for d in self.domains],
            "capabilities":      [c.value for c in self.capabilities],
            "objectives":        [o.value for o in self.objectives],
            "confidence_level":  self.confidence_level,
            "var_horizon_days":  self.var_horizon_days,
            "lookback_days":     self.lookback_days,
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
