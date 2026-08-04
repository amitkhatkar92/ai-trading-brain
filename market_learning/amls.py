"""
amls.py — Autonomous Market Learning Scheduler (AMLS).

MLS Phase 6.

AMLS is the operational heartbeat of MLS.  It orchestrates the complete
Market Learning System pipeline every trading day, without human intervention.

Responsibilities:
    Detect trading days and market events.
    Execute MLS pipeline stages in order.
    Handle retries and stage-level failure recovery.
    Persist DNA to the Institutional DNA Repository.
    Signal the Platform Intelligence Gateway to reload.
    Generate a complete execution telemetry record for every run.
    Maintain an auditable run history.

Explicitly NOT responsible for:
    DNA discovery (DNADiscoveryEngine does that).
    DNA scoring (PMCIEngine, CDSEngine, CAPMCIEngine do that).
    Trading decisions (DecisionEngine does that).
    Changing strategies or thresholds.
    Any write not directly required for MLS pipeline persistence.

Design contract:
    - Every stage failure is caught, recorded, and never propagates.
    - generate_report stage ALWAYS runs regardless of upstream failures.
    - Thread-safe: multiple callers get consistent state.
    - History is atomically written to disk after every run.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import date as _date
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .amls_config import AMLSConfig
from .amls_models import (
    ALL_STAGES,
    ALWAYS_RUN_STAGES,
    STAGE_CLASSIFY,
    STAGE_CONSENSUS,
    STAGE_DISCOVER,
    STAGE_IDR_SYNC,
    STAGE_PIG_REFRESH,
    STAGE_REPORT,
    STAGE_SNAPSHOT,
    MLSPipelineRun,
    PipelineFailure,
    PipelineHealth,
    PipelineStage,
    PipelineState,
    PipelineStatistics,
    PipelineTelemetry,
)
from .mls_config import MLSConfig

log = logging.getLogger(__name__)

_IST = timezone(timedelta(hours=5, minutes=30))
_DEFAULT_MLS_DIR = Path(__file__).resolve().parent.parent / "data" / "mls"


# ─── helpers ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Current time as ISO 8601 string."""
    return datetime.now().isoformat()


def _today_str() -> str:
    """Today's date as YYYY-MM-DD."""
    return _date.today().isoformat()


def _amls_run_id(date_str: str) -> str:
    """Deterministic run ID for a given date."""
    uid = uuid.uuid4().hex[:8]
    return f"AMLS-{date_str.replace('-', '')}-{uid}"


def _skipped_run(run_id: str, date_str: str, reason: str) -> MLSPipelineRun:
    now = _now_iso()
    stage = PipelineStage(
        name=STAGE_SNAPSHOT,
        state=PipelineState.SKIPPED,
        start_time=now,
        end_time=now,
        duration_ms=0.0,
        retry_count=0,
        output_summary=reason,
        failure=None,
    )
    return MLSPipelineRun(
        run_id=run_id,
        trading_date=date_str,
        state=PipelineState.SKIPPED,
        stages=[stage],
        started_at=now,
        ended_at=now,
        total_duration_ms=0.0,
        telemetry=None,
    )


def _determine_run_state(stages: List[PipelineStage]) -> PipelineState:
    """Derive overall run state from individual stage states."""
    substantive = [s for s in stages if s.name != STAGE_REPORT]
    if not substantive:
        return PipelineState.SKIPPED
    success_n = sum(1 for s in substantive if s.state == PipelineState.SUCCESS)
    failed_n  = sum(1 for s in substantive if s.state == PipelineState.FAILED)
    skipped_n = sum(1 for s in substantive if s.state == PipelineState.SKIPPED)
    total     = len(substantive)
    if success_n == total:
        return PipelineState.SUCCESS
    if success_n == 0 and skipped_n == total:
        return PipelineState.SKIPPED
    if success_n == 0:
        return PipelineState.FAILED
    return PipelineState.PARTIAL


# ─── IDR sync helper ─────────────────────────────────────────────────────────

def _cdna_category(direction_value: str) -> str:
    """Map SeparationDirection.value → IDR category string."""
    if direction_value in ("WINNERS_HIGHER", "WINNERS_LOWER"):
        return "WINNER"
    if direction_value in ("NEUTRALS_HIGHER", "NEUTRALS_LOWER"):
        return "NEUTRAL"
    return "CONSENSUS"


