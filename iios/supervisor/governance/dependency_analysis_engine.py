"""
dependency_analysis_engine.py — iios.supervisor.governance
-----------------------------------------------------------
Subsystem dependency graph analysis engine.

Builds the enterprise dependency graph from the static PLATFORM_DEPENDENCIES
map and the available snapshot data, then identifies critical paths and
isolated subsystems.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .constants import (
    DOMAIN_SNAPSHOT_KEY,
    PLATFORM_DEPENDENCIES,
    DependencyType,
    SupervisionDomain,
)
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_response import (
    DependencyReport,
    SubsystemDependency,
    SubsystemHealth,
    PlatformHealthReport,
)


class DependencyAnalysisEngine:
    """
    Stateless subsystem dependency analysis engine.

    Derives the enterprise dependency graph from the static platform topology
    defined in :data:`PLATFORM_DEPENDENCIES`.
    """

    def analyze(
        self,
        context: AutonomousGovernanceContext,
        platform_health: PlatformHealthReport,
    ) -> DependencyReport:
        """
        Analyze subsystem dependencies and identify critical paths.

        Parameters
        ----------
        context : AutonomousGovernanceContext
        platform_health : PlatformHealthReport

        Returns
        -------
        DependencyReport
        """
        all_domains = [d.value for d in SupervisionDomain if d != SupervisionDomain.ENTERPRISE]
        dependencies: List[SubsystemDependency] = []

        for from_domain, dep_list in PLATFORM_DEPENDENCIES.items():
            if from_domain == SupervisionDomain.ENTERPRISE.value:
                continue
            for to_domain in dep_list:
                dependencies.append(SubsystemDependency(
                    from_subsystem  = from_domain,
                    to_subsystem    = to_domain,
                    dependency_type = DependencyType.HARD,
                    is_critical     = True,
                    description     = f"{from_domain} depends on {to_domain}",
                ))

        # Find isolated subsystems (no incoming or outgoing hard deps).
        with_outgoing: Set[str] = {d.from_subsystem for d in dependencies}
        with_incoming: Set[str] = {d.to_subsystem for d in dependencies}
        isolated = tuple(
            s for s in all_domains
            if s not in with_outgoing and s not in with_incoming
        )

        critical_paths = self._find_critical_paths(all_domains, dependencies)

        return DependencyReport.create(
            tuple(dependencies),
            tuple(all_domains),
            critical_paths        = critical_paths,
            isolated_subsystems   = isolated,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_critical_paths(
        self,
        domains:      List[str],
        dependencies: List[SubsystemDependency],
    ) -> Tuple[Tuple[str, ...], ...]:
        """Identify the longest dependency chains (critical paths)."""
        # Build adjacency list: who depends on whom.
        adjacency: Dict[str, List[str]] = {d: [] for d in domains}
        for dep in dependencies:
            if dep.is_critical:
                adjacency[dep.from_subsystem].append(dep.to_subsystem)

        paths: List[Tuple[str, ...]] = []
        for start in domains:
            if not adjacency[start]:
                continue
            path = self._longest_path_from(start, adjacency, set())
            if len(path) >= 2:
                paths.append(tuple(path))

        # Return unique paths sorted by length descending.
        seen: Set[Tuple[str, ...]] = set()
        result: List[Tuple[str, ...]] = []
        for p in sorted(paths, key=len, reverse=True):
            if p not in seen:
                seen.add(p)
                result.append(p)
        return tuple(result[:10])  # cap at 10 paths

    def _longest_path_from(
        self,
        node:      str,
        adjacency: Dict[str, List[str]],
        visited:   Set[str],
    ) -> List[str]:
        """Depth-first traversal to find the longest path from *node*."""
        if node in visited:
            return [node]
        visited = visited | {node}
        if not adjacency.get(node):
            return [node]
        best: List[str] = [node]
        for neighbour in adjacency[node]:
            sub = self._longest_path_from(neighbour, adjacency, visited)
            candidate = [node] + sub
            if len(candidate) > len(best):
                best = candidate
        return best
