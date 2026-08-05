"""
hkap_engine.py — Top-level orchestrator for HKAP-001.

Enforces:
  - Forward-only knowledge flow (year N can only read years < N)
  - Complete year isolation (each year has its own data directory)
  - No live IDR merge until explicit SD approval
  - Resumable: completed years are skipped on restart (unless force=True)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .hkap_config        import HKAPConfig
from .hkap_models        import (
    FutureDataLeakError,
    HKAPError,
    HKAPStatus,
    HKAPSummary,
    YearKnowledgePackage,
    YearNotCompleteError,
    YearStudyStatus,
)
from .cross_year_analyzer import CrossYearAnalyzer
from .report_generator    import HKAPReportGenerator
from .year_runner         import YearRunner

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HKAPEngine:
    """
    Top-level HKAP-001 orchestrator.

    Usage:
        engine = HKAPEngine(config, ptue)
        summary = engine.run()           # all years + synthesis
        pkg     = engine.run_year(2023)  # single year
        engine.run_synthesis()           # synthesis only (after all years done)
        st      = engine.status()
    """

    def __init__(
        self,
        config: Optional[HKAPConfig] = None,
        ptue:   Optional[Any]        = None,  # PointInTimeUniverseEngine
    ) -> None:
        self._config  = config or HKAPConfig()
        self._ptue    = ptue or self._build_default_ptue()
        self._results: Dict[int, YearKnowledgePackage] = {}
        self._synthesis_done = False
        self._load_persisted_results()

    # ── public API ────────────────────────────────────────────────────────

    def run(
        self,
        years: Optional[List[int]] = None,
        force: bool = False,
    ) -> HKAPSummary:
        """
        Run the full program: all years in chronological order, then synthesis.

        Args:
            years: Override which years to run (must be subset of config.years).
            force: If True, re-run years that are already complete.
        """
        target = sorted(years or self._config.sorted_years)

        # validate years are in config
        invalid = [y for y in target if y not in self._config.years]
        if invalid:
            raise HKAPError(f"Years not in config: {invalid}")

        for year in target:
            if not force and year in self._results and \
               self._results[year].status == YearStudyStatus.COMPLETE.value:
                log.info("[HKAP] year=%d already complete — skipping (use force=True to rerun)", year)
                continue
            try:
                self.run_year(year)
            except Exception as exc:
                log.error("[HKAP] year=%d run failed: %s", year, exc)

        # ── synthesis ─────────────────────────────────────────────────────
        completed = [y for y in target
                     if y in self._results and
                     self._results[y].status == YearStudyStatus.COMPLETE.value]

        synthesis_reports: List[str] = []
        if len(completed) >= 2:
            try:
                synthesis_reports = self.run_synthesis()
                self._synthesis_done = True
            except Exception as exc:
                log.error("[HKAP] synthesis failed: %s", exc)

        return self._build_summary(synthesis_reports)

    def run_year(self, year: int) -> YearKnowledgePackage:
        """
        Run a single year's pipeline with correct forward-only prior context.

        Raises:
            HKAPError: if year not in configured years.
            FutureDataLeakError: impossible to trigger from here (guarded in YearRunner).
        """
        if year not in self._config.years:
            raise HKAPError(f"Year {year} not in configured years: {self._config.years}")

        # ── prior context: only completed years strictly before this year ─
        prior = [
            self._results[y]
            for y in self._config.sorted_years
            if y < year and y in self._results and
               self._results[y].status == YearStudyStatus.COMPLETE.value
        ]

        log.info("[HKAP] run_year=%d prior=%s", year, [p.year for p in prior])

        runner = YearRunner(
            year          = year,
            config        = self._config,
            ptue          = self._ptue,
            prior_context = prior,
        )
        pkg = runner.run()
        self._results[year] = pkg
        self._persist_result(year, pkg)
        return pkg

    def run_synthesis(self) -> List[str]:
        """
        Run cross-year analysis and generate all 8 synthesis reports.

        Requires at least 2 completed years.
        Returns list of generated file paths.
        """
        completed = {
            y: pkg for y, pkg in self._results.items()
            if pkg.status == YearStudyStatus.COMPLETE.value
        }
        if len(completed) < 2:
            raise HKAPError(
                f"Synthesis requires ≥2 completed years. "
                f"Completed: {sorted(completed.keys())}"
            )

        log.info("[HKAP] run_synthesis years=%s", sorted(completed.keys()))

        analyzer = CrossYearAnalyzer()
        dna_records, edge_records = analyzer.analyze(completed)

        gen     = HKAPReportGenerator(self._config)
        summary = self._build_summary([])
        reports = gen.generate_synthesis_reports(
            completed, dna_records, edge_records, summary
        )
        self._synthesis_done = True
        return reports

    def status(self) -> HKAPStatus:
        years_planned   = self._config.sorted_years
        years_completed = sorted(
            y for y, p in self._results.items()
            if p.status == YearStudyStatus.COMPLETE.value
        )
        years_failed    = sorted(
            y for y, p in self._results.items()
            if p.status == YearStudyStatus.FAILED.value
        )
        years_pending   = [
            y for y in years_planned
            if y not in self._results or
               self._results[y].status not in (
                   YearStudyStatus.COMPLETE.value, YearStudyStatus.FAILED.value
               )
        ]
        total_dna = sum(
            p.dna_snapshot.total_discovered
            for p in self._results.values()
            if p.dna_snapshot
        )
        return HKAPStatus(
            years_planned         = years_planned,
            years_completed       = years_completed,
            years_failed          = years_failed,
            years_pending         = years_pending,
            current_year          = None,
            is_synthesis_done     = self._synthesis_done,
            total_dna_accumulated = total_dna,
            last_updated          = _now_iso(),
        )

    def history(self) -> Dict[int, YearKnowledgePackage]:
        """Return all completed year packages (read-only copy)."""
        return dict(self._results)

    def request_live_merge(self) -> None:
        """
        Gate for merging historical knowledge into the live IDR.

        Raises HKAPError: always — merge is not automatic.
        The user must explicitly call ScientificDirector.approve_study() to
        initiate a merge.  This method exists solely to document the gating.
        """
        raise HKAPError(
            "Live IDR merge is not automatic. "
            "Use ScientificDirector.approve_study() with a merge study plan "
            "after reviewing FINAL_INSTITUTIONAL_KNOWLEDGE_RECOMMENDATION.md."
        )

    # ── internal ──────────────────────────────────────────────────────────

    def _build_summary(self, synthesis_reports: List[str]) -> HKAPSummary:
        all_dna    = []
        for pkg in self._results.values():
            if pkg.dna_snapshot:
                all_dna.extend(pkg.dna_snapshot.confidence_by_id.keys())

        completed = [y for y, p in self._results.items()
                     if p.status == YearStudyStatus.COMPLETE.value]
        failed    = [y for y, p in self._results.items()
                     if p.status == YearStudyStatus.FAILED.value]

        return HKAPSummary(
            years_planned           = self._config.sorted_years,
            years_completed         = sorted(completed),
            years_failed            = sorted(failed),
            total_dna_discovered    = len(set(all_dna)),
            stable_dna_count        = 0,   # populated after synthesis
            emerging_dna_count      = 0,
            disappearing_dna_count  = 0,
            stable_edges_count      = 0,
            regime_specific_count   = 0,
            regime_independent_count = 0,
            synthesis_reports       = synthesis_reports,
            generated_at            = _now_iso(),
        )

    def _persist_result(self, year: int, pkg: YearKnowledgePackage) -> None:
        if self._config.dry_run:
            return
        path = Path(self._config.data_root) / str(year) / "year_knowledge_package.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(pkg.to_dict(), f, indent=2)
        except Exception as exc:
            log.warning("[HKAP] persist year=%d failed: %s", year, exc)

    def _load_persisted_results(self) -> None:
        """On startup, reload any completed year packages from disk."""
        if not self._config.resume_on_restart:
            return
        root = Path(self._config.data_root)
        for year in self._config.sorted_years:
            path = root / str(year) / "year_knowledge_package.json"
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    # minimal reconstruction — just status and key metadata
                    from .hkap_models import (
                        YearDNASnapshot, YearEdgeSnapshot,
                        YearMarketProfile, YearSDReview
                    )
                    # lightweight reload: status + dna confidence map for cross-year use
                    ds = None
                    if data.get("dna_snapshot"):
                        d = data["dna_snapshot"]
                        ds = YearDNASnapshot(
                            year=d["year"], winner_dna=d.get("winner_dna", []),
                            loser_dna=d.get("loser_dna", []),
                            neutral_dna=d.get("neutral_dna", []),
                            regime_specific_dna=d.get("regime_specific_dna", {}),
                            regime_independent_dna=d.get("regime_independent_dna", []),
                            total_discovered=d.get("total_discovered", 0),
                            high_confidence_count=d.get("high_confidence_count", 0),
                            median_confidence=d.get("median_confidence", 0.0),
                            confidence_by_id=d.get("confidence_by_id", {}),
                            source_db=d.get("source_db", ""),
                        )
                    es = None
                    if data.get("edge_snapshot"):
                        e = data["edge_snapshot"]
                        es = YearEdgeSnapshot(
                            year=e["year"], active_edges=e.get("active_edges", []),
                            promoted_this_year=e.get("promoted_this_year", []),
                            demoted_this_year=e.get("demoted_this_year", []),
                            retired_this_year=e.get("retired_this_year", []),
                            survival_rate=e.get("survival_rate", 0.0),
                            new_edge_rate=e.get("new_edge_rate", 0.0),
                            total_prior_edges=e.get("total_prior_edges", 0),
                        )
                    mp = None
                    if data.get("market_profile"):
                        m = data["market_profile"]
                        mp = YearMarketProfile(**m)
                    pkg = YearKnowledgePackage(
                        year=data["year"], status=data["status"],
                        market_profile=mp, dna_snapshot=ds, edge_snapshot=es,
                        sd_review=None,
                        prior_years_context=data.get("prior_years_context", []),
                        trading_days_analyzed=data.get("trading_days_analyzed", 0),
                        universe_size=data.get("universe_size", 0),
                        completed_at=data.get("completed_at", ""),
                        reports=data.get("reports", []),
                        stage_statuses=data.get("stage_statuses", {}),
                    )
                    self._results[year] = pkg
                    log.info("[HKAP] loaded year=%d status=%s from disk", year, pkg.status)
                except Exception as exc:
                    log.debug("[HKAP] load year=%d failed: %s", year, exc)

    @staticmethod
    def _build_default_ptue() -> Any:
        """Build a PTUE instance with default config."""
        from autonomous_research.ptue        import PointInTimeUniverseEngine
        from autonomous_research.ptue_config import PTUEConfig
        return PointInTimeUniverseEngine(config=PTUEConfig())
