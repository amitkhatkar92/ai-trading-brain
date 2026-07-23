"""
platform_health_engine.py — iios.supervisor.governance
--------------------------------------------------------
Platform health assessment engine.

Reads all subsystem snapshots from the governance context and produces
a PlatformHealthReport.  Stateless — safe to call from multiple threads.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .constants import (
    DOMAIN_SNAPSHOT_KEY,
    HEALTH_CRITICAL_THRESHOLD,
    HEALTH_DEGRADED_THRESHOLD,
    HEALTH_NORMAL_THRESHOLD,
    HEALTH_OPTIMAL_THRESHOLD,
    SupervisionDomain,
    SubsystemStatus,
)
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_response import (
    PlatformHealthReport,
    SubsystemHealth,
)


class PlatformHealthEngine:
    """
    Stateless platform health assessment engine.

    For each supervised domain it reads the corresponding snapshot from the
    context, scores it, assigns a SubsystemStatus, and aggregates the results
    into a PlatformHealthReport.
    """

    def assess(self, context: AutonomousGovernanceContext) -> PlatformHealthReport:
        """
        Assess platform health from all available subsystem snapshots.

        Parameters
        ----------
        context : AutonomousGovernanceContext
            Full enterprise context for this governance cycle.

        Returns
        -------
        PlatformHealthReport
        """
        health_list: List[SubsystemHealth] = []
        for domain in SupervisionDomain:
            if domain == SupervisionDomain.ENTERPRISE:
                continue
            snap_key = DOMAIN_SNAPSHOT_KEY.get(domain.value, "")
            snapshot = getattr(context, snap_key.replace(".", "_"), None) if snap_key else None
            if snapshot is None:
                snapshot = context.inputs.get(snap_key, {})
            health_list.append(self._score_subsystem(domain.value, snapshot or {}))

        # Also score platform overall using platform_health dict
        if context.platform_health:
            ph = context.platform_health
            overall_from_ph = float(ph.get("overall", ph.get("score", 1.0)))
            status, score = self._classify(overall_from_ph)
            for i, h in enumerate(health_list):
                if h.subsystem_id == SupervisionDomain.PLATFORM_INFRASTRUCTURE.value:
                    health_list[i] = SubsystemHealth(
                        subsystem_id = h.subsystem_id,
                        status       = status,
                        health_score = score,
                        issues       = h.issues,
                        last_updated = h.last_updated,
                    )
                    break

        return PlatformHealthReport.create(tuple(health_list))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_subsystem(self, subsystem_id: str, snapshot: dict) -> SubsystemHealth:
        """Derive a health score and status from a snapshot dict."""
        if not snapshot:
            return SubsystemHealth(
                subsystem_id = subsystem_id,
                status       = SubsystemStatus.UNKNOWN,
                health_score = 0.5,
                issues       = ("snapshot_missing",),
            )

        # Check common health / status fields in the snapshot.
        raw_score: float = 1.0
        issues: List[str] = []

        # Try common score keys.
        for key in ("health_score", "health", "score", "availability"):
            val = snapshot.get(key)
            if isinstance(val, (int, float)):
                raw_score = float(val)
                break
        else:
            # No explicit health score; estimate from status / error keys.
            status_val = snapshot.get("status", "")
            if isinstance(status_val, str):
                if status_val in ("critical", "error", "failed"):
                    raw_score = 0.2
                    issues.append(f"status={status_val}")
                elif status_val in ("degraded", "warning", "impaired"):
                    raw_score = 0.6
                    issues.append(f"status={status_val}")
            error_count = snapshot.get("error_count", snapshot.get("errors", 0))
            if isinstance(error_count, (int, float)) and error_count > 0:
                raw_score = min(raw_score, max(0.3, 1.0 - float(error_count) * 0.1))
                issues.append(f"error_count={error_count}")

        # Clamp to [0, 1].
        raw_score = max(0.0, min(1.0, raw_score))
        status, score = self._classify(raw_score)
        return SubsystemHealth(
            subsystem_id = subsystem_id,
            status       = status,
            health_score = score,
            issues       = tuple(issues),
        )

    @staticmethod
    def _classify(score: float):
        if score >= HEALTH_OPTIMAL_THRESHOLD:
            return SubsystemStatus.HEALTHY, score
        if score >= HEALTH_NORMAL_THRESHOLD:
            return SubsystemStatus.DEGRADED, score
        if score >= HEALTH_DEGRADED_THRESHOLD:
            return SubsystemStatus.IMPAIRED, score
        if score > 0.0:
            return SubsystemStatus.CRITICAL, score
        return SubsystemStatus.UNKNOWN, score
