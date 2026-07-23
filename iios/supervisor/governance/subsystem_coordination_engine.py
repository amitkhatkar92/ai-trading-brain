"""
subsystem_coordination_engine.py — iios.supervisor.governance
--------------------------------------------------------------
Cross-subsystem coordination analysis engine.

Analyses whether supervised subsystems are coordinating correctly by
inspecting dependency health and snapshot availability.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .constants import SubsystemStatus, SupervisionDomain
from .autonomous_governance_response import (
    DependencyReport,
    PlatformHealthReport,
    SubsystemHealth,
)


class SubsystemCoordinationEngine:
    """
    Stateless cross-subsystem coordination analysis engine.

    Identifies coordination failures: cases where a subsystem is healthy
    but one of its hard dependencies is impaired or critical.
    """

    def analyze(
        self,
        platform_health:   PlatformHealthReport,
        dependency_report: DependencyReport,
    ) -> Dict[str, any]:
        """
        Analyse cross-subsystem coordination.

        Parameters
        ----------
        platform_health : PlatformHealthReport
        dependency_report : DependencyReport

        Returns
        -------
        Dict with keys:
          - coordination_failures : List[str]
          - coordination_score    : float (0–1)
          - blocked_subsystems    : List[str]
          - healthy_chains        : int
        """
        health_map: Dict[str, SubsystemHealth] = {
            h.subsystem_id: h for h in platform_health.subsystem_health
        }

        failures: List[str] = []
        blocked:  List[str] = []

        for dep in dependency_report.dependencies:
            if not dep.is_critical:
                continue
            downstream_health = health_map.get(dep.from_subsystem)
            upstream_health   = health_map.get(dep.to_subsystem)
            if upstream_health and upstream_health.status in (
                SubsystemStatus.CRITICAL, SubsystemStatus.IMPAIRED
            ):
                msg = (
                    f"{dep.from_subsystem} depends on {dep.to_subsystem} "
                    f"which is {upstream_health.status.value.upper()}"
                )
                failures.append(msg)
                if dep.from_subsystem not in blocked:
                    blocked.append(dep.from_subsystem)

        total_deps  = len(dependency_report.dependencies)
        failed_deps = len(failures)
        score       = 1.0 - (failed_deps / total_deps) if total_deps else 1.0
        healthy_chains = max(0, total_deps - failed_deps)

        return {
            "coordination_failures": failures,
            "coordination_score":    round(score, 4),
            "blocked_subsystems":    blocked,
            "healthy_chains":        healthy_chains,
        }
