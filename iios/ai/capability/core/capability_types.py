"""
capability_types.py -- iios.ai.capability.core
================================================
Enumerations for capability types and statuses.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

from enum import Enum


class CapabilityType(str, Enum):
    """High-level kind of capability."""
    TOOL                  = "tool"
    SKILL                 = "skill"
    CONNECTOR             = "connector"
    KNOWLEDGE_SOURCE      = "knowledge_source"
    EXECUTION_ENVIRONMENT = "execution_environment"
    WORKFLOW_ACTION       = "workflow_action"
    CUSTOM                = "custom"


class CapabilityCategory(str, Enum):
    """Domain category for capability discovery."""
    DATA          = "data"
    COMPUTATION   = "computation"
    COMMUNICATION = "communication"
    STORAGE       = "storage"
    ANALYSIS      = "analysis"
    GENERATION    = "generation"
    INTEGRATION   = "integration"
    WORKFLOW      = "workflow"
    CUSTOM        = "custom"


class CapabilityStatus(str, Enum):
    """Lifecycle status of a registered capability."""
    PENDING    = "pending"
    ACTIVE     = "active"
    DISABLED   = "disabled"
    DEPRECATED = "deprecated"
    REMOVED    = "removed"

    def is_executable(self) -> bool:
        """Return True only for ACTIVE capabilities."""
        return self == CapabilityStatus.ACTIVE
