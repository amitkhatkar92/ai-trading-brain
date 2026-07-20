"""
iios/execution/analytics/snapshot/analytics_snapshot_builder.py
===============================================================
AnalyticsSnapshotBuilder — builds ExecutionAnalyticsSnapshot from
validated M1/M2/M3/M4 analytics sources.

Accepted sources:
  - M1 AnalyticsSession + AnalyticsStatistics     (lifecycle)
  - M2 AnalyticsSnapshot + EngineAnalyticsStatistics (engine)
  - M3 PerformanceAnalyticsReport                 (performance)
  - M4 PredictionReport                           (predictive)

Rejection criteria:
  - Missing required identifiers
  - Duplicate snapshot IDs
  - Incomplete analytics state
  - Invalid lifecycle state
  - Invalid forecast state

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .analytics_snapshot_metadata import AnalyticsMetadata, AuditMetadata
from .analytics_snapshot_validation import AnalyticsSnapshotValidator
from .constants import (
    ACTOR_BUILDER,
    BUILDER_SYSTEM_ID,
    SNAPSHOT_FRAMEWORK_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    AnalyticsHealth,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsStatus,
    SnapshotLifecycleState,
    health_from_score,
)
from .exceptions import SnapshotBuildError, SnapshotEngineNotRunningError
from .execution_analytics_snapshot import (
    BenchmarkSummary,
    ConfidenceSummary,
    ExecutionAnalyticsSnapshot,
    HistoricalSummary,
    PerformanceKPIs,
    PerformanceScorecard,
    PerformanceSummary,
    PredictionSummary,
    SnapshotAnalyticsStatistics,
    SnapshotCapacityForecast,
    SnapshotForecastSummary,
    SnapshotRiskForecast,
    TrendSummary,
)

_log = get_logger(__name__)

_RUNNING   = frozenset({EngineState.RUNNING, "running"})
_VALID_M1  = {"ACTIVE", "active", "READY", "ready", "COMPLETED", "completed"}


def _safe(obj: Any, attr: str, default: Any = None) -> Any:
    """Safe getattr with a default."""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def _safe_call(obj: Any, method: str, default: Any = None) -> Any:
    """Safe getattr + call."""
    try:
        fn = getattr(obj, method, None)
        if callable(fn):
            return fn()
        return default
    except Exception:
        return default


class AnalyticsSnapshotBuilder(LifecycleAwareMixin):
    """
    Constructs ExecutionAnalyticsSnapshot from validated analytics sources.

    Raises SnapshotBuildError for invalid or incomplete inputs.
    Thread-safe.  Must be started before use.
    """

    def __init__(self) -> None:
        super().__init__()
        self._validator = AnalyticsSnapshotValidator()

    def _on_start(self) -> None:
        _log.info("AnalyticsSnapshotBuilder started.", system_id=BUILDER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("AnalyticsSnapshotBuilder stopped.", system_id=BUILDER_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotEngineNotRunningError()

    # ── Source extraction helpers ─────────────────────────────────────────────

    def _extract_ids_from_session(self, session: Any) -> dict:
        """Extract identifiers from an M1 AnalyticsSession."""
        return {
            "analytics_session_id": _safe(session, "_session_id", "") or
                                    _safe(session, "session_id", ""),
            "execution_session_id": _safe(session, "_execution_session_id", "") or
                                    _safe(session, "execution_session_id", ""),
            "workflow_id":          _safe(session, "_workflow_id", "") or
                                    _safe(session, "workflow_id", ""),
            "portfolio_id":         _safe(session, "_portfolio_id", "") or
                                    _safe(session, "portfolio_id", ""),
            "strategy_id":          _safe(session, "_strategy_id", "") or
                                    _safe(session, "strategy_id", ""),
            "analytics_scope":      _safe(session, "_analytics_scope",
                                         AnalyticsScope.EXECUTION) or
                                    _safe(session, "analytics_scope",
                                         AnalyticsScope.EXECUTION),
            "analytics_mode":       _safe(session, "_analytics_mode",
                                         AnalyticsMode.ON_DEMAND) or
                                    _safe(session, "analytics_mode",
                                         AnalyticsMode.ON_DEMAND),
        }

    def _extract_performance(self, perf_report: Any) -> tuple:
        """Extract M3 performance data → (PerformanceSummary, PerformanceKPIs, PerformanceScorecard, TrendSummary, BenchmarkSummary, float)."""
        if perf_report is None:
            return None, None, None, None, None, 0.5

        # ── PerformanceSummary from KPIReport ─────────────────────────────────
        kpi_report = _safe(perf_report, "kpi_report")
        kpi_values: dict = {}
        if kpi_report is not None:
            raw = _safe(kpi_report, "kpi_values", ())
            if raw is None:
                raw = ()
            # kpi_values is a tuple of KPIValue objects with .kpi_type.value and .value
            for kv in raw:
                try:
                    ktype = _safe(_safe(kv, "kpi_type"), "value", None) or str(_safe(kv, "kpi_type", "unknown"))
                    kval  = float(_safe(kv, "value", 0.0) or 0.0)
                    kpi_values[ktype] = kval
                except (TypeError, ValueError):
                    pass

        perf_summary = PerformanceSummary(
            total_executions      = int(kpi_values.get("total_executions", 0)),
            successful_executions = int(kpi_values.get("successful_executions", 0)),
            success_rate          = min(1.0, max(0.0, float(kpi_values.get("success_rate", 0.0)))),
            avg_execution_time_ms = max(0.0, float(kpi_values.get("avg_execution_time_ms", 0.0))),
            total_pnl             = float(kpi_values.get("total_pnl", 0.0)),
            win_rate              = min(1.0, max(0.0, float(kpi_values.get("win_rate", 0.0)))),
            sharpe_ratio          = float(kpi_values.get("sharpe_ratio", 0.0)),
            max_drawdown          = abs(float(kpi_values.get("max_drawdown", 0.0))),
            avg_slippage          = abs(float(kpi_values.get("avg_slippage", 0.0))),
            fill_rate             = min(1.0, max(0.0, float(kpi_values.get("fill_rate", 1.0)))),
        )

        perf_kpis = PerformanceKPIs(
            execution_success_rate = perf_summary.success_rate,
            avg_latency_ms         = perf_summary.avg_execution_time_ms,
            fill_rate              = perf_summary.fill_rate,
            slippage_rate          = perf_summary.avg_slippage,
            kpi_values             = kpi_values,
        )

        # ── PerformanceScorecard ──────────────────────────────────────────────
        sc = _safe(perf_report, "scorecard")
        perf_scorecard = None
        perf_confidence = 0.5
        if sc is not None:
            grade_obj = _safe(sc, "grade")
            grade_str = grade_obj.value if hasattr(grade_obj, "value") else str(grade_obj)
            overall = float(_safe(sc, "overall_score", 0.5) or 0.5)
            # kpi_scores is already a plain dict {str: float}
            kpi_scores_raw = _safe(sc, "kpi_scores", {}) or {}
            kpi_scores = {str(k): float(v) for k, v in kpi_scores_raw.items()} if isinstance(kpi_scores_raw, dict) else {}
            perf_scorecard = PerformanceScorecard(
                overall_score    = min(1.0, max(0.0, overall)),
                execution_score  = min(1.0, max(0.0, float(kpi_scores.get("execution_success_rate", overall)))),
                risk_score       = min(1.0, max(0.0, float(kpi_scores.get("risk_rule_effectiveness", overall)))),
                efficiency_score = min(1.0, max(0.0, float(kpi_scores.get("portfolio_efficiency", overall)))),
                grade            = grade_str,
                kpi_scores       = kpi_scores,
            )
            perf_confidence = perf_scorecard.overall_score

        # ── TrendSummary ──────────────────────────────────────────────────────
        trend_summary = None
        trends = _safe(perf_report, "trends")
        if trends:
            trend_values = [str(_safe(t, "trend", "unknown") or "unknown") for t in trends]
            dominant = max(set(trend_values), key=trend_values.count) if trend_values else "unknown"
            trend_summary = TrendSummary(
                dominant_trend  = dominant,
                trend_count     = len(trend_values),
                improving_count = trend_values.count("improving"),
                degrading_count = trend_values.count("degrading"),
                stable_count    = trend_values.count("stable"),
                volatile_count  = trend_values.count("volatile"),
            )

        # ── BenchmarkSummary ──────────────────────────────────────────────────
        bm_report = _safe(perf_report, "benchmark_report")
        bench_summary = None
        if bm_report is not None:
            overall_bm  = float(_safe(bm_report, "overall_score", 0.5) or 0.5)
            comps_raw   = _safe(bm_report, "comparisons", []) or []
            comparisons = {}
            within = 0
            exceeding = 0
            for comp in comps_raw:
                kpi_name = str(_safe(_safe(comp, "kpi_type"), "value", "unknown") or "unknown")
                actual   = float(_safe(comp, "actual_value", 0.0) or 0.0)
                comparisons[kpi_name] = actual
                status = _safe(_safe(comp, "status"), "value", "ok") or "ok"
                if status in {"warning", "critical"}:
                    exceeding += 1
                else:
                    within += 1
            bench_summary = BenchmarkSummary(
                overall_score        = min(1.0, max(0.0, overall_bm)),
                benchmark_count      = len(comps_raw),
                within_threshold     = within,
                exceeding_threshold  = exceeding,
                comparisons          = comparisons,
            )

        return perf_summary, perf_kpis, perf_scorecard, trend_summary, bench_summary, perf_confidence

    def _extract_predictions(self, pred_report: Any) -> tuple:
        """Extract M4 prediction data → (PredictionSummary, SnapshotForecastSummary, SnapshotCapacityForecast, SnapshotRiskForecast, float)."""
        if pred_report is None:
            return None, None, None, None, 0.5

        forecast_count  = int(_safe(pred_report, "forecast_count", 0) or 0)

        # ForecastSummary
        m4_fs = _safe(pred_report, "forecast_summary")
        total_f     = forecast_count
        dominant    = "unknown"
        avg_conf    = 0.5
        horizon_str = "next_hour"
        domain_str  = ""
        if m4_fs is not None:
            total_f     = int(_safe(m4_fs, "total_forecasts", total_f) or total_f)
            trend_obj   = _safe(m4_fs, "dominant_trend")
            dominant    = trend_obj.value if hasattr(trend_obj, "value") else str(trend_obj)
            avg_conf    = float(_safe(m4_fs, "avg_confidence", 0.5) or 0.5)
            dom_obj     = _safe(pred_report, "domain")
            domain_str  = dom_obj.value if hasattr(dom_obj, "value") else str(dom_obj or "")
            hor_obj     = _safe(pred_report, "horizon")
            horizon_str = hor_obj.value if hasattr(hor_obj, "value") else str(hor_obj or "next_hour")

        snap_fc_summary = SnapshotForecastSummary(
            total_forecasts  = total_f,
            dominant_trend   = dominant,
            forecast_horizon = horizon_str,
            avg_confidence   = min(1.0, max(0.0, avg_conf)),
            forecast_domain  = domain_str,
        )

        # PredictionSummary
        hi_count = int(_safe(m4_fs, "high_confidence_count", 0) or 0) if m4_fs else 0
        lo_count = int(_safe(m4_fs, "low_confidence_count", 0) or 0) if m4_fs else 0
        pred_summary = PredictionSummary(
            total_predictions     = total_f,
            avg_confidence        = avg_conf,
            high_confidence_count = hi_count,
            low_confidence_count  = lo_count,
            prediction_domains    = (domain_str,) if domain_str else (),
        )

        # CapacityForecast
        snap_cap = None
        m4_cap = _safe(pred_report, "capacity_forecast")
        if m4_cap is not None:
            cap_rl  = _safe(m4_cap, "risk_level")
            cap_str = cap_rl.value if hasattr(cap_rl, "value") else str(cap_rl or "minimal")
            snap_cap = SnapshotCapacityForecast(
                current_utilization    = min(1.0, max(0.0, float(_safe(m4_cap, "current_utilization", 0.0) or 0.0))),
                forecasted_utilization = min(1.0, max(0.0, float(_safe(m4_cap, "forecasted_utilization", 0.0) or 0.0))),
                capacity_headroom      = min(1.0, max(0.0, float(_safe(m4_cap, "capacity_headroom", 1.0) or 1.0))),
                bottleneck_risk        = min(1.0, max(0.0, float(_safe(m4_cap, "bottleneck_risk", 0.0) or 0.0))),
                risk_level             = cap_str,
            )

        # RiskForecast
        snap_risk = None
        m4_risk = _safe(pred_report, "risk_forecast")
        if m4_risk is not None:
            risk_rl  = _safe(m4_risk, "risk_level")
            risk_str = risk_rl.value if hasattr(risk_rl, "value") else str(risk_rl or "minimal")
            cf_raw   = _safe(m4_risk, "contributing_factors", ()) or ()
            mi_raw   = _safe(m4_risk, "mitigation_indicators", ()) or ()
            snap_risk = SnapshotRiskForecast(
                risk_level            = risk_str,
                risk_score            = min(1.0, max(0.0, float(_safe(m4_risk, "risk_score", 0.0) or 0.0))),
                contributing_factors  = tuple(str(f) for f in cf_raw),
                mitigation_indicators = tuple(str(m) for m in mi_raw),
                confidence            = min(1.0, max(0.0, float(_safe(m4_risk, "confidence", 0.5) or 0.5))),
            )

        pred_confidence = avg_conf
        return pred_summary, snap_fc_summary, snap_cap, snap_risk, pred_confidence

    def _extract_statistics(self, m1_stats: Any, m2_stats: Any, m3_stats: Any, m4_stats: Any) -> SnapshotAnalyticsStatistics:
        total = 0
        success = 0
        failed  = 0
        t_ms    = 0.0
        samples = 0
        perf_cycles = 0
        pred_cycles = 0

        for src in (m1_stats, m2_stats):
            if src is None:
                continue
            total   += int(_safe(src, "total_cycles", 0) or _safe(src, "prediction_cycles", 0) or 0)
            failed  += int(_safe(src, "failed_cycles", 0) or 0)
            t_ms    += float(_safe(src, "avg_processing_time_ms", 0.0) or 0.0)
            samples += 1

        if m3_stats is not None:
            c = int(_safe(m3_stats, "performance_cycles", 0) or 0)
            perf_cycles += c
            total  += c
            failed += int(_safe(m3_stats, "failed_cycles", 0) or 0)
            t_ms   += float(_safe(m3_stats, "avg_processing_time_ms", 0.0) or 0.0)
            samples += 1

        if m4_stats is not None:
            c = int(_safe(m4_stats, "prediction_cycles", 0) or 0)
            pred_cycles += c
            total  += c
            failed += int(_safe(m4_stats, "failed_cycles", 0) or 0)
            t_ms   += float(_safe(m4_stats, "avg_processing_time_ms", 0.0) or 0.0)
            samples += 1

        success = max(0, total - failed)
        avg_ms  = t_ms / samples if samples else 0.0
        sr      = success / total if total else 1.0

        return SnapshotAnalyticsStatistics(
            total_cycles       = total,
            successful_cycles  = success,
            failed_cycles      = failed,
            avg_cycle_time_ms  = avg_ms,
            total_events       = 0,
            performance_cycles = perf_cycles,
            prediction_cycles  = pred_cycles,
            success_rate       = min(1.0, max(0.0, sr)),
        )

    # ── Public build method ───────────────────────────────────────────────────

    def build(
        self,
        *,
        # M1 — Analytics Lifecycle
        analytics_session:    Optional[Any] = None,
        analytics_statistics: Optional[Any] = None,
        # M2 — Analytics Engine
        engine_snapshot:      Optional[Any] = None,
        engine_statistics:    Optional[Any] = None,
        # M3 — Performance Analytics
        performance_report:   Optional[Any] = None,
        performance_stats:    Optional[Any] = None,
        # M4 — Predictive Intelligence
        prediction_report:    Optional[Any] = None,
        predictive_stats:     Optional[Any] = None,
        # Overrides (used when session object unavailable)
        analytics_session_id: str           = "",
        execution_session_id: str           = "",
        workflow_id:          str           = "",
        portfolio_id:         str           = "",
        strategy_id:          str           = "",
        analytics_scope:      Optional[AnalyticsScope] = None,
        analytics_mode:       Optional[AnalyticsMode]  = None,
        analytics_status:     Optional[AnalyticsStatus] = None,
        snapshot_id:          Optional[str] = None,
    ) -> ExecutionAnalyticsSnapshot:
        """
        Build an ExecutionAnalyticsSnapshot from validated analytics sources.

        Raises SnapshotBuildError if required identifiers are missing.
        """
        self._assert_running()
        t0 = time.perf_counter()

        # 1. Resolve identifiers
        ids: dict = {}
        if analytics_session is not None:
            ids = self._extract_ids_from_session(analytics_session)

        sid  = ids.get("analytics_session_id") or analytics_session_id
        eid  = ids.get("execution_session_id") or execution_session_id
        wid  = ids.get("workflow_id")          or workflow_id
        pid  = ids.get("portfolio_id")         or portfolio_id
        stid = ids.get("strategy_id")          or strategy_id
        scope = ids.get("analytics_scope")     or analytics_scope or AnalyticsScope.EXECUTION
        mode  = ids.get("analytics_mode")      or analytics_mode  or AnalyticsMode.ON_DEMAND

        # Validate identifiers
        validation = self._validator.validate_build_inputs(
            analytics_session_id = sid,
            execution_session_id = eid,
        )
        if not validation.is_valid:
            raise SnapshotBuildError("; ".join(validation.errors))

        # 2. Extract performance data
        (
            perf_summary, perf_kpis, perf_scorecard,
            trend_summary, bench_summary, perf_confidence,
        ) = self._extract_performance(performance_report)

        # 3. Extract prediction data
        (
            pred_summary, fc_summary, cap_fc, risk_fc, pred_confidence,
        ) = self._extract_predictions(prediction_report)

        # 4. Aggregate statistics
        snap_stats = self._extract_statistics(
            analytics_statistics, engine_statistics,
            performance_stats, predictive_stats,
        )

        # 5. Compute confidence summary
        overall_conf = (perf_confidence + pred_confidence) / 2.0
        conf_summary = ConfidenceSummary(
            overall_confidence     = min(1.0, max(0.0, overall_conf)),
            performance_confidence = min(1.0, max(0.0, perf_confidence)),
            prediction_confidence  = min(1.0, max(0.0, pred_confidence)),
            risk_confidence        = min(1.0, max(0.0,
                                        float(_safe(risk_fc, "confidence", 0.5) if risk_fc else 0.5))),
        )

        # 6. Compute operational health score
        op_health = overall_conf
        if risk_fc is not None:
            op_health = max(0.0, min(1.0, 1.0 - risk_fc.risk_score * 0.5 + overall_conf * 0.5))

        # 7. Build metadata
        build_ms = (time.perf_counter() - t0) * 1_000.0
        sources = tuple(filter(None, [
            "m1:analytics_lifecycle"    if analytics_session  is not None else None,
            "m2:analytics_engine"       if engine_snapshot    is not None else None,
            "m3:performance_analytics"  if performance_report is not None else None,
            "m4:predictive_intelligence" if prediction_report is not None else None,
        ]))
        meta = AnalyticsMetadata(
            source_version    = SNAPSHOT_FRAMEWORK_VERSION,
            build_duration_ms = round(build_ms, 3),
            data_sources      = sources,
        )
        audit = AuditMetadata(
            created_by  = ACTOR_BUILDER,
            created_at  = time.time(),
        )

        # 8. Determine status
        status = analytics_status or AnalyticsStatus.COMPLETED

        # 9. Determine historical summary
        hist_summary = HistoricalSummary(
            data_points     = snap_stats.total_cycles,
            sessions_analyzed = 1 if sid else 0,
        )

        # 10. Assemble snapshot
        snap = ExecutionAnalyticsSnapshot(
            snapshot_id           = snapshot_id or str(uuid.uuid4()),
            snapshot_version      = SNAPSHOT_SCHEMA_VERSION,
            analytics_session_id  = sid,
            execution_session_id  = eid,
            workflow_id           = wid,
            portfolio_id          = pid,
            strategy_id           = stid,
            analytics_scope       = scope,
            analytics_mode        = mode,
            lifecycle_state       = SnapshotLifecycleState.READY,
            analytics_status      = status,
            analytics_health      = health_from_score(op_health),
            performance_summary   = perf_summary,
            performance_kpis      = perf_kpis,
            performance_scorecard = perf_scorecard,
            trend_summary         = trend_summary,
            benchmark_summary     = bench_summary,
            historical_summary    = hist_summary,
            prediction_summary    = pred_summary,
            forecast_summary      = fc_summary,
            confidence_summary    = conf_summary,
            operational_health_score = min(1.0, max(0.0, op_health)),
            capacity_forecast     = cap_fc,
            risk_forecast         = risk_fc,
            analytics_statistics  = snap_stats,
            analytics_metadata    = meta,
            audit_metadata        = audit,
            framework_version     = SNAPSHOT_FRAMEWORK_VERSION,
        )

        return snap
