"""iios/investment/decision/core/decision_configuration.py
DecisionConfiguration — policy-driven configuration for one decision run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.decision.core.decision_constants import (
    DEFAULT_APPROVAL_THRESHOLD,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_EVIDENCE_TIMEOUT_SECS,
    DEFAULT_RISK_THRESHOLD,
    MAX_DECISION_AGE_SECS,
    EnvironmentProfile,
)


@dataclass(frozen=True)
class DecisionConfiguration:
    """
    Immutable configuration snapshot injected into a decision at creation time.
    Controls thresholds, policies, and behaviour for a single decision execution.
    """
    approval_threshold:       float               = DEFAULT_APPROVAL_THRESHOLD
    confidence_threshold:     float               = DEFAULT_CONFIDENCE_THRESHOLD
    risk_threshold:           float               = DEFAULT_RISK_THRESHOLD
    evidence_timeout_seconds: float               = DEFAULT_EVIDENCE_TIMEOUT_SECS
    max_age_seconds:          float               = MAX_DECISION_AGE_SECS
    auto_approve:             bool                = False
    publish_on_approval:      bool                = True
    auto_archive_on_publish:  bool                = False
    environment:              EnvironmentProfile  = EnvironmentProfile.DEVELOPMENT
    policies:                 Dict[str, Any]      = field(default_factory=dict)
    override_allowed:         bool                = True
    require_explanation:      bool                = True

    def with_environment(self, env: EnvironmentProfile) -> "DecisionConfiguration":
        """Return a new configuration with the environment overridden."""
        return DecisionConfiguration(
            approval_threshold=self.approval_threshold,
            confidence_threshold=self.confidence_threshold,
            risk_threshold=self.risk_threshold,
            evidence_timeout_seconds=self.evidence_timeout_seconds,
            max_age_seconds=self.max_age_seconds,
            auto_approve=self.auto_approve and not env.requires_approval,
            publish_on_approval=self.publish_on_approval,
            auto_archive_on_publish=self.auto_archive_on_publish,
            environment=env,
            policies=self.policies,
            override_allowed=self.override_allowed,
            require_explanation=self.require_explanation,
        )

    def with_policy(self, key: str, value: Any) -> "DecisionConfiguration":
        return DecisionConfiguration(
            approval_threshold=self.approval_threshold,
            confidence_threshold=self.confidence_threshold,
            risk_threshold=self.risk_threshold,
            evidence_timeout_seconds=self.evidence_timeout_seconds,
            max_age_seconds=self.max_age_seconds,
            auto_approve=self.auto_approve,
            publish_on_approval=self.publish_on_approval,
            auto_archive_on_publish=self.auto_archive_on_publish,
            environment=self.environment,
            policies={**self.policies, key: value},
            override_allowed=self.override_allowed,
            require_explanation=self.require_explanation,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_threshold":       self.approval_threshold,
            "confidence_threshold":     self.confidence_threshold,
            "risk_threshold":           self.risk_threshold,
            "evidence_timeout_seconds": self.evidence_timeout_seconds,
            "max_age_seconds":          self.max_age_seconds,
            "auto_approve":             self.auto_approve,
            "publish_on_approval":      self.publish_on_approval,
            "auto_archive_on_publish":  self.auto_archive_on_publish,
            "environment":              self.environment.value,
            "policies":                 self.policies,
            "override_allowed":         self.override_allowed,
            "require_explanation":      self.require_explanation,
        }


# Sensible pre-built configurations per environment
DEVELOPMENT_CONFIG = DecisionConfiguration(environment=EnvironmentProfile.DEVELOPMENT, auto_approve=True)
PAPER_CONFIG       = DecisionConfiguration(environment=EnvironmentProfile.PAPER,       auto_approve=False)
LIVE_CONFIG        = DecisionConfiguration(environment=EnvironmentProfile.LIVE,        auto_approve=False, require_explanation=True)
BACKTEST_CONFIG    = DecisionConfiguration(environment=EnvironmentProfile.BACKTEST,    auto_approve=True)
