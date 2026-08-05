"""
kde_engine.py — Top-level Knowledge Discovery Engine.

Orchestrates all schemes, scoring, relationship mining, clustering, and reporting.
Never writes to the live IDR.  Only proposes discoveries.
"""
from __future__ import annotations

import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .kde_config       import KDEConfig
from .kde_models       import (
    Discovery, DiscoveryCandidate, DiscoveryStatistics, KDERunResult, KDEStatus,
)
from .scheme_base      import BaseDiscoveryScheme, DiscoveryContext
from .discovery_scorer import DiscoveryScorer
from .relationship_miner import RelationshipMiner
from .cluster_builder  import ClusterBuilder
from .report_generator import KDEReportGenerator

log = logging.getLogger(__name__)


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("KDE-%Y%m%d-%H%M%S")


class KDEEngine:
    """
    Knowledge Discovery Engine.

    Usage:
        engine = KDEEngine(config)
        result = engine.run(hkap_packages, dna_records, edge_records)

    New discovery schemes are added by calling engine.register_scheme(MyScheme())
    — no engine modification required.
    """

    def __init__(self, config: Optional[KDEConfig] = None) -> None:
        self._config     = config or KDEConfig()
        self._registry:  Dict[str, BaseDiscoveryScheme] = {}
        self._run_history: List[KDERunResult] = []
        self._register_defaults()

    # ── public API ────────────────────────────────────────────────────────

    def register_scheme(self, scheme: BaseDiscoveryScheme) -> None:
        """Register an additional discovery scheme.  Idempotent."""
        self._registry[scheme.SCHEME_ID] = scheme
        log.info("[KDE] registered scheme %s: %s", scheme.SCHEME_ID, scheme.SCHEME_NAME)

    def deregister_scheme(self, scheme_id: str) -> None:
        self._registry.pop(scheme_id, None)

    def run(
        self,
        hkap_packages: Dict[int, Any],
        dna_records:   Optional[List[Any]] = None,
        edge_records:  Optional[List[Any]] = None,
    ) -> KDERunResult:
        """
        Execute all enabled schemes, score, relate, cluster, and report.

        Args:
            hkap_packages: {year: YearKnowledgePackage} from HKAP-001
            dna_records:   [CrossYearDNARecord] from CrossYearAnalyzer
            edge_records:  [CrossYearEdgeRecord] from CrossYearAnalyzer

        Returns:
            KDERunResult with all discoveries, relationships, clusters, and reports.
        """
        ctx = DiscoveryContext(
            hkap_packages = hkap_packages,
            dna_records   = dna_records or [],
            edge_records  = edge_records or [],
            config        = self._config,
        )

        enabled = [
            s for sid, s in self._registry.items()
            if sid in self._config.enabled_schemes
        ]
        log.info("[KDE] run start: %d schemes enabled on %d years",
                 len(enabled), len(hkap_packages))

        all_candidates = self._run_schemes(enabled, ctx)

        scorer      = DiscoveryScorer()
        discoveries = scorer.score_and_promote(all_candidates, self._config)

        miner         = RelationshipMiner()
        relationships = miner.mine(discoveries)

        builder  = ClusterBuilder()
        clusters = builder.build(discoveries)

        stats = self._compute_statistics(all_candidates, discoveries, relationships, clusters)

        reporter = KDEReportGenerator(self._config)
        reports  = reporter.generate(discoveries, relationships, clusters, stats)

        result = KDERunResult(
            run_id        = _run_id(),
            discoveries   = discoveries,
            relationships = relationships,
            clusters      = clusters,
            statistics    = stats,
            reports       = reports,
            schemes_run   = [s.SCHEME_ID for s in enabled],
            generated_at  = datetime.now(timezone.utc).isoformat(),
        )
        self._run_history.append(result)
        log.info(
            "[KDE] run complete: %d discoveries, %d relationships, %d clusters",
            len(discoveries), len(relationships), len(clusters),
        )
        return result

    def status(self) -> KDEStatus:
        total_disc = sum(len(r.discoveries) for r in self._run_history)
        last_run   = self._run_history[-1] if self._run_history else None
        return KDEStatus(
            total_runs         = len(self._run_history),
            last_run_id        = last_run.run_id if last_run else None,
            total_discoveries  = total_disc,
            schemes_registered = len(self._registry),
            schemes_enabled    = len(self._config.enabled_schemes),
            last_run_at        = last_run.generated_at if last_run else None,
        )

    def last_result(self) -> Optional[KDERunResult]:
        return self._run_history[-1] if self._run_history else None

    def history(self) -> List[KDERunResult]:
        return list(self._run_history)

    # ── internal ──────────────────────────────────────────────────────────

    def _run_schemes(
        self,
        schemes: List[BaseDiscoveryScheme],
        ctx:     DiscoveryContext,
    ) -> List[DiscoveryCandidate]:
        all_candidates: List[DiscoveryCandidate] = []

        if self._config.parallel_schemes and len(schemes) > 1:
            with ThreadPoolExecutor(max_workers=self._config.max_workers) as ex:
                futures = {ex.submit(s.run, ctx): s for s in schemes}
                for future in as_completed(futures):
                    scheme = futures[future]
                    try:
                        all_candidates.extend(future.result())
                    except Exception as exc:
                        log.warning("[KDE] scheme %s async error: %s",
                                    scheme.SCHEME_ID, exc)
        else:
            for scheme in schemes:
                candidates = scheme.run(ctx)
                all_candidates.extend(candidates)

        return all_candidates

    def _compute_statistics(
        self,
        candidates:    List[DiscoveryCandidate],
        discoveries:   List[Discovery],
        relationships: list,
        clusters:      list,
    ) -> DiscoveryStatistics:
        by_scheme: Dict[str, int] = {}
        by_regime: Dict[str, int] = {}
        high_value = 0

        for d in discoveries:
            by_scheme[d.scheme_id] = by_scheme.get(d.scheme_id, 0) + 1
            for r in d.regimes_observed:
                by_regime[r] = by_regime.get(r, 0) + 1
            if d.potential_value in ("HIGH", "VERY_HIGH"):
                high_value += 1

        avg_score = statistics.mean(d.score.overall for d in discoveries) if discoveries else 0.0
        avg_nov   = statistics.mean(d.score.novelty for d in discoveries) if discoveries else 0.0
        avg_conf  = statistics.mean(d.score.scientific_confidence for d in discoveries) if discoveries else 0.0

        return DiscoveryStatistics(
            total_candidates      = len(candidates),
            total_discoveries     = len(discoveries),
            discoveries_by_scheme = by_scheme,
            discoveries_by_regime = by_regime,
            avg_score             = round(avg_score, 4),
            avg_novelty           = round(avg_nov, 4),
            avg_confidence        = round(avg_conf, 4),
            high_value_count      = high_value,
            relationship_count    = len(relationships),
            cluster_count         = len(clusters),
            generated_at          = datetime.now(timezone.utc).isoformat(),
        )

    def _register_defaults(self) -> None:
        from .schemes import ALL_SCHEMES
        for scheme_cls in ALL_SCHEMES:
            scheme = scheme_cls()
            self._registry[scheme.SCHEME_ID] = scheme
        log.debug("[KDE] registered %d default schemes", len(self._registry))
