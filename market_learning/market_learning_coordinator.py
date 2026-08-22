"""
market_learning_coordinator.py — MarketLearningCoordinator.

Single orchestration layer for every market-learning activity in IIOS.

Responsibilities:
    Coordinate end-of-day learning in a fixed, deterministic stage order.
    Execute each stage and collect per-stage telemetry.
    Isolate stage failures so one failure never aborts remaining stages.
    Refresh institutional knowledge (IDR) and platform intelligence (PIG)
    after each pipeline run.
    Maintain an auditable run history on disk.

Explicitly NOT responsible for:
    Creating strategies, DNA, or any domain objects.
    Changing PMCI, CDS, or MLS algorithms.
    Modifying thresholds, risk limits, or trading rules.
    Running any analysis other than orchestrating existing modules.

Pipeline order (fixed):
    Stage 1  Strategy Learning      → LearningEngine.learn(trades)
    Stage 2  AMLS                   → AutonomousMarketLearningScheduler.run_pipeline()
    Stage 3  DNA Reinforcement      → DNAReinforcementEngine.process_batch()
    Stage 4  IDR Refresh            → IDRRepository.statistics()
    Stage 5  PIG Refresh            → PIGTradingAdapter.reload_library()
    Stage 6  Learning Summary       → compile telemetry → persist history

Failure policy:
    Every stage is wrapped in an independent try/except.
    A failed stage records its error in LearningStage.error and continues
    to the next stage. The final health is:
        HEALTHY  — all enabled stages succeeded
        DEGRADED — one or more stages failed but pipeline finished
        FAILED   — reserved for future use (currently not raised)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import date as _date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .mlc_config import MLCConfig
from .mlc_models import (
    LearningHealth,
    LearningRun,
    LearningSummary,
    LearningStage,
    LearningStageStatus,
    LearningStageType,
    LearningTelemetry,
    MLCError,
    MLCStageError,
    _now_iso,
    make_run_id,
)

log = logging.getLogger(__name__)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _today() -> str:
    return _date.today().isoformat()


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Attribute-or-dict accessor; tries all keys in order."""
    for key in keys:
        if isinstance(obj, dict):
            val = obj.get(key)
        else:
            val = getattr(obj, key, None)
        if val is not None:
            return val
    return default


