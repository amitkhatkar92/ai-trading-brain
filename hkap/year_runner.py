"""
year_runner.py — Orchestrates the complete HKAP pipeline for a single calendar year.

Pipeline stages (run in order, each isolated from the others):

  stage_universe      — PTUE point-in-time constituent list
  stage_snapshots     — HistoricalSnapshotBuilder: yfinance → DailyMarketSnapshot
  stage_mls           — PopulationClassifier + DNADiscoveryEngine + DNAConsensusEngine
  stage_idr           — Save year consensus DNA to year-specific IDR
  stage_profile       — MarketProfiler: regime / sector / personality
  stage_edges         — Edge discovery (high-confidence DNA from IDR)
  stage_cross_year    — Compare DNA to prior years
  stage_sd_review     — ScientificDirector review (year-scoped SD instance)
  stage_reports       — Generate all per-year markdown files

Forward-only constraint is enforced in __init__: if any prior_context year
>= current year, FutureDataLeakError is raised immediately.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .hkap_config  import HKAPConfig
from .hkap_models  import (
    FutureDataLeakError,
    YearDNASnapshot,
    YearEdgeSnapshot,
    YearKnowledgePackage,
    YearSDReview,
    YearStudyStatus,
)
from .market_profiler import MarketProfiler
from .snapshot_builder import HistoricalSnapshotBuilder

log = logging.getLogger(__name__)

_STAGE_UNIVERSE   = "universe"
_STAGE_SNAPSHOTS  = "snapshots"
_STAGE_MLS        = "mls"
_STAGE_IDR        = "idr"
_STAGE_PROFILE    = "profile"
_STAGE_EDGES      = "edges"
_STAGE_CROSS_YEAR = "cross_year"
_STAGE_SD_REVIEW  = "sd_review"
_STAGE_REPORTS    = "reports"

_ALL_STAGES = [
    _STAGE_UNIVERSE, _STAGE_SNAPSHOTS, _STAGE_MLS, _STAGE_IDR,
    _STAGE_PROFILE, _STAGE_EDGES, _STAGE_CROSS_YEAR, _STAGE_SD_REVIEW,
    _STAGE_REPORTS,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class YearRunner:
    """
    Single-year HKAP pipeline runner.

    Constructs fresh MLS component instances scoped to {data_root}/{year}/.
    Never writes to any prior year's directory.
    Stage failures are isolated — remaining stages continue.
    """

    def __init__(
        self,
        year:          int,
        config:        HKAPConfig,
        ptue:          Any,   # PointInTimeUniverseEngine
        prior_context: Optional[List[YearKnowledgePackage]] = None,
    ) -> None:
        self._year    = year
        self._config  = config
        self._ptue    = ptue
        self._prior   = prior_context or []

        # ── enforce forward-only ──────────────────────────────────────────
        for pkg in self._prior:
            if pkg.year >= self._year:
                raise FutureDataLeakError(self._year, pkg.year)

        self._year_dir = Path(config.data_root) / str(year)
        self._year_dir.mkdir(parents=True, exist_ok=True)
        self._reports_dir = Path(config.reports_root) / str(year)
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        self._stage_statuses: Dict[str, str] = {s: "PENDING" for s in _ALL_STAGES}
        self._sector_map: Dict[str, str] = self._load_sector_map()

    # ── public API ────────────────────────────────────────────────────────

    def run(self) -> YearKnowledgePackage:
        """
        Execute all pipeline stages for this year.
        Returns a YearKnowledgePackage regardless of individual stage failures.
        """
        log.info("[HKAP][YR] year=%d starting pipeline (prior=%s)",
                 self._year, [p.year for p in self._prior])

        symbols:     List[str]  = []
        snapshots:   List[dict] = []
        idr_path:    Optional[Path]         = None
        dna_snap:    Optional[YearDNASnapshot]  = None
        edge_snap:   Optional[YearEdgeSnapshot] = None
        profile     = None
        sd_review   = None
        reports:     List[str]  = []

        # ── stage: universe ───────────────────────────────────────────────
        try:
            symbols = self._stage_universe()
            self._stage_statuses[_STAGE_UNIVERSE] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=universe FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_UNIVERSE] = "FAILED"

        if not symbols:
            return self._failed_package("No symbols available")

        # ── stage: snapshots ──────────────────────────────────────────────
        try:
            snapshots = self._stage_snapshots(symbols)
            self._stage_statuses[_STAGE_SNAPSHOTS] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=snapshots FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_SNAPSHOTS] = "FAILED"

        if len(snapshots) < self._config.min_trading_days:
            log.warning("[HKAP][YR] year=%d insufficient trading days (%d<%d)",
                        self._year, len(snapshots), self._config.min_trading_days)
            return self._failed_package("Insufficient trading days")

        # ── stage: MLS pipeline ────────────────────────────────────────────
        try:
            idr_path = self._stage_mls(snapshots)
            self._stage_statuses[_STAGE_MLS] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=mls FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_MLS] = "FAILED"

        # ── stage: IDR → DNA snapshot ─────────────────────────────────────
        try:
            if idr_path:
                dna_snap = self._stage_idr(idr_path)
                self._stage_statuses[_STAGE_IDR] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=idr FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_IDR] = "FAILED"

        # ── stage: market profile ─────────────────────────────────────────
        try:
            profile = MarketProfiler().profile_year(self._year, snapshots, self._sector_map)
            self._stage_statuses[_STAGE_PROFILE] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=profile FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_PROFILE] = "FAILED"

        # ── stage: edge discovery ─────────────────────────────────────────
        try:
            edge_snap = self._stage_edges(dna_snap)
            self._stage_statuses[_STAGE_EDGES] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=edges FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_EDGES] = "FAILED"

        # ── stage: cross-year comparison ──────────────────────────────────
        try:
            if self._prior and dna_snap:
                self._stage_cross_year(dna_snap, edge_snap)
            self._stage_statuses[_STAGE_CROSS_YEAR] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=cross_year FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_CROSS_YEAR] = "FAILED"

        # ── stage: SD review ──────────────────────────────────────────────
        try:
            sd_review = self._stage_sd_review(dna_snap, profile)
            self._stage_statuses[_STAGE_SD_REVIEW] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=sd_review FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_SD_REVIEW] = "FAILED"

        # ── stage: reports ────────────────────────────────────────────────
        try:
            from .report_generator import HKAPReportGenerator
            pkg_preview = YearKnowledgePackage(
                year=self._year, status=YearStudyStatus.COMPLETE.value,
                market_profile=profile, dna_snapshot=dna_snap,
                edge_snapshot=edge_snap, sd_review=sd_review,
                prior_years_context=[p.year for p in self._prior],
                trading_days_analyzed=len(snapshots), universe_size=len(symbols),
                completed_at=_now_iso(), reports=[], stage_statuses=dict(self._stage_statuses),
            )
            gen = HKAPReportGenerator(self._config)
            reports = gen.generate_year_reports(pkg_preview)
            self._stage_statuses[_STAGE_REPORTS] = "COMPLETE"
        except Exception as exc:
            log.error("[HKAP][YR] year=%d stage=reports FAILED: %s", self._year, exc)
            self._stage_statuses[_STAGE_REPORTS] = "FAILED"

        # ── persist package to disk ───────────────────────────────────────
        pkg = YearKnowledgePackage(
            year                   = self._year,
            status                 = YearStudyStatus.COMPLETE.value,
            market_profile         = profile,
            dna_snapshot           = dna_snap,
            edge_snapshot          = edge_snap,
            sd_review              = sd_review,
            prior_years_context    = [p.year for p in self._prior],
            trading_days_analyzed  = len(snapshots),
            universe_size          = len(symbols),
            completed_at           = _now_iso(),
            reports                = reports,
            stage_statuses         = dict(self._stage_statuses),
        )
        self._save_package(pkg)
        log.info("[HKAP][YR] year=%d COMPLETE dna=%d edges=%d reports=%d",
                 self._year,
                 dna_snap.total_discovered if dna_snap else 0,
                 len(edge_snap.active_edges) if edge_snap else 0,
                 len(reports))
        return pkg

    # ── stage implementations ─────────────────────────────────────────────

    def _stage_universe(self) -> List[str]:
        """Get NIFTY500 constituent list for start-of-year using PTUE."""
        date_str  = f"{self._year}-01-02"  # first trading day of year
        universe  = self._ptue.get_universe(date_str, self._config.universe_name)
        symbols   = universe.symbols[:self._config.max_symbols]
        log.info("[HKAP][YR] year=%d universe size=%d (capped at %d)",
                 self._year, len(universe.symbols), self._config.max_symbols)
        return symbols

    def _stage_snapshots(self, symbols: List[str]) -> List[dict]:
        """Build DailyMarketSnapshot dicts for all trading days in the year."""
        builder = HistoricalSnapshotBuilder(
            cache_dir     = self._year_dir,
            sector_map    = self._sector_map,
            dry_run       = self._config.dry_run,
            lookback_days = self._config.download_lookback_days,
        )
        return builder.build_year(self._year, symbols)

    def _stage_mls(self, snapshot_dicts: List[dict]) -> Optional[Path]:
        """
        Run PopulationClassifier + DNADiscoveryEngine + DNAConsensusEngine
        on all snapshots and persist to the year-specific IDR.
        Returns the IDR db path.
        """
        from market_learning.market_observer_models import (
            DailyMarketSnapshot, MarketObservation, ObservationMetadata,
        )
        from market_learning.population_classifier import PopulationClassifier
        from market_learning.dna_discovery_engine  import DNADiscoveryEngine
        from market_learning.dna_consensus_engine  import DNAConsensusEngine
        from market_learning.idr_repository        import IDRRepository
        from market_learning.dna_consensus_models  import ConsensusLibrary

        mls_dir  = self._year_dir / "mls"
        idr_path = self._year_dir / "institutional_dna.db"

        classifier = PopulationClassifier(data_dir=mls_dir)
        dde        = DNADiscoveryEngine(data_dir=mls_dir)
        dce        = DNAConsensusEngine(data_dir=str(mls_dir / "consensus"))
        idr        = IDRRepository(db_path=idr_path)

        history: list = []
        processed = 0

        for snap_dict in snapshot_dicts:
            try:
                snapshot = self._dict_to_snapshot(snap_dict,
                                                   DailyMarketSnapshot,
                                                   MarketObservation,
                                                   ObservationMetadata)
                classification = classifier.classify(snapshot)
                discovery      = dde.discover(snapshot, classification, history)
                dce.update(discovery)
                history.append(discovery)
                if len(history) > 60:
                    history = history[-60:]  # keep rolling 60-day window
                processed += 1
            except Exception as exc:
                log.debug("[HKAP][YR] year=%d snap=%s MLS error: %s",
                          self._year, snap_dict.get("trading_date", "?"), exc)

        log.info("[HKAP][YR] year=%d MLS processed %d/%d snapshots",
                 self._year, processed, len(snapshot_dicts))

        # ── sync final consensus library to IDR ───────────────────────────
        lib = dce.get_library() if hasattr(dce, "get_library") else None
        if lib:
            self._sync_library_to_idr(lib, idr, self._year)

        return idr_path if idr_path.exists() else None

    def _dict_to_snapshot(
        self, d: dict, SnapshotCls, ObsCls, MetaCls
    ) -> Any:
        """Construct a DailyMarketSnapshot from a raw dict."""
        obs_list = [
            ObsCls(
                symbol            = o["symbol"],
                feature_timestamp = o["feature_timestamp"],
                features          = o["features"],
                feature_count     = o["feature_count"],
            )
            for o in d.get("observations", [])
        ]
        md = d.get("metadata", {})
        meta = MetaCls(
            run_id                     = md.get("run_id", f"HKAP-{self._year}"),
            trading_date               = md.get("trading_date", d["trading_date"]),
            capture_time               = md.get("capture_time", d["feature_timestamp"]),
            universe_size              = md.get("universe_size", len(obs_list)),
            feature_count              = md.get("feature_count", 0),
            snapshot_id                = md.get("snapshot_id", d["snapshot_id"]),
            temporal_contract_verified = md.get("temporal_contract_verified", True),
            regime                     = md.get("regime", d.get("regime", "RANGE_MARKET")),
            volatility                 = md.get("volatility", d.get("volatility", "MEDIUM")),
            vix                        = float(md.get("vix", 0.0)),
            pcr                        = float(md.get("pcr", 0.0)),
            breadth                    = float(md.get("breadth", d.get("breadth", 0.5))),
            global_bias                = float(md.get("global_bias", 0.5)),
            mls_config_hash            = md.get("mls_config_hash", ""),
            warnings                   = list(md.get("warnings", [])),
        )
        return SnapshotCls(
            snapshot_id       = d["snapshot_id"],
            trading_date      = d["trading_date"],
            feature_timestamp = d["feature_timestamp"],
            regime            = d.get("regime", "RANGE_MARKET"),
            volatility        = d.get("volatility", "MEDIUM"),
            vix               = float(d.get("vix", 0.0)),
            pcr               = float(d.get("pcr", 0.0)),
            breadth           = float(d.get("breadth", 0.5)),
            global_bias       = float(d.get("global_bias", 0.5)),
            universe_size     = d.get("universe_size", len(obs_list)),
            symbols           = d.get("symbols", [o.symbol for o in obs_list]),
            observations      = obs_list,
            metadata          = meta,
            created_at        = d.get("created_at", _now_iso()),
        )

    def _sync_library_to_idr(self, lib: Any, idr: Any, year: int) -> None:
        """Write ConsensusDNA records from ConsensusLibrary to the IDR."""
        from market_learning.idr_models import InstitutionalDNA
        try:
            items = lib.dna if hasattr(lib, "dna") else {}
            for key, cdna in items.items():
                try:
                    idna = InstitutionalDNA(
                        id                    = cdna.id,
                        feature_name          = cdna.feature_name,
                        direction             = cdna.direction.value if hasattr(cdna.direction, "value") else str(cdna.direction),
                        category              = cdna.category.value  if hasattr(cdna.category,  "value") else str(cdna.category),
                        lifecycle             = cdna.lifecycle.value  if hasattr(cdna.lifecycle,  "value") else str(cdna.lifecycle),
                        consensus_score       = float(getattr(cdna, "consensus_score", 0.0)),
                        confidence            = float(getattr(cdna, "confidence", 0.0)),
                        effect_size           = float(getattr(cdna, "effect_size", 0.0)),
                        regime_consistency    = float(getattr(cdna, "regime_consistency", 0.0)),
                        sector_consistency    = float(getattr(cdna, "sector_consistency", 0.0)),
                        temporal_stability    = float(getattr(cdna, "temporal_stability", 0.0)),
                        replication_frequency = float(getattr(cdna, "replication_frequency", 0.0)),
                        evidence_count        = int(getattr(cdna, "evidence_count", 0)),
                        regime_counts         = getattr(cdna, "regime_counts", {}),
                        last_seen             = getattr(cdna, "last_seen", None),
                        study_id              = f"HKAP-{year}",
                        source                = "HKAP",
                        created_at            = _now_iso(),
                        updated_at            = _now_iso(),
                        is_current            = True,
                        version               = 1,
                        metadata              = {},
                    )
                    idr.save(idna)
                except Exception as exc:
                    log.debug("[HKAP][YR] IDR sync item failed: %s", exc)
        except Exception as exc:
            log.warning("[HKAP][YR] IDR sync failed: %s", exc)

    def _stage_idr(self, idr_path: Path) -> YearDNASnapshot:
        """Read the year's IDR and build a YearDNASnapshot."""
        from market_learning.idr_repository import IDRRepository
        idr = IDRRepository(db_path=idr_path)
        all_dna  = idr.list_all() if hasattr(idr, "list_all") else []
        winner   = [d.id for d in all_dna if getattr(d, "category", "") in ("WINNER", "winner_dna")]
        loser    = [d.id for d in all_dna if getattr(d, "category", "") in ("LOSER", "loser_dna")]
        neutral  = [d.id for d in all_dna if d.id not in winner and d.id not in loser]
        conf_map = {d.id: float(getattr(d, "confidence", 0.0)) for d in all_dna}
        high_conf = [d for d in all_dna if float(getattr(d, "confidence", 0.0)) >= self._config.dna_edge_threshold]
        median_c  = sorted(conf_map.values())[len(conf_map) // 2] if conf_map else 0.0

        # regime-specific: dna that appears only under one regime
        regime_specific: Dict[str, List[str]] = {}
        regime_independent: List[str]         = []
        for d in all_dna:
            rc = getattr(d, "regime_counts", {})
            active_regimes = [r for r, cnt in rc.items() if cnt > 0] if isinstance(rc, dict) else []
            if len(active_regimes) == 1:
                regime_specific.setdefault(active_regimes[0], []).append(d.id)
            elif len(active_regimes) == 0 or len(active_regimes) >= 3:
                regime_independent.append(d.id)

        return YearDNASnapshot(
            year                   = self._year,
            winner_dna             = winner,
            loser_dna              = loser,
            neutral_dna            = neutral,
            regime_specific_dna    = regime_specific,
            regime_independent_dna = regime_independent,
            total_discovered       = len(all_dna),
            high_confidence_count  = len(high_conf),
            median_confidence      = median_c,
            confidence_by_id       = conf_map,
            source_db              = str(idr_path),
        )

    def _stage_edges(self, dna_snap: Optional[YearDNASnapshot]) -> YearEdgeSnapshot:
        """Identify edges (high-confidence DNA) and compare to prior year."""
        active_edges = []
        if dna_snap:
            active_edges = [
                dna_id for dna_id, conf in dna_snap.confidence_by_id.items()
                if conf >= self._config.dna_edge_threshold
            ]

        # compare to prior year's edges
        prior_active: List[str] = []
        if self._prior:
            last_prior = self._prior[-1]
            if last_prior.edge_snapshot:
                prior_active = last_prior.edge_snapshot.active_edges

        promoted  = [e for e in active_edges if e not in prior_active]
        demoted   = [e for e in prior_active if e not in active_edges and
                     (dna_snap and e in dna_snap.confidence_by_id)]
        retired   = [e for e in prior_active if e not in active_edges and
                     (not dna_snap or e not in dna_snap.confidence_by_id)]

        total_prior  = len(prior_active)
        survival     = len([e for e in active_edges if e in prior_active]) / max(total_prior, 1)
        new_rate     = len(promoted) / max(len(active_edges), 1)

        return YearEdgeSnapshot(
            year               = self._year,
            active_edges       = active_edges,
            promoted_this_year = promoted,
            demoted_this_year  = demoted,
            retired_this_year  = retired,
            survival_rate      = survival,
            new_edge_rate      = new_rate,
            total_prior_edges  = total_prior,
        )

    def _stage_cross_year(
        self, dna_snap: YearDNASnapshot, edge_snap: Optional[YearEdgeSnapshot]
    ) -> None:
        """Log cross-year comparison observations (stored in edge_snap already)."""
        if not self._prior:
            return
        prior_counts = [p.dna_snapshot.total_discovered for p in self._prior
                        if p.dna_snapshot]
        avg_prior = sum(prior_counts) / len(prior_counts) if prior_counts else 0
        trend = "GROWING" if dna_snap.total_discovered > avg_prior else "SHRINKING"
        log.info("[HKAP][YR] year=%d cross_year: dna_count=%d avg_prior=%.0f trend=%s",
                 self._year, dna_snap.total_discovered, avg_prior, trend)

    def _stage_sd_review(
        self,
        dna_snap: Optional[YearDNASnapshot],
        profile: Any,
    ) -> YearSDReview:
        """
        Run a ScientificDirector review scoped to this year.

        Uses a fresh SD instance with the year-specific IDR.
        All components optional — SD degrades gracefully when None.
        """
        from autonomous_research.scientific_director import ScientificDirector
        from autonomous_research.sd_config           import SDConfig

        idr_path = self._year_dir / "institutional_dna.db"
        idr = None
        if idr_path.exists():
            try:
                from market_learning.idr_repository import IDRRepository
                idr = IDRRepository(db_path=idr_path)
            except Exception:
                pass

        sd_journal = self._year_dir / "sd_journal.json"
        sd = ScientificDirector(
            idr    = idr,
            config = SDConfig(
                dry_run      = self._config.dry_run,
                journal_path = str(sd_journal),
            ),
        )

        review = sd.monthly_review()   # monthly review inspects IDR state

        observations = [str(obs) for obs in (review.observations or [])]
        decisions    = [str(d)   for d   in (review.decisions    or [])]

        lessons = [
            f"Year {self._year}: {profile.market_personality if profile else 'unknown'} "
            f"market with {dna_snap.total_discovered if dna_snap else 0} DNA patterns",
        ]
        if profile:
            lessons.append(
                f"Dominant regime {profile.dominant_regime} "
                f"({profile.regime_distribution.get(profile.dominant_regime, 0):.0%} of days)"
            )

        questions = [
            "Which DNA patterns from this year persist into the next?",
            "Do the high-confidence edges survive a regime change?",
        ]
        if dna_snap and dna_snap.high_confidence_count == 0:
            questions.append(
                "Why were no high-confidence edges discovered? "
                "Possible data quality issue?"
            )

        recommendation = (
            f"Run targeted study on top-performing DNA patterns "
            f"from {self._year} under {profile.dominant_regime if profile else 'unknown'} regime."
        )

        return YearSDReview(
            year                = self._year,
            review_id           = getattr(review, "review_id", f"HKAP-SD-{self._year}"),
            health              = getattr(review, "health", "UNKNOWN"),
            observations        = observations,
            reasoning           = getattr(review, "summary", f"Year {self._year} assessment."),
            lessons_learned     = lessons,
            remaining_questions = questions,
            recommended_study   = recommendation,
            confidence          = 0.7,
            generated_at        = _now_iso(),
        )

    # ── utilities ─────────────────────────────────────────────────────────

    def _save_package(self, pkg: YearKnowledgePackage) -> None:
        if self._config.dry_run:
            return
        path = self._year_dir / "year_knowledge_package.json"
        try:
            with open(path, "w") as f:
                json.dump(pkg.to_dict(), f, indent=2)
        except Exception as exc:
            log.warning("[HKAP][YR] year=%d save_package failed: %s", self._year, exc)

    def _failed_package(self, reason: str) -> YearKnowledgePackage:
        log.warning("[HKAP][YR] year=%d FAILED: %s", self._year, reason)
        return YearKnowledgePackage(
            year                  = self._year,
            status                = YearStudyStatus.FAILED.value,
            market_profile        = None,
            dna_snapshot          = None,
            edge_snapshot         = None,
            sd_review             = None,
            prior_years_context   = [p.year for p in self._prior],
            trading_days_analyzed = 0,
            universe_size         = 0,
            completed_at          = _now_iso(),
            reports               = [],
            stage_statuses        = dict(self._stage_statuses),
        )

    @staticmethod
    def _load_sector_map() -> Dict[str, str]:
        """Load symbol → sector from data/nifty500_universe.json."""
        universe_path = Path("data/nifty500_universe.json")
        if not universe_path.exists():
            return {}
        try:
            with open(universe_path) as f:
                items = json.load(f)
            return {item["symbol"]: item.get("sector", "OTHER") for item in items}
        except Exception:
            return {}
