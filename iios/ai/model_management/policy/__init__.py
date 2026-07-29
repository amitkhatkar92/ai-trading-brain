"""
iios.ai.model_management.policy
==================================
M3 Policy Framework for A2 Model Management.
"""
from __future__ import annotations

from .policies import (
    AllowAllCostPolicy,
    CapabilityBasedSelectionPolicy,
    CapabilityPolicy,
    CostPolicy,
    FailoverPolicy,
    FixedPreferredModelPolicy,
    LatencyPolicy,
    ModelValidationPolicy,
    NoFailoverPolicy,
    NoPreferencePolicy,
    PermissiveCapabilityPolicy,
    PermissiveLatencyPolicy,
    PermissiveModelValidationPolicy,
    PreferredModelPolicy,
    SelectionPolicy,
    SimpleFailoverPolicy,
    StrictCapabilityPolicy,
    StrictModelValidationPolicy,
    TierBudgetCostPolicy,
)

__all__ = [
    "SelectionPolicy",
    "CapabilityBasedSelectionPolicy",
    "FailoverPolicy",
    "SimpleFailoverPolicy",
    "NoFailoverPolicy",
    "CostPolicy",
    "AllowAllCostPolicy",
    "TierBudgetCostPolicy",
    "LatencyPolicy",
    "PermissiveLatencyPolicy",
    "PreferredModelPolicy",
    "NoPreferencePolicy",
    "FixedPreferredModelPolicy",
    "CapabilityPolicy",
    "StrictCapabilityPolicy",
    "PermissiveCapabilityPolicy",
    "ModelValidationPolicy",
    "StrictModelValidationPolicy",
    "PermissiveModelValidationPolicy",
]