def _cdna_to_idr(cdna: Any, now_str: str) -> Any:
    """Convert ConsensusDNA → InstitutionalDNA for IDR persistence."""
    from .idr_models import InstitutionalDNA  # lazy import — avoid cycle

    last_obs = cdna.all_observations[-1] if cdna.all_observations else {}
    confidence = float(last_obs.get("confidence", 0.0))
    effect_abs = float(last_obs.get("effect_abs", 0.0))

    return InstitutionalDNA(
        id=cdna.consensus_id,
        feature_name=cdna.feature_name,
        direction=cdna.direction.value,
        category=_cdna_category(cdna.direction.value),
        lifecycle=cdna.consensus_state.value,
        version=1,                               # IDR handles versioning on save()
        consensus_score=cdna.consensus_score,
        confidence=confidence,
        effect_size=effect_abs,
        regime_consistency=cdna.regime_consistency,
        sector_consistency=cdna.sector_consistency,
        temporal_stability=cdna.temporal_stability,
        replication_frequency=cdna.replication_frequency,
        evidence_count=cdna.evidence_count,
        regime_counts=dict(cdna.regime_counts),
        last_seen=cdna.last_seen,
        study_id="AMLS",
        source="amls_phase6",
        created_at=cdna.first_seen,
        updated_at=now_str,
        is_current=True,
        metadata={
            "level":               cdna.level.value,
            "feature_persistence": cdna.feature_persistence,
            "confidence_trend":    cdna.confidence_trend,
        },
    )


# ─── AutonomousMarketLearningScheduler ───────────────────────────────────────