class MarketLearningCoordinator:
    """
    Single orchestration layer for all IIOS market-learning activities.

    Usage::

        mlc = MarketLearningCoordinator(
            amls=self.amls,
            dre=self.dre,
            idr=self.idr,
            pig_adapter=self.pig_adapter,
            learning_engine=self.learning_engine,
        )

        # In _do_eod_learning():
        run = mlc.run_learning_pipeline(closed_trades)
        log.info("[MLC] %s health=%s stages_ok=%d",
                 run.run_id, run.health.value, run.stages_ok)
    """

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(
        self,
        amls:            Optional[Any] = None,   # AutonomousMarketLearningScheduler
        dre:             Optional[Any] = None,   # DNAReinforcementEngine
        idr:             Optional[Any] = None,   # IDRRepository
        pig_adapter:     Optional[Any] = None,   # PIGTradingAdapter
        learning_engine: Optional[Any] = None,   # LearningEngine
        config:          Optional[MLCConfig] = None,
    ) -> None:
        self._amls            = amls
        self._dre             = dre
        self._idr             = idr
        self._pig_adapter     = pig_adapter
        self._learning_engine = learning_engine
        self._config          = config or MLCConfig()
        self._lock            = threading.Lock()
        self._history:        List[Dict[str, Any]] = []
        self._last_run:       Optional[LearningRun] = None

        # Ensure history directory exists
        try:
            Path(self._config.history_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as _dir_exc:
            log.debug("[MLC] Could not create history dir: %s", _dir_exc)

        # Load existing history from disk
        self._load_history()

        log.info(
            "[MLC] MarketLearningCoordinator ready — "
            "amls=%s dre=%s idr=%s pig=%s le=%s",
            self._amls is not None,
            self._dre is not None,
            self._idr is not None,
            self._pig_adapter is not None,
            self._learning_engine is not None,
        )

    # ── Primary API ───────────────────────────────────────────────────────────

    def run_learning_pipeline(
        self,
        trades:      Optional[List[Any]] = None,
        pig_results: Optional[Dict[str, Any]] = None,
    ) -> LearningRun:
        """
        Execute the complete market-learning pipeline for today.

        Parameters
        ----------
        trades :
            List of closed OrderRecord / trade objects from today's session.
            Passed to Strategy Learning (Stage 1) and DNA Reinforcement (Stage 3).
            May be empty — pipeline still runs for market-data updates.
        pig_results :
            Optional dict mapping order_id → PlatformIntelligence (from PIG query
            at decision time). Needed for full DRE alignment calculation.
            If absent, DRE processes trades with minimal PMCI context.

        Returns
        -------
        LearningRun
            Always returned — even if stages fail. Callers must not assume success.
        """
        trading_date = _today()
        run_id       = make_run_id(trading_date)
        started_at   = _now_iso()
        t0           = time.monotonic()

        trades_list: List[Any] = list(trades or [])

        log.info(
            "[MLC] Starting pipeline: run_id=%s date=%s trades=%d",
            run_id, trading_date, len(trades_list),
        )

        run = LearningRun(
            run_id       = run_id,
            trading_date = trading_date,
            started_at   = started_at,
        )

        tel = LearningTelemetry()

        # ── Stage 1: Strategy Learning ────────────────────────────────────────
        s1 = self._make_stage(LearningStageType.STRATEGY_LEARNING, "strategy_learning")
        run.stages.append(s1)
        if not self._config.strategy_learning_enabled or self._learning_engine is None:
            reason = "disabled" if not self._config.strategy_learning_enabled else "no_learning_engine"
            s1.mark_skipped(reason)
            log.debug("[MLC][strategy_learning] Skipped: %s", reason)
        else:
            s1.mark_start()
            try:
                self._learning_engine.learn(trades_list)
                tel.strategy_learning_ran = True
                tel.trades_processed      = len(trades_list)
                s1.mark_complete({"trades_processed": len(trades_list)})
                log.info("[MLC][strategy_learning] ✓ trades=%d", len(trades_list))
            except Exception as _sl_exc:
                s1.mark_failed(str(_sl_exc))
                log.warning("[MLC][strategy_learning] ✗ %s", _sl_exc)

        # ── Stage 2: AMLS ─────────────────────────────────────────────────────
        s2 = self._make_stage(LearningStageType.AMLS, "amls")
        run.stages.append(s2)
        if not self._config.amls_enabled or self._amls is None:
            reason = "disabled" if not self._config.amls_enabled else "no_amls"
            s2.mark_skipped(reason)
            log.debug("[MLC][amls] Skipped: %s", reason)
        else:
            s2.mark_start()
            try:
                amls_run = self._amls.run_pipeline()
                amls_tel = amls_run.telemetry
                dna_upd  = bool(amls_tel.dna_updated)    if amls_tel else False
                repo_w   = int(amls_tel.repository_writes) if amls_tel else 0
                gw_ref   = bool(amls_tel.gateway_refreshed) if amls_tel else False
                tel.amls_ran       = True
                tel.dna_updated    = dna_upd
                tel.repository_updates = repo_w
                tel.gateway_refresh    = gw_ref
                tel.amls_duration_ms   = float(amls_run.total_duration_ms or 0.0)
                s2.mark_complete({
                    "state":        amls_run.state.value,
                    "dna_updated":  dna_upd,
                    "repo_writes":  repo_w,
                    "pig_refresh":  gw_ref,
                    "duration_ms":  tel.amls_duration_ms,
                })
                log.info(
                    "[MLC][amls] ✓ state=%s dna_updated=%s repo_writes=%d pig_refresh=%s",
                    amls_run.state.value, dna_upd, repo_w, gw_ref,
                )
            except Exception as _amls_exc:
                s2.mark_failed(str(_amls_exc))
                log.warning("[MLC][amls] ✗ %s", _amls_exc)

        # ── Stage 3: DNA Reinforcement (DRE) ──────────────────────────────────
        s3 = self._make_stage(LearningStageType.DNA_REINFORCEMENT, "dna_reinforcement")
        run.stages.append(s3)
        if not self._config.dre_enabled or self._dre is None:
            reason = "disabled" if not self._config.dre_enabled else "no_dre"
            s3.mark_skipped(reason)
            log.debug("[MLC][dna_reinforcement] Skipped: %s", reason)
        else:
            s3.mark_start()
            try:
                reinforcements = self._run_dre_stage(trades_list, pig_results or {})
                n_reinforced = len([r for r in reinforcements
                                    if hasattr(r, "reinforcement_type")
                                    and str(getattr(r, "reinforcement_type", "")).upper()
                                       not in ("INSUFFICIENT_EVIDENCE", "NEUTRAL")])
                tel.dre_ran             = True
                tel.dre_trades_attempted = len(trades_list)
                tel.dna_reinforced      = n_reinforced
                s3.mark_complete({
                    "trades_attempted":  len(trades_list),
                    "reinforcements":    len(reinforcements),
                    "dna_reinforced":    n_reinforced,
                })
                log.info(
                    "[MLC][dna_reinforcement] ✓ trades=%d reinforcements=%d active=%d",
                    len(trades_list), len(reinforcements), n_reinforced,
                )
            except Exception as _dre_exc:
                s3.mark_failed(str(_dre_exc))
                log.warning("[MLC][dna_reinforcement] ✗ %s", _dre_exc)

        # ── Stage 4: IDR Refresh ──────────────────────────────────────────────
        s4 = self._make_stage(LearningStageType.IDR_REFRESH, "idr_refresh")
        run.stages.append(s4)
        if not self._config.idr_refresh_enabled or self._idr is None:
            reason = "disabled" if not self._config.idr_refresh_enabled else "no_idr"
            s4.mark_skipped(reason)
            log.debug("[MLC][idr_refresh] Skipped: %s", reason)
        else:
            s4.mark_start()
            try:
                stats = self._idr.statistics()
                total_dna = int(_get(stats, "total_dna", "dna_count", default=0))
                tel.idr_total_dna    = total_dna
                tel.knowledge_generated = (
                    tel.repository_updates + tel.dna_reinforced
                )
                s4.mark_complete({
                    "total_dna":     total_dna,
                    "dna_updated":   tel.dna_updated,
                    "dna_reinforced": tel.dna_reinforced,
                })
                log.info("[MLC][idr_refresh] ✓ total_dna=%d", total_dna)
            except Exception as _idr_exc:
                s4.mark_failed(str(_idr_exc))
                log.warning("[MLC][idr_refresh] ✗ %s", _idr_exc)

        # ── Stage 5: PIG Refresh ──────────────────────────────────────────────
        s5 = self._make_stage(LearningStageType.PIG_REFRESH, "pig_refresh")
        run.stages.append(s5)
        # Skip PIG refresh if AMLS already refreshed it (avoid duplicate reload)
        _amls_already_refreshed = tel.amls_ran and tel.gateway_refresh
        if not self._config.pig_refresh_enabled or self._pig_adapter is None:
            reason = "disabled" if not self._config.pig_refresh_enabled else "no_pig_adapter"
            s5.mark_skipped(reason)
            log.debug("[MLC][pig_refresh] Skipped: %s", reason)
        elif _amls_already_refreshed:
            s5.mark_skipped("already_refreshed_by_amls")
            log.debug("[MLC][pig_refresh] Skipped: already refreshed by AMLS Stage 6")
        else:
            s5.mark_start()
            try:
                reloaded = self._pig_adapter.reload_library()
                tel.gateway_refresh = True
                s5.mark_complete({"reloaded": reloaded})
                log.info("[MLC][pig_refresh] ✓ reloaded=%s", reloaded)
            except Exception as _pig_exc:
                s5.mark_failed(str(_pig_exc))
                log.warning("[MLC][pig_refresh] ✗ %s", _pig_exc)

        # ── Stage 6: Summary ──────────────────────────────────────────────────
        s6 = self._make_stage(LearningStageType.SUMMARY, "summary")
        run.stages.append(s6)
        s6.mark_start()
        try:
            n_ok      = sum(1 for s in run.stages[:-1] if s.succeeded)
            n_failed  = sum(1 for s in run.stages[:-1] if s.failed)
            n_skipped = sum(1 for s in run.stages[:-1] if s.status == LearningStageStatus.SKIPPED)
            health = (LearningHealth.HEALTHY  if n_failed == 0
                      else LearningHealth.DEGRADED)
            s6.mark_complete({
                "stages_ok":      n_ok,
                "stages_failed":  n_failed,
                "stages_skipped": n_skipped,
                "health":         health.value,
            })
        except Exception as _sum_exc:
            s6.mark_failed(str(_sum_exc))
            health = LearningHealth.DEGRADED

        # ── Finalise run ──────────────────────────────────────────────────────
        run.ended_at          = _now_iso()
        run.total_duration_ms = (time.monotonic() - t0) * 1000.0
        run.telemetry         = tel
        run.health            = health

        with self._lock:
            self._last_run = run

        # Persist history (non-critical)
        try:
            self._append_history(run)
        except Exception as _hist_exc:
            log.debug("[MLC] History write failed: %s", _hist_exc)

        log.info(
            "[MLC] Pipeline complete: run_id=%s health=%s duration_ms=%.0f "
            "stages_ok=%d stages_failed=%d stages_skipped=%d",
            run.run_id, run.health.value, run.total_duration_ms,
            run.stages_ok, run.stages_failed, run.stages_skipped,
        )
        return run

    # ── Standalone stage APIs ─────────────────────────────────────────────────

    def run_amls(self) -> Any:
        """
        Invoke the AMLS pipeline standalone, outside the full EOD pipeline.

        Returns the MLSPipelineRun object from AMLS.
        Raises MLCError if AMLS is not available.
        """
        if self._amls is None:
            raise MLCError("AMLS is not configured in this coordinator")
        return self._amls.run_pipeline()

    def run_reinforcement(
        self,
        trades:      List[Any],
        pig_results: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """
        Invoke DRE standalone for a list of closed trades.

        Returns a flat list of DNAReinforcement records.
        Raises MLCError if DRE is not available.
        """
        if self._dre is None:
            raise MLCError("DRE is not configured in this coordinator")
        return self._run_dre_stage(trades, pig_results or {})

    # ── Query API ─────────────────────────────────────────────────────────────

    def status(self) -> LearningSummary:
        """
        Return a summary of the most recently completed pipeline run.

        Returns a zero-state summary if no run has been performed yet.
        """
        with self._lock:
            last = self._last_run

        if last is None:
            return LearningSummary(
                run_id            = "none",
                trading_date      = _today(),
                stages_total      = 0,
                stages_ok         = 0,
                stages_failed     = 0,
                stages_skipped    = 0,
                total_duration_ms = 0.0,
                pipeline_healthy  = True,
                health            = LearningHealth.HEALTHY,
                telemetry         = None,
            )

        return LearningSummary(
            run_id            = last.run_id,
            trading_date      = last.trading_date,
            stages_total      = len(last.stages),
            stages_ok         = last.stages_ok,
            stages_failed     = last.stages_failed,
            stages_skipped    = last.stages_skipped,
            total_duration_ms = last.total_duration_ms or 0.0,
            pipeline_healthy  = last.stages_failed == 0,
            health            = last.health,
            telemetry         = last.telemetry,
        )

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return the last `limit` historical pipeline run records as dicts.

        Sorted newest-first (index 0 = most recent run).
        """
        with self._lock:
            runs = list(self._history)
        runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)
        return runs[:limit]

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics across all runs in history.
        """
        with self._lock:
            hist = list(self._history)

        total_runs  = len(hist)
        if total_runs == 0:
            return {
                "total_runs":          0,
                "healthy_runs":        0,
                "degraded_runs":       0,
                "total_trades":        0,
                "total_reinforced":    0,
                "avg_duration_ms":     0.0,
                "last_run_date":       None,
            }

        healthy    = sum(1 for r in hist if r.get("health") == "HEALTHY")
        degraded   = sum(1 for r in hist if r.get("health") == "DEGRADED")
        all_trades = sum(
            (r.get("telemetry") or {}).get("trades_processed", 0)
            for r in hist
        )
        all_reinforced = sum(
            (r.get("telemetry") or {}).get("dna_reinforced", 0)
            for r in hist
        )
        durations = [r.get("total_duration_ms") or 0.0 for r in hist]
        avg_ms    = sum(durations) / len(durations) if durations else 0.0

        hist_sorted = sorted(hist, key=lambda r: r.get("trading_date", ""), reverse=True)

        return {
            "total_runs":       total_runs,
            "healthy_runs":     healthy,
            "degraded_runs":    degraded,
            "total_trades":     all_trades,
            "total_reinforced": all_reinforced,
            "avg_duration_ms":  round(avg_ms, 1),
            "last_run_date":    hist_sorted[0].get("trading_date") if hist_sorted else None,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_stage(stage_type: LearningStageType, name: str) -> LearningStage:
        return LearningStage(stage_type=stage_type, name=name)

    def _run_dre_stage(
        self,
        trades:      List[Any],
        pig_results: Dict[str, Any],
    ) -> List[Any]:
        """
        Build the batch of (trade, pmci_result, ca_pmci, cds) tuples and
        submit to DRE.process_batch().

        Trades without a PIG/PMCI result are skipped with a debug log so that
        DRE never receives a None pmci_result (which would raise DREInputError).
        """
        items = []
        for trade in trades:
            order_id = str(_get(trade, "order_id", "trade_id", default=""))
            pi       = pig_results.get(order_id)
            if pi is None:
                log.debug(
                    "[MLC][dna_reinforcement] No PIG result for trade %s "
                    "— skipping DRE for this trade.",
                    order_id,
                )
                continue
            # Extract PMCI, CA-PMCI, CDS from the PlatformIntelligence object
            pmci    = _get(pi, "pmci_result",    default=None)
            ca_pmci = _get(pi, "ca_pmci_result", default=None)
            cds     = _get(pi, "cds_scores",     default=None)
            if pmci is None:
                log.debug(
                    "[MLC][dna_reinforcement] PIG result for trade %s has no "
                    "pmci_result — skipping DRE.",
                    order_id,
                )
                continue
            items.append((trade, pmci, ca_pmci, cds))

        if not items:
            log.debug(
                "[MLC][dna_reinforcement] No trades with PMCI results — "
                "DRE batch is empty (O-ADD-003: PMCI not yet persisted at execution time)."
            )
            return []

        return self._dre.process_batch(items)

    # ── History persistence ────────────────────────────────────────────────────

    def _append_history(self, run: LearningRun) -> None:
        """Append run to in-memory history and atomically write to disk."""
        run_dict = run.to_dict()

        with self._lock:
            self._history.append(run_dict)
            # Evict oldest entries beyond the cap
            if len(self._history) > self._config.max_history_runs:
                self._history = self._history[-self._config.max_history_runs:]
            snapshot = list(self._history)

        path = Path(self._config.history_path)
        tmp  = str(path) + ".tmp"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(snapshot, fh, indent=2, default=str)
            os.replace(tmp, str(path))
        except Exception as _write_exc:
            log.debug("[MLC] History write failed: %s", _write_exc)
            try:
                os.unlink(tmp)
            except Exception:
                pass

    def _load_history(self) -> None:
        """Load history from disk into memory (silent on missing file)."""
        path = Path(self._config.history_path)
        if not path.exists():
            return
        try:
            with open(str(path), encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                with self._lock:
                    self._history = data[-self._config.max_history_runs:]
                log.debug("[MLC] Loaded %d history run(s) from disk.", len(self._history))
        except Exception as _load_exc:
            log.debug("[MLC] Could not load history: %s", _load_exc)
