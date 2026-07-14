"""iios/investment/portfolio/diversification/correlation_engine.py

Orchestrates correlation matrix, analysis, dependency, and relationship-graph
into a single CorrelationReport.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.diversification.correlation_analysis import (
    CorrelationAnalysisResult,
    analyze_correlations,
)
from iios.investment.portfolio.diversification.correlation_matrix import (
    CorrelationMatrix,
    build_correlation_matrix,
)
from iios.investment.portfolio.diversification.dependency_analysis import (
    DependencyAnalysisResult,
    analyze_dependencies,
)
from iios.investment.portfolio.diversification.diversification_types import (
    AVG_CORR_CRITICAL,
    AVG_CORR_WARNING,
    PositionData,
)
from iios.investment.portfolio.diversification.overlap_analysis import (
    OverlapResult,
    analyze_overlap,
)
from iios.investment.portfolio.diversification.relationship_graph import (
    RelationshipGraph,
    build_relationship_graph,
)


@dataclass(frozen=True)
class CorrelationReport:
    """Full correlation intelligence for one portfolio evaluation."""

    report_id:    str                     = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str                     = ""
    plan_id:      str                     = ""

    matrix:       CorrelationMatrix       = field(default_factory=CorrelationMatrix)
    analysis:     CorrelationAnalysisResult = field(default_factory=CorrelationAnalysisResult)
    dependency:   DependencyAnalysisResult = field(default_factory=DependencyAnalysisResult)
    overlap:      OverlapResult           = field(default_factory=OverlapResult)
    graph:        RelationshipGraph       = field(default_factory=RelationshipGraph)

    is_high_correlation: bool = False
    warnings:     tuple       = field(default_factory=tuple)
    evaluated_at: float       = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "portfolio_id":        self.portfolio_id,
            "plan_id":             self.plan_id,
            "analysis":            self.analysis.to_dict(),
            "dependency":          self.dependency.to_dict(),
            "overlap":             self.overlap.to_dict(),
            "graph_summary":       self.graph.to_dict(),
            "is_high_correlation": self.is_high_correlation,
            "warnings":            list(self.warnings),
            "evaluated_at":        self.evaluated_at,
        }


class CorrelationEngine:
    """Computes a full CorrelationReport from a list of PositionData."""

    def __init__(self, graph_threshold: float = 0.55) -> None:
        self._graph_threshold = graph_threshold

    def evaluate(
        self,
        positions:    List[PositionData],
        portfolio_id: str = "",
        plan_id:      str = "",
    ) -> CorrelationReport:
        if not positions:
            return CorrelationReport(portfolio_id=portfolio_id, plan_id=plan_id)

        matrix     = build_correlation_matrix(positions)
        analysis   = analyze_correlations(positions, matrix)
        dependency = analyze_dependencies(positions)
        overlap    = analyze_overlap(positions)
        graph      = build_relationship_graph(positions, matrix, self._graph_threshold)

        high_corr = analysis.avg_correlation >= AVG_CORR_WARNING

        warnings = []
        if analysis.avg_correlation >= AVG_CORR_CRITICAL:
            warnings.append(
                f"Critical average correlation {analysis.avg_correlation:.2f} "
                f"— portfolio lacks diversification benefit"
            )
        elif analysis.avg_correlation >= AVG_CORR_WARNING:
            warnings.append(
                f"High average correlation {analysis.avg_correlation:.2f}"
            )
        if analysis.n_extreme_pairs > 0:
            warnings.append(
                f"{analysis.n_extreme_pairs} pairs have extreme correlation (≥ 0.80)"
            )
        if dependency.hidden_dependency_count > 0:
            warnings.append(
                f"{dependency.hidden_dependency_count} hidden cross-sector industry dependencies"
            )

        return CorrelationReport(
            portfolio_id       = portfolio_id,
            plan_id            = plan_id,
            matrix             = matrix,
            analysis           = analysis,
            dependency         = dependency,
            overlap            = overlap,
            graph              = graph,
            is_high_correlation= high_corr,
            warnings           = tuple(warnings),
        )