class AutonomousMarketLearningScheduler:
    """
    MLS Phase 6 — Autonomous Market Learning Scheduler.

    Orchestrates the complete MLS pipeline every trading day.
    No learning, discovery, or DNA logic lives here.
    This class only coordinates calls to existing MLS modules.

    Usage::

        from market_learning import AutonomousMarketLearningScheduler
        amls = AutonomousMarketLearningScheduler()

        # Full pipeline (post-market close, ~15:35)
        run = amls.run_pipeline()

        # Full pipeline with live snapshot (called at 15:35 with 09:15 snapshot)
        run = amls.run_pipeline(market_snapshot=saved_0915_snapshot)

        # Query API
        status = amls.pipeline_status()
        last   = amls.last_run()
        stats  = amls.statistics()
        health = amls.health_check()
    """

    # Stage name constants (mirrors amls_models.py)
    STAGE_SNAPSHOT    = STAGE_SNAPSHOT
    STAGE_CLASSIFY    = STAGE_CLASSIFY
    STAGE_DISCOVER    = STAGE_DISCOVER
    STAGE_CONSENSUS   = STAGE_CONSENSUS
    STAGE_IDR_SYNC    = STAGE_IDR_SYNC
    STAGE_PIG_REFRESH = STAGE_PIG_REFRESH
    STAGE_REPORT      = STAGE_REPORT

    def __init__(
        self,
        config:      Optional[AMLSConfig]   = None,
        mls_config:  Optional[MLSConfig]    = None,
        data_dir:    Optional[Path]         = None,
        # ── Injectable MLS modules (supply mocks in tests) ────────────────
        observer:    Optional[Any]          = None,  # MarketObserver
        classifier:  Optional[Any]          = None,  # PopulationClassifier
        discovery:   Optional[Any]          = None,  # DNADiscoveryEngine
        consensus:   Optional[Any]          = None,  # DNAConsensusEngine
        idr:         Optional[Any]          = None,  # IDRRepository
        pig_adapter: Optional[Any]          = None,  # PIGTradingAdapter (optional)
    ) -> None:
        self._cfg      = config     or AMLSConfig()
        self._mls_cfg  = mls_config or MLSConfig()
        root           = Path(data_dir) if data_dir else _DEFAULT_MLS_DIR

        # History / report directory
        self._amls_dir   = root / "amls"
        self._amls_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._amls_dir / "history.json"

        # MLS module registry (lazy-load defaults, accept injected mocks)
        self._observer   = observer   or self._default_observer(self._mls_cfg, root)
        self._classifier = classifier or self._default_classifier(self._mls_cfg, root)
        self._discovery  = discovery  or self._default_discovery(self._mls_cfg, root)
        self._consensus  = consensus  or self._default_consensus(self._mls_cfg, root)
        self._idr        = idr        or self._default_idr(self._mls_cfg, root)
        self._pig_adapter = pig_adapter   # None is valid — PIG refresh becomes no-op

        self._lock         = threading.Lock()
        self._current_run: Optional[MLSPipelineRun] = None
        self._history:     List[MLSPipelineRun]     = []
        self._history_loaded = False

        log.info("[AMLS] Initialised. data_dir=%s pig_adapter=%s", root,
                 pig_adapter is not None)

    # ── default module constructors ──────────────────────────────────────────

    @staticmethod
    def _default_observer(cfg: MLSConfig, root: Path) -> Any:
        from .market_observer import MarketObserver
        return MarketObserver(config=cfg, data_dir=root)

    @staticmethod
    def _default_classifier(cfg: MLSConfig, root: Path) -> Any:
        from .population_classifier import PopulationClassifier
        return PopulationClassifier(config=cfg, data_dir=root)

    @staticmethod
    def _default_discovery(cfg: MLSConfig, root: Path) -> Any:
        from .dna_discovery_engine import DNADiscoveryEngine
        return DNADiscoveryEngine(config=cfg, data_dir=root)

    @staticmethod
    def _default_consensus(cfg: MLSConfig, root: Path) -> Any:
        from .dna_consensus_engine import DNAConsensusEngine
        return DNAConsensusEngine(config=cfg, data_dir=str(root / "consensus"))

    @staticmethod
    def _default_idr(cfg: MLSConfig, root: Path) -> Any:
        from .idr_repository import IDRRepository
        return IDRRepository(db_path=root / "institutional_dna.db", config=cfg)

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC QUERY API
    # ═════════════════════════════════════════════════════════════════════════

    def pipeline_status(self) -> PipelineState:
        """Return state of the current or last run."""
        with self._lock:
            if self._current_run is not None:
                return self._current_run.state
            history = self._load_history()
            return history[-1].state if history else PipelineState.WAITING

    def last_run(self) -> Optional[MLSPipelineRun]:
        """Return the most recent pipeline run, or None."""
        with self._lock:
            history = self._load_history()
            return history[-1] if history else None

    def history(self, days: int = 30) -> List[MLSPipelineRun]:
        """
        Return pipeline run history, newest first, limited to *days* days.
        """
        with self._lock:
            all_runs = self._load_history()
        cutoff = (_date.today() - timedelta(days=days)).isoformat()
        filtered = [r for r in all_runs if r.trading_date >= cutoff]
        return list(reversed(filtered))   # newest first

    def statistics(self) -> PipelineStatistics:
        """Compute aggregate statistics from all available run history."""
        with self._lock:
            runs = self._load_history()
        return self._compute_statistics(runs)

    def health_check(self) -> PipelineHealth:
        """Return a comprehensive health diagnostic snapshot."""
        with self._lock:
            runs = self._load_history()

        issues: List[str] = []

        # Last run state
        last    = runs[-1] if runs else None
        state   = last.state.value if last else PipelineState.WAITING.value
        run_date  = last.trading_date if last else None
        interrupted = last is not None and last.state in (
            PipelineState.RUNNING, PipelineState.PARTIAL
        )
        if interrupted:
            issues.append("Last pipeline run did not complete cleanly")

        # Days since last success
        success_runs = [r for r in runs if r.state == PipelineState.SUCCESS]
        last_success = success_runs[-1].trading_date if success_runs else None
        days_since: Optional[int] = None
        if last_success:
            delta = _date.today() - _date.fromisoformat(last_success)
            days_since = delta.days
            if days_since > 5:
                issues.append(f"Last successful run was {days_since} days ago")

        # Snapshot check
        today_str = _today_str()
        missing_snap = True
        try:
            snap = self._observer.load_snapshot(today_str)
            missing_snap = snap is None
        except Exception:
            missing_snap = True
        if missing_snap:
            issues.append(f"No market snapshot for {today_str}")

        # DNA check
        missing_dna = True
        try:
            lib = self._consensus.master_library()
            missing_dna = len(lib.all_consensus) == 0
        except Exception:
            missing_dna = True
        if missing_dna:
            issues.append("ConsensusLibrary is empty — MLS pipeline may never have run")

        # Repository check
        repo_ok = True
        try:
            self._idr.statistics()
        except Exception as e:
            repo_ok = False
            issues.append(f"IDR repository error: {e}")

        # Gateway check
        gw_ok = True
        if self._pig_adapter is not None:
            gw_ok = getattr(self._pig_adapter, "is_available", lambda: False)()
            if not gw_ok:
                issues.append("PIG adapter not loaded (no DNA data yet)")

        healthy = len(issues) == 0
        return PipelineHealth(
            healthy=healthy,
            issues=issues,
            pipeline_state=state,
            last_run_date=run_date,
            last_success_date=last_success,
            days_since_success=days_since,
            missing_snapshot=missing_snap,
            missing_dna=missing_dna,
            repository_ok=repo_ok,
            gateway_ok=gw_ok,
            pipeline_interrupted=interrupted,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # PIPELINE EXECUTION
    # ═════════════════════════════════════════════════════════════════════════

    def run_pipeline(
        self,
        market_snapshot: Optional[Any]   = None,
        date:            Optional[_date] = None,
        force:           bool            = False,
    ) -> MLSPipelineRun:
        """
        Execute the complete MLS pipeline for the given trading date.

        Args:
            market_snapshot: Pre-move MarketSnapshot (timestamp ≤ 09:15 IST).
                             If None, snapshot_capture loads today's file from disk.
            date:            Trading date. Defaults to today.
            force:           Skip calendar checks (weekend/holiday detection).

        Returns:
            MLSPipelineRun — complete run record including all stage results
            and telemetry. Always returned, even on failure or skip.
        """
        date_str = date.isoformat() if date else _today_str()
        run_id   = _amls_run_id(date_str)

        # ── Calendar gate ────────────────────────────────────────────────────
        if not force and not self._cfg.force_run:
            skip_reason = self._calendar_skip_reason(date_str)
            if skip_reason:
                run = _skipped_run(run_id, date_str, skip_reason)
                log.info("[AMLS] Skipped: run_id=%s reason=%s", run_id, skip_reason)
                self._append_history(run)
                with self._lock:
                    self._current_run = run
                return run

        log.info("[AMLS] Starting pipeline: run_id=%s date=%s", run_id, date_str)
        t0 = time.monotonic()
        started_at = _now_iso()

        stages: List[PipelineStage] = []
        ctx: Dict[str, Any] = {}   # intermediate pipeline values

        with self._lock:
            self._current_run = MLSPipelineRun(
                run_id=run_id,
                trading_date=date_str,
                state=PipelineState.RUNNING,
                stages=[],
                started_at=started_at,
                ended_at=None,
                total_duration_ms=None,
                telemetry=None,
            )

        # ── Stage 1: Snapshot capture ────────────────────────────────────────
        stage1, dms = self._execute_stage(
            STAGE_SNAPSHOT,
            self._fn_snapshot,
            market_snapshot,
            date_str,
        )
        stages.append(stage1)
        if dms is not None:
            ctx["dms"] = dms

        # ── Stage 2: Population classification ──────────────────────────────
        if ctx.get("dms") is not None:
            stage2, cls_result = self._execute_stage(
                STAGE_CLASSIFY,
                self._fn_classify,
                ctx["dms"],
            )
        else:
            stage2, cls_result = _skipped_stage(STAGE_CLASSIFY, "no snapshot available"), None
        stages.append(stage2)
        if cls_result is not None:
            ctx["classification"] = cls_result

        # ── Stage 3: DNA discovery ───────────────────────────────────────────
        if ctx.get("dms") is not None and ctx.get("classification") is not None:
            stage3, report = self._execute_stage(
                STAGE_DISCOVER,
                self._fn_discover,
                ctx["dms"],
                ctx["classification"],
            )
        else:
            stage3, report = _skipped_stage(STAGE_DISCOVER, "missing snapshot or classification"), None
        stages.append(stage3)
        if report is not None:
            ctx["report"] = report

        # ── Stage 4: DNA consensus ───────────────────────────────────────────
        if ctx.get("report") is not None:
            stage4, library = self._execute_stage(
                STAGE_CONSENSUS,
                self._fn_consensus,
                ctx["report"],
            )
        else:
            stage4, library = _skipped_stage(STAGE_CONSENSUS, "no discovery report"), None
        stages.append(stage4)
        if library is not None:
            ctx["library"] = library

        # ── Stage 5: IDR sync ────────────────────────────────────────────────
        if ctx.get("library") is not None:
            stage5, idr_writes = self._execute_stage(
                STAGE_IDR_SYNC,
                self._fn_idr_sync,
                ctx["library"],
            )
        else:
            stage5, idr_writes = _skipped_stage(STAGE_IDR_SYNC, "no consensus library"), None
        stages.append(stage5)
        ctx["idr_writes"] = idr_writes or 0

        # ── Stage 6: PIG refresh ─────────────────────────────────────────────
        # Runs when library updated; also runs on partial failure (best-effort).
        if ctx.get("library") is not None or STAGE_PIG_REFRESH in ALWAYS_RUN_STAGES:
            stage6, gw_refreshed = self._execute_stage(
                STAGE_PIG_REFRESH,
                self._fn_pig_refresh,
            )
        else:
            stage6, gw_refreshed = _skipped_stage(STAGE_PIG_REFRESH, "no new library"), None
        stages.append(stage6)
        ctx["gateway_refreshed"] = bool(gw_refreshed)

        # ── Stage 7: Generate report ─────────────────────────────────────────
        total_ms  = (time.monotonic() - t0) * 1000
        ended_at  = _now_iso()
        run_state = _determine_run_state(stages)
        stage7, telemetry = self._execute_stage(
            STAGE_REPORT,
            self._fn_report,
            run_id, date_str, started_at, ended_at, total_ms, stages, ctx,
        )
        stages.append(stage7)

        # ── Finalise run ─────────────────────────────────────────────────────
        run = MLSPipelineRun(
            run_id=run_id,
            trading_date=date_str,
            state=run_state,
            stages=stages,
            started_at=started_at,
            ended_at=ended_at,
            total_duration_ms=total_ms,
            telemetry=telemetry,
        )

        self._append_history(run)
        with self._lock:
            self._current_run = run

        log.info(
            "[AMLS] Pipeline complete: run_id=%s date=%s state=%s "
            "duration_ms=%.0f stages_ok=%d/%d",
            run_id, date_str, run_state.value, total_ms,
            len(run.successful_stages()), len(stages) - 1,  # exclude report
        )
        return run

    def run_stage(
        self,
        stage_name: str,
        context:    Optional[Dict[str, Any]] = None,
    ) -> PipelineStage:
        """
        Execute a single named stage independently.

        Each stage loads its required inputs from disk if not provided
        in context.  Useful for re-running failed stages or manual debugging.

        Args:
            stage_name: One of the STAGE_* constants.
            context:    Optional dict with pre-loaded values.
                        Keys: 'dms', 'classification', 'report',
                              'library', 'market_snapshot'

        Returns:
            PipelineStage — execution record (never raises).
        """
        ctx = context or {}
        if stage_name == STAGE_SNAPSHOT:
            stage, _ = self._execute_stage(
                STAGE_SNAPSHOT,
                self._fn_snapshot,
                ctx.get("market_snapshot"),
                _today_str(),
            )
        elif stage_name == STAGE_CLASSIFY:
            dms = ctx.get("dms") or self._observer.load_snapshot(_today_str())
            if dms is None:
                return _skipped_stage(STAGE_CLASSIFY, "no snapshot")
            stage, _ = self._execute_stage(STAGE_CLASSIFY, self._fn_classify, dms)
        elif stage_name == STAGE_DISCOVER:
            dms = ctx.get("dms") or self._observer.load_snapshot(_today_str())
            cr  = ctx.get("classification") or self._classifier.load_result(_today_str())
            if dms is None or cr is None:
                return _skipped_stage(STAGE_DISCOVER, "missing snapshot or classification")
            stage, _ = self._execute_stage(STAGE_DISCOVER, self._fn_discover, dms, cr)
        elif stage_name == STAGE_CONSENSUS:
            report = ctx.get("report") or self._discovery.load_report(_today_str())
            if report is None:
                return _skipped_stage(STAGE_CONSENSUS, "no discovery report")
            stage, _ = self._execute_stage(STAGE_CONSENSUS, self._fn_consensus, report)
        elif stage_name == STAGE_IDR_SYNC:
            library = ctx.get("library") or self._consensus.master_library()
            if not library.all_consensus:
                return _skipped_stage(STAGE_IDR_SYNC, "empty library")
            stage, _ = self._execute_stage(STAGE_IDR_SYNC, self._fn_idr_sync, library)
        elif stage_name == STAGE_PIG_REFRESH:
            stage, _ = self._execute_stage(STAGE_PIG_REFRESH, self._fn_pig_refresh)
        elif stage_name == STAGE_REPORT:
            return _skipped_stage(STAGE_REPORT, "run_stage() cannot generate standalone report")
        else:
            raise ValueError(f"Unknown stage name: {stage_name!r}")
        return stage

    # ═════════════════════════════════════════════════════════════════════════
    # STAGE FUNCTIONS
    # ═════════════════════════════════════════════════════════════════════════

    def _fn_snapshot(
        self,
        market_snapshot: Optional[Any],
        date_str: str,
    ) -> Any:
        """Execute snapshot_capture stage logic."""
        if market_snapshot is not None:
            dms = self._observer.capture(market_snapshot)
            log.info("[AMLS] Snapshot captured: id=%s universe=%s",
                     getattr(dms, "snapshot_id", "?"),
                     getattr(dms, "universe_size", "?"))
            return dms

        if not self._cfg.load_snapshot_from_disk:
            raise RuntimeError("No market_snapshot provided and load_snapshot_from_disk=False")

        dms = self._observer.load_snapshot(date_str)
        if dms is None:
            raise RuntimeError(
                f"No snapshot found on disk for {date_str} and no live snapshot provided"
            )
        log.info("[AMLS] Snapshot loaded from disk: id=%s date=%s",
                 getattr(dms, "snapshot_id", "?"), date_str)
        return dms

    def _fn_classify(self, dms: Any) -> Any:
        result = self._classifier.classify(dms)
        log.info("[AMLS] Classification done: id=%s populations=%d",
                 getattr(result, "result_id", "?"),
                 len(getattr(result, "populations", [])))
        return result

    def _fn_discover(self, dms: Any, classification: Any) -> Any:
        report = self._discovery.discover(dms, classification)
        n_chars = len(getattr(report, "all_characteristics", []))
        log.info("[AMLS] DNA discovery done: id=%s characteristics=%d",
                 getattr(report, "report_id", "?"), n_chars)
        return report

    def _fn_consensus(self, report: Any) -> Any:
        library = self._consensus.update(report)
        n_dna = len(getattr(library, "all_consensus", []))
        log.info("[AMLS] Consensus updated: library_id=%s total_dna=%d",
                 getattr(library, "library_id", "?"), n_dna)
        return library

    def _fn_idr_sync(self, library: Any) -> int:
        """Sync ConsensusLibrary → IDR.  Returns number of records written."""
        now_str = _now_iso()
        written = 0
        failed  = 0
        all_consensus = getattr(library, "all_consensus", [])
        for cdna in all_consensus:
            try:
                idr_record = _cdna_to_idr(cdna, now_str)
                self._idr.save(idr_record, study_id="AMLS", operator="amls_scheduler")
                written += 1
            except Exception as e:
                failed += 1
                log.warning("[AMLS] IDR sync failed for %s: %s",
                            getattr(cdna, "consensus_id", "?"), e)
        log.info("[AMLS] IDR sync complete: written=%d failed=%d total=%d",
                 written, failed, len(all_consensus))
        if failed > 0 and written == 0:
            raise RuntimeError(
                f"IDR sync: all {failed} record(s) failed to persist"
            )
        return written

    def _fn_pig_refresh(self) -> bool:
        """Signal PIG adapter to reload the updated library."""
        if self._pig_adapter is None:
            log.debug("[AMLS] PIG refresh skipped: no adapter injected")
            return False
        try:
            self._pig_adapter.reload_library()
            log.info("[AMLS] PIG adapter library reloaded")
            return True
        except Exception as e:
            log.warning("[AMLS] PIG reload failed: %s", e)
            raise

    def _fn_report(
        self,
        run_id:    str,
        date_str:  str,
        start:     str,
        end:       str,
        duration:  float,
        stages:    List[PipelineStage],
        ctx:       Dict[str, Any],
    ) -> PipelineTelemetry:
        """Build and persist PipelineTelemetry for the current run."""
        substantive = [s for s in stages if s.name != STAGE_REPORT]
        success_n  = sum(1 for s in substantive if s.state == PipelineState.SUCCESS)
        failed_n   = sum(1 for s in substantive if s.state == PipelineState.FAILED)
        skipped_n  = sum(1 for s in substantive if s.state == PipelineState.SKIPPED)
        retry_sum  = sum(s.retry_count for s in substantive)
        failures   = [s.failure for s in substantive if s.failure is not None]
        run_state  = _determine_run_state(substantive)

        report_obj = ctx.get("report")
        library    = ctx.get("library")
        n_chars    = len(getattr(report_obj, "all_characteristics", [])) if report_obj else 0
        n_dna      = len(getattr(library, "all_consensus", [])) if library else 0

        tel = PipelineTelemetry(
            run_id=run_id,
            trading_date=date_str,
            start_time=start,
            end_time=end,
            total_duration_ms=duration,
            pipeline_state=run_state.value,
            success=run_state == PipelineState.SUCCESS,
            stages_success=success_n,
            stages_failed=failed_n,
            stages_skipped=skipped_n,
            total_retry_count=retry_sum,
            knowledge_generated=n_chars > 0,
            dna_updated=n_dna > 0,
            repository_writes=int(ctx.get("idr_writes", 0)),
            gateway_refreshed=bool(ctx.get("gateway_refreshed", False)),
            failures=failures,
        )

        self._persist_report(date_str, tel)
        return tel

    # ═════════════════════════════════════════════════════════════════════════
    # EXECUTION ENGINE
    # ═════════════════════════════════════════════════════════════════════════

    def _execute_stage(
        self,
        name: str,
        fn:   Any,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[PipelineStage, Optional[Any]]:
        """
        Execute *fn* with retry and timing.  Never raises.

        Returns (PipelineStage, result_or_None).
        """
        start = _now_iso()
        t0    = time.monotonic()
        retry = 0
        last_exc: Optional[Exception] = None
        result: Optional[Any] = None

        while retry <= self._cfg.max_retries:
            try:
                result = fn(*args, **kwargs)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                retry += 1
                log.debug("[AMLS] Stage %s attempt %d failed: %s", name, retry, exc)
                if retry <= self._cfg.max_retries:
                    self._sleep_retry(retry)

        duration = (time.monotonic() - t0) * 1000.0
        end      = _now_iso()

        if last_exc is None:
            summary = self._stage_summary(name, result)
            return (
                PipelineStage(
                    name=name,
                    state=PipelineState.SUCCESS,
                    start_time=start,
                    end_time=end,
                    duration_ms=duration,
                    retry_count=retry,
                    output_summary=summary,
                    failure=None,
                ),
                result,
            )

        failure = PipelineFailure(
            stage_name=name,
            error_type=type(last_exc).__name__,
            error_message=str(last_exc),
            retries_attempted=retry - 1,
            timestamp=end,
        )
        log.error("[AMLS] Stage %s FAILED after %d retries: %s: %s",
                  name, retry - 1, type(last_exc).__name__, last_exc)
        return (
            PipelineStage(
                name=name,
                state=PipelineState.FAILED,
                start_time=start,
                end_time=end,
                duration_ms=duration,
                retry_count=retry - 1,
                output_summary="",
                failure=failure,
            ),
            None,
        )

    def _sleep_retry(self, attempt: int) -> None:
        delay = self._cfg.retry_delay_s * (2 ** (attempt - 1))
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _stage_summary(name: str, result: Optional[Any]) -> str:
        if result is None:
            return "ok"
        if name == STAGE_SNAPSHOT:
            return (f"snapshot_id={getattr(result, 'snapshot_id', '?')} "
                    f"universe={getattr(result, 'universe_size', '?')}")
        if name == STAGE_CLASSIFY:
            pops = getattr(result, "populations", [])
            return f"result_id={getattr(result, 'result_id', '?')} populations={len(pops)}"
        if name == STAGE_DISCOVER:
            chars = getattr(result, "all_characteristics", [])
            return f"report_id={getattr(result, 'report_id', '?')} characteristics={len(chars)}"
        if name == STAGE_CONSENSUS:
            dna = getattr(result, "all_consensus", [])
            return (f"library_id={getattr(result, 'library_id', '?')} "
                    f"total_dna={len(dna)}")
        if name == STAGE_IDR_SYNC:
            return f"records_written={result}"
        if name == STAGE_PIG_REFRESH:
            return "reloaded" if result else "no_adapter"
        if name == STAGE_REPORT:
            return f"state={getattr(result, 'pipeline_state', '?')}"
        return "ok"

    # ═════════════════════════════════════════════════════════════════════════
    # CALENDAR LOGIC
    # ═════════════════════════════════════════════════════════════════════════

    def _calendar_skip_reason(self, date_str: str) -> Optional[str]:
        """Return skip reason string, or None if trading day."""
        try:
            d = _date.fromisoformat(date_str)
        except ValueError:
            return f"invalid date: {date_str}"
        if self._cfg.skip_weekends and d.weekday() >= 5:
            return f"weekend ({d.strftime('%A')})"
        if date_str in self._cfg.holidays:
            return f"NSE holiday ({date_str})"
        return None

    def is_trading_day(self, date_str: Optional[str] = None) -> bool:
        """Return True if *date_str* (default: today) is a trading day."""
        ds = date_str or _today_str()
        return self._calendar_skip_reason(ds) is None

    # ═════════════════════════════════════════════════════════════════════════
    # HISTORY PERSISTENCE
    # ═════════════════════════════════════════════════════════════════════════

    def _load_history(self) -> List[MLSPipelineRun]:
        """Thread-safe lazy load of run history from disk."""
        if self._history_loaded:
            return list(self._history)
        if not self._history_file.exists():
            self._history_loaded = True
            return []
        try:
            raw = json.loads(self._history_file.read_text("utf-8"))
            self._history = [MLSPipelineRun.from_dict(d) for d in raw]
        except Exception as e:
            log.warning("[AMLS] Could not load history: %s", e)
            self._history = []
        self._history_loaded = True
        return list(self._history)

    def _append_history(self, run: MLSPipelineRun) -> None:
        """Append *run* to history and persist atomically."""
        with self._lock:
            self._load_history()
            self._history.append(run)
            # Prune old runs
            cutoff = (_date.today() - timedelta(days=self._cfg.history_days)).isoformat()
            self._history = [r for r in self._history if r.trading_date >= cutoff]
            self._write_history()

    def _write_history(self) -> None:
        """Atomically persist history list to disk."""
        tmp = self._history_file.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps([r.to_dict() for r in self._history], indent=2),
                encoding="utf-8",
            )
            os.replace(str(tmp), str(self._history_file))
        except Exception as e:
            log.error("[AMLS] Failed to persist history: %s", e)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _persist_report(self, date_str: str, tel: PipelineTelemetry) -> None:
        """Write the daily telemetry report to its own file."""
        reports_dir = self._amls_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"AMLS-{date_str.replace('-', '')}.json"
        try:
            report_file.write_text(
                json.dumps(tel.to_dict(), indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.warning("[AMLS] Could not write report file: %s", e)

    # ═════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _compute_statistics(runs: List[MLSPipelineRun]) -> PipelineStatistics:
        if not runs:
            return PipelineStatistics(
                total_runs=0, successful_runs=0, failed_runs=0,
                partial_runs=0, skipped_runs=0, avg_duration_ms=0.0,
                total_dna_updates=0, total_idr_writes=0, total_retries=0,
                success_rate=0.0,
                last_successful_run=None, last_failed_run=None,
            )
        total     = len(runs)
        success_n = sum(1 for r in runs if r.state == PipelineState.SUCCESS)
        failed_n  = sum(1 for r in runs if r.state == PipelineState.FAILED)
        partial_n = sum(1 for r in runs if r.state == PipelineState.PARTIAL)
        skipped_n = sum(1 for r in runs if r.state == PipelineState.SKIPPED)

        durations = [r.total_duration_ms for r in runs
                     if r.total_duration_ms is not None and r.state != PipelineState.SKIPPED]
        avg_dur = sum(durations) / len(durations) if durations else 0.0

        dna_updates  = sum(
            1 for r in runs
            if r.telemetry and r.telemetry.dna_updated
        )
        idr_writes   = sum(
            r.telemetry.repository_writes for r in runs
            if r.telemetry and r.telemetry.repository_writes
        )
        retries      = sum(
            r.telemetry.total_retry_count for r in runs
            if r.telemetry and r.telemetry.total_retry_count
        )
        non_skipped  = total - skipped_n
        rate         = success_n / non_skipped if non_skipped > 0 else 0.0

        success_runs = [r for r in runs if r.state == PipelineState.SUCCESS]
        failed_runs  = [r for r in runs if r.state in (PipelineState.FAILED, PipelineState.PARTIAL)]

        return PipelineStatistics(
            total_runs=total,
            successful_runs=success_n,
            failed_runs=failed_n,
            partial_runs=partial_n,
            skipped_runs=skipped_n,
            avg_duration_ms=avg_dur,
            total_dna_updates=dna_updates,
            total_idr_writes=idr_writes,
            total_retries=retries,
            success_rate=rate,
            last_successful_run=success_runs[-1].trading_date if success_runs else None,
            last_failed_run=failed_runs[-1].trading_date if failed_runs else None,
        )


# ─── module-level helper ─────────────────────────────────────────────────────

def _skipped_stage(name: str, reason: str) -> PipelineStage:
    now = _now_iso()
    return PipelineStage(
        name=name,
        state=PipelineState.SKIPPED,
        start_time=now,
        end_time=now,
        duration_ms=0.0,
        retry_count=0,
        output_summary=reason,
        failure=None,
    )
