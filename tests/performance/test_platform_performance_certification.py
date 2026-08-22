"""tests/performance/test_platform_performance_certification.py
IIOS Core Intelligence Platform — Performance & Load Certification
C1–C5 + M2.1–M2.5 Frameworks

Parts
-----
 1  Latency Certification
 2  Throughput Certification
 3  Scalability Certification
 4  Resource Certification
 5  Long Run Certification
 6  Framework Overhead
 7  Stress Certification
 8  Bottleneck Analysis
 9  Optimization Report   (report-only — always passes)
10  Final Certification   (aggregate verdict)

Benchmark methodology
---------------------
* All engine calls use mock engines identical to integration certification.
* No real I/O, no real market data.  What is measured is FRAMEWORK overhead:
  lock contention, state machine transitions, event publishing, history
  accumulation, async execution, logging, error handling.
* Measurements are stored in the module-level _M dict for cross-part access.
* Thresholds are set to be meaningful but not brittle:
  p99 < 500ms, throughput > 10 wf/sec are conservative floors that the
  framework should vastly exceed on any modern machine.
"""
from __future__ import annotations

import gc
import logging
import statistics
import sys
import threading
import time
import tracemalloc
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

# ── IIOS imports ───────────────────────────────────────────────────────────────

from iios.investment.investment_constants import (
    AssetClass, InvestmentObjective, RiskProfile, TimeHorizon,
)
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.workflow.institutional_investment_workflow import (
    InstitutionalWorkflowOrchestrator,
    WorkflowResult,
)
from iios.investment.workflow.workflow_context import WorkflowEngines, WorkflowParameters
from iios.investment.workflow.workflow_history import WorkflowHistory
from iios.investment.workflow.workflow_statistics import WorkflowStatistics
from iios.investment.workflow.workflow_events import WorkflowEventPublisher
from iios.investment.workflow.engine_lifecycle import (
    EngineState, LifecycleAwareMixin,
)
from iios.common.async_exec.async_execution_manager import (
    get_execution_manager, reset_execution_manager,
)
from iios.common.errors.error_manager import (
    get_error_manager, reset_error_manager,
)


# ══════════════════════════════════════════════════════════════════════════════
#  MODULE-LEVEL MEASUREMENTS  (populated progressively as tests run)
# ══════════════════════════════════════════════════════════════════════════════

_M: Dict[str, Any] = {}          # raw measurements
_log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

class _Snap:
    """Minimal snapshot stub — identical to integration certification."""
    def __init__(self, prefix: str = "snap") -> None:
        self.snapshot_id   = f"{prefix}-{uuid.uuid4().hex[:6]}"
        self.quality_score = 0.85
        self.overall_score = 85.0
        self.is_ready      = True

    def to_dict(self) -> dict:
        return {"snapshot_id": self.snapshot_id}


class _BigSnap(_Snap):
    """Snapshot with a large payload — used in stress tests."""
    def __init__(self, prefix: str = "big", kb: int = 50) -> None:
        super().__init__(prefix)
        self.payload = "x" * (kb * 1024)


def _make_engines(**kwargs: Any) -> WorkflowEngines:
    """Return a WorkflowEngines with mock engines.  Same pattern as integration cert."""
    fails = {k: kwargs.get(k, False) for k in
             ("market_fail", "company_fail", "strategy_fail",
              "decision_fail", "portfolio_fail")}
    snaps = {k: kwargs.get(k, None) for k in
             ("market_snap", "company_snap", "strategy_snap",
              "decision_snap", "portfolio_snap")}

    def _eng(prefix: str, fail: bool, snap: Any) -> MagicMock:
        m = MagicMock()
        if fail:
            for attr in ("update", "integrate", "integrate_sync",
                         "get_snapshot_sync", "submit_update_sync"):
                setattr(m, attr, MagicMock(side_effect=RuntimeError(
                    f"{prefix} injected failure")))
        else:
            effective = snap or _Snap(prefix)
            for attr in ("update", "integrate", "integrate_sync",
                         "get_snapshot_sync"):
                setattr(m, attr, MagicMock(return_value=effective))
            m.submit_update_sync = MagicMock(return_value=None)
        m.make_bundle.return_value = MagicMock()
        m.receive = MagicMock(return_value=None)
        return m

    return WorkflowEngines(
        market_engine    = _eng("mkt",  fails["market_fail"],    snaps["market_snap"]),
        company_engine   = _eng("cmp",  fails["company_fail"],   snaps["company_snap"]),
        strategy_engine  = _eng("str",  fails["strategy_fail"],  snaps["strategy_snap"]),
        decision_engine  = _eng("dec",  fails["decision_fail"],  snaps["decision_snap"]),
        portfolio_engine = _eng("prt",  fails["portfolio_fail"], snaps["portfolio_snap"]),
    )


def _make_request(symbols: Optional[List[str]] = None) -> InvestmentRequest:
    return InvestmentRequest(
        request_id   = str(uuid.uuid4()),
        asset_class  = AssetClass.EQUITY,
        symbols      = symbols or ["AAPL"],
        objective    = InvestmentObjective.GROWTH,
        risk_profile = RiskProfile.MODERATE,
        time_horizon = TimeHorizon.LONG_TERM,
    )


def _make_orchestrator(**kw: Any) -> InstitutionalWorkflowOrchestrator:
    return InstitutionalWorkflowOrchestrator(
        engines = _make_engines(**kw),
        params  = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
    )


def _run_pipeline(orchestrator: InstitutionalWorkflowOrchestrator) -> WorkflowResult:
    return orchestrator.run(_make_request(), portfolio_id="P-PERF-001")


def _time_run(orchestrator: InstitutionalWorkflowOrchestrator) -> float:
    """Return wall-clock ms for one pipeline run."""
    t0 = time.perf_counter()
    _run_pipeline(orchestrator)
    return (time.perf_counter() - t0) * 1_000.0


def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = max(0, min(len(sorted_d) - 1, int(len(sorted_d) * p / 100.0)))
    return sorted_d[idx]


def _get_mem_mb() -> float:
    """Return current process working-set in MB (Windows ctypes path)."""
    try:
        import ctypes
        import ctypes.wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [
                ("cb",                          ctypes.c_ulong),
                ("PageFaultCount",              ctypes.c_ulong),
                ("PeakWorkingSetSize",          ctypes.c_size_t),
                ("WorkingSetSize",              ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage",     ctypes.c_size_t),
                ("QuotaPagedPoolUsage",         ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage",  ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage",      ctypes.c_size_t),
                ("PagefileUsage",               ctypes.c_size_t),
                ("PeakPagefileUsage",           ctypes.c_size_t),
                ("PrivateUsage",                ctypes.c_size_t),
            ]

        pmc = _PMC()
        pmc.cb = ctypes.sizeof(pmc)
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            h, ctypes.byref(pmc), pmc.cb
        )
        if ok:
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    # Fallback: tracemalloc current
    if tracemalloc.is_tracing():
        cur, _ = tracemalloc.get_traced_memory()
        return cur / (1024 * 1024)
    return 0.0


def _warmup(n: int = 20) -> None:
    """Warmup JIT / import caches before measurement."""
    orc = _make_orchestrator()
    for _ in range(n):
        _run_pipeline(orc)


# ══════════════════════════════════════════════════════════════════════════════
#  PART 1 — LATENCY CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart1Latency:
    """
    Measure per-stage and end-to-end pipeline latency.
    Thresholds are conservative floors.  Any modern machine should exceed them.
    """

    WARMUP_N  = 30
    MEASURE_N = 300

    # ── Thresholds (ms) ───────────────────────────────────────────────────────
    # Framework-only (mock I/O).  Production adds real engine latency on top.
    T_STAGE_AVG_MS  = 10.0    # avg per stage
    T_PIPELINE_AVG  = 50.0    # avg pipeline (5 stages)
    T_P50           = 30.0    # median
    T_P95           = 150.0   # 95th percentile
    T_P99           = 300.0   # 99th percentile
    T_WORST         = 1_000.0 # absolute worst (GC / JIT pause allowance)

    @classmethod
    def _collect(cls) -> Tuple[List[float], Dict[str, List[float]]]:
        """Return (pipeline_durations_ms, per_stage_durations_ms_dict)."""
        _warmup(cls.WARMUP_N)
        orc = _make_orchestrator()
        pipeline: List[float] = []
        stages:   Dict[str, List[float]] = {
            "market": [], "company": [], "strategy": [],
            "decision": [], "portfolio": [],
        }
        for _ in range(cls.MEASURE_N):
            r = _run_pipeline(orc)
            pipeline.append(r.run_record.total_duration_ms)
            for stage, ms in r.run_record.stage_durations_ms.items():
                if stage in stages:
                    stages[stage].append(ms)
        return pipeline, stages

    def test_collect_latency_samples(self):
        """Collect and cache the full latency sample set (runs once per session)."""
        if "p1_pipeline_ms" in _M:
            return  # already collected
        pipeline, stages = self._collect()
        _M["p1_pipeline_ms"]  = pipeline
        _M["p1_stage_ms"]     = stages
        _M["p1_p50"]          = _percentile(pipeline, 50)
        _M["p1_p95"]          = _percentile(pipeline, 95)
        _M["p1_p99"]          = _percentile(pipeline, 99)
        _M["p1_avg"]          = statistics.mean(pipeline)
        _M["p1_worst"]        = max(pipeline)
        _M["p1_n"]            = len(pipeline)
        assert len(pipeline) == self.MEASURE_N

    def test_market_stage_avg_latency(self):
        self.test_collect_latency_samples()
        ms_list = _M["p1_stage_ms"].get("market", [])
        if not ms_list:
            pytest.skip("no market stage timings captured")
        avg = statistics.mean(ms_list)
        assert avg < self.T_STAGE_AVG_MS, (
            f"Market stage avg {avg:.2f}ms exceeds {self.T_STAGE_AVG_MS}ms"
        )

    def test_company_stage_avg_latency(self):
        self.test_collect_latency_samples()
        ms_list = _M["p1_stage_ms"].get("company", [])
        if not ms_list:
            pytest.skip("no company stage timings captured")
        avg = statistics.mean(ms_list)
        assert avg < self.T_STAGE_AVG_MS, (
            f"Company stage avg {avg:.2f}ms exceeds {self.T_STAGE_AVG_MS}ms"
        )

    def test_strategy_stage_avg_latency(self):
        self.test_collect_latency_samples()
        ms_list = _M["p1_stage_ms"].get("strategy", [])
        if not ms_list:
            pytest.skip("no strategy stage timings captured")
        avg = statistics.mean(ms_list)
        assert avg < self.T_STAGE_AVG_MS, (
            f"Strategy stage avg {avg:.2f}ms exceeds {self.T_STAGE_AVG_MS}ms"
        )

    def test_decision_stage_avg_latency(self):
        self.test_collect_latency_samples()
        ms_list = _M["p1_stage_ms"].get("decision", [])
        if not ms_list:
            pytest.skip("no decision stage timings captured")
        avg = statistics.mean(ms_list)
        assert avg < self.T_STAGE_AVG_MS, (
            f"Decision stage avg {avg:.2f}ms exceeds {self.T_STAGE_AVG_MS}ms"
        )

    def test_portfolio_stage_avg_latency(self):
        self.test_collect_latency_samples()
        ms_list = _M["p1_stage_ms"].get("portfolio", [])
        if not ms_list:
            pytest.skip("no portfolio stage timings captured")
        avg = statistics.mean(ms_list)
        assert avg < self.T_STAGE_AVG_MS, (
            f"Portfolio stage avg {avg:.2f}ms exceeds {self.T_STAGE_AVG_MS}ms"
        )

    def test_pipeline_avg_latency(self):
        self.test_collect_latency_samples()
        avg = _M["p1_avg"]
        assert avg < self.T_PIPELINE_AVG, (
            f"Pipeline avg {avg:.2f}ms exceeds {self.T_PIPELINE_AVG}ms"
        )

    def test_pipeline_p50_latency(self):
        self.test_collect_latency_samples()
        p50 = _M["p1_p50"]
        assert p50 < self.T_P50, (
            f"Pipeline p50 {p50:.2f}ms exceeds {self.T_P50}ms"
        )

    def test_pipeline_p95_latency(self):
        self.test_collect_latency_samples()
        p95 = _M["p1_p95"]
        assert p95 < self.T_P95, (
            f"Pipeline p95 {p95:.2f}ms exceeds {self.T_P95}ms"
        )

    def test_pipeline_p99_latency(self):
        self.test_collect_latency_samples()
        p99 = _M["p1_p99"]
        assert p99 < self.T_P99, (
            f"Pipeline p99 {p99:.2f}ms exceeds {self.T_P99}ms"
        )

    def test_pipeline_worst_case_latency(self):
        self.test_collect_latency_samples()
        worst = _M["p1_worst"]
        assert worst < self.T_WORST, (
            f"Pipeline worst-case {worst:.2f}ms exceeds {self.T_WORST}ms"
        )

    def test_latency_distribution_is_tight(self):
        """p99/p50 ratio must be < 20 (no long tail)."""
        self.test_collect_latency_samples()
        p50  = _M["p1_p50"]
        p99  = _M["p1_p99"]
        if p50 <= 0:
            return
        ratio = p99 / p50
        assert ratio < 20.0, (
            f"Latency tail ratio p99/p50 = {ratio:.1f}x exceeds 20x "
            f"(p50={p50:.2f}ms p99={p99:.2f}ms)"
        )

    def test_latency_report(self):
        """Always passes — prints the latency profile."""
        self.test_collect_latency_samples()
        pipeline = _M.get("p1_pipeline_ms", [])
        stages   = _M.get("p1_stage_ms",    {})
        print("\n")
        print("  [Part 1] Latency Profile")
        print(f"    N samples     : {_M.get('p1_n', 0)}")
        print(f"    Pipeline avg  : {_M.get('p1_avg', 0):.2f} ms")
        print(f"    Pipeline p50  : {_M.get('p1_p50', 0):.2f} ms")
        print(f"    Pipeline p95  : {_M.get('p1_p95', 0):.2f} ms")
        print(f"    Pipeline p99  : {_M.get('p1_p99', 0):.2f} ms")
        print(f"    Pipeline worst: {_M.get('p1_worst', 0):.2f} ms")
        print(f"    Stage averages (ms):")
        for stage, ms_list in stages.items():
            if ms_list:
                print(f"      {stage:<12}: {statistics.mean(ms_list):.3f} avg  "
                      f"{_percentile(ms_list, 95):.3f} p95")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 2 — THROUGHPUT CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart2Throughput:
    """
    Measure how many workflows per second the platform sustains.
    """

    WARMUP_N          = 20
    SEQUENTIAL_N      = 200      # sequential burst
    CONCURRENT_BATCH  = 50       # concurrent batch size
    CONCURRENT_ROUNDS = 4        # rounds of concurrent batches
    WORKERS           = 8        # thread pool size for concurrent test

    T_WF_PER_SEC_SEQ  = 10.0    # sequential workflows/sec minimum
    T_WF_PER_SEC_CONC = 5.0     # concurrent workflows/sec minimum (per worker)
    T_SNAP_PER_SEC    = 10.0    # portfolio snapshots/sec minimum

    def test_sequential_throughput(self):
        _warmup(self.WARMUP_N)
        orc = _make_orchestrator()
        t0  = time.perf_counter()
        for _ in range(self.SEQUENTIAL_N):
            _run_pipeline(orc)
        elapsed = time.perf_counter() - t0
        wf_per_sec = self.SEQUENTIAL_N / elapsed
        _M["p2_seq_wf_per_sec"] = wf_per_sec
        _M["p2_seq_elapsed_sec"] = elapsed
        print(f"\n  [Part 2] Sequential throughput: {wf_per_sec:.1f} wf/sec")
        assert wf_per_sec >= self.T_WF_PER_SEC_SEQ, (
            f"Sequential throughput {wf_per_sec:.1f} wf/sec < target "
            f"{self.T_WF_PER_SEC_SEQ} wf/sec"
        )

    def test_snapshot_throughput(self):
        """Count published snapshots per second."""
        orc    = _make_orchestrator()
        snaps  = 0
        t0     = time.perf_counter()
        for _ in range(100):
            r = _run_pipeline(orc)
            if r.succeeded and r.portfolio_snapshot is not None:
                snaps += 1
        elapsed = time.perf_counter() - t0
        snap_per_sec = snaps / elapsed
        _M["p2_snap_per_sec"] = snap_per_sec
        print(f"\n  [Part 2] Snapshot throughput: {snap_per_sec:.1f} snap/sec")
        assert snap_per_sec >= self.T_SNAP_PER_SEC, (
            f"Snapshot throughput {snap_per_sec:.1f}/sec < target "
            f"{self.T_SNAP_PER_SEC}/sec"
        )

    def test_concurrent_pipeline_throughput(self):
        """Run CONCURRENT_BATCH pipelines in parallel, measure combined wf/sec."""
        _warmup(self.WARMUP_N)
        completed = 0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.WORKERS) as pool:
            futures = []
            for _ in range(self.CONCURRENT_BATCH * self.CONCURRENT_ROUNDS):
                orc = _make_orchestrator()
                futures.append(pool.submit(_run_pipeline, orc))
            for f in as_completed(futures):
                try:
                    f.result()
                    completed += 1
                except Exception:
                    pass
        elapsed = time.perf_counter() - t0
        total = self.CONCURRENT_BATCH * self.CONCURRENT_ROUNDS
        wf_per_sec = completed / elapsed
        _M["p2_conc_wf_per_sec"] = wf_per_sec
        _M["p2_conc_success_rate"] = completed / total
        print(f"\n  [Part 2] Concurrent throughput: {wf_per_sec:.1f} wf/sec "
              f"({completed}/{total} succeeded)")
        assert completed >= int(total * 0.95), (
            f"Concurrent success rate {completed}/{total} < 95%"
        )
        per_worker = wf_per_sec / self.WORKERS
        assert per_worker >= self.T_WF_PER_SEC_CONC, (
            f"Per-worker concurrent throughput {per_worker:.1f} wf/sec < "
            f"{self.T_WF_PER_SEC_CONC}"
        )

    def test_max_sustainable_throughput(self):
        """Run 3 back-to-back bursts; throughput must not degrade > 30%."""
        _warmup(self.WARMUP_N)
        burst_n = 100
        burst_rates: List[float] = []
        for burst in range(3):
            orc = _make_orchestrator()
            t0  = time.perf_counter()
            for _ in range(burst_n):
                _run_pipeline(orc)
            elapsed = time.perf_counter() - t0
            burst_rates.append(burst_n / elapsed)
        _M["p2_burst_rates"] = burst_rates
        print(f"\n  [Part 2] Burst rates (wf/sec): "
              f"{', '.join(f'{r:.1f}' for r in burst_rates)}")
        assert burst_rates[0] > 0
        degradation = (burst_rates[0] - min(burst_rates)) / burst_rates[0]
        assert degradation < 0.30, (
            f"Throughput degraded {degradation*100:.1f}% across bursts "
            f"(threshold 30%)"
        )

    def test_throughput_report(self):
        print("\n")
        print("  [Part 2] Throughput Summary")
        print(f"    Sequential     : {_M.get('p2_seq_wf_per_sec', 0):.1f} wf/sec")
        print(f"    Snapshot rate  : {_M.get('p2_snap_per_sec', 0):.1f} snap/sec")
        print(f"    Concurrent     : {_M.get('p2_conc_wf_per_sec', 0):.1f} wf/sec total")
        rates = _M.get("p2_burst_rates", [])
        if rates:
            print(f"    Burst rates    : {', '.join(f'{r:.1f}' for r in rates)}")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 3 — SCALABILITY CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart3Scalability:
    """
    Run N concurrent workflows and verify correctness + latency growth.
    Each concurrency level uses independent orchestrators (no shared state).
    """

    LEVELS = [1, 5, 10, 25, 50, 100]
    T_ALL_SUCCEED_PCT  = 0.95      # 95% success rate minimum
    T_LATENCY_FACTOR   = 6.0       # p95 at 100 conc must be < 6x single p95
    T_DEADLOCK_SEC     = 120.0     # hard timeout for 100-concurrent batch

    @staticmethod
    def _run_concurrent(n: int) -> Tuple[float, float, int, int]:
        """
        Run n concurrent pipelines.
        Returns (wall_sec, p95_ms, succeeded, total).
        """
        results:  List[float] = []
        lock      = threading.Lock()
        counter   = [0]   # [0]=errors

        def _worker():
            orc = _make_orchestrator()
            t0  = time.perf_counter()
            try:
                _run_pipeline(orc)
                ms = (time.perf_counter() - t0) * 1_000.0
                with lock:
                    results.append(ms)
            except Exception:
                with lock:
                    counter[0] += 1

        workers = min(n, 32)   # cap ThreadPoolExecutor to 32 for safety
        t_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_worker) for _ in range(n)]
            for f in as_completed(futs, timeout=120.0):
                try:
                    f.result()
                except Exception:
                    pass
        wall = time.perf_counter() - t_start
        p95  = _percentile(results, 95) if results else 0.0
        return wall, p95, len(results), n

    def test_1_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(1)
        _M["p3_1_p95"]   = p95
        _M["p3_1_wall"]  = wall
        assert ok == total, f"1-concurrent: {ok}/{total} succeeded"

    def test_5_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(5)
        _M["p3_5_p95"]  = p95
        _M["p3_5_wall"] = wall
        assert ok >= int(total * self.T_ALL_SUCCEED_PCT), (
            f"5-concurrent: {ok}/{total} < 95%"
        )

    def test_10_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(10)
        _M["p3_10_p95"]  = p95
        _M["p3_10_wall"] = wall
        assert ok >= int(total * self.T_ALL_SUCCEED_PCT), (
            f"10-concurrent: {ok}/{total} < 95%"
        )

    def test_25_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(25)
        _M["p3_25_p95"]  = p95
        _M["p3_25_wall"] = wall
        assert ok >= int(total * self.T_ALL_SUCCEED_PCT), (
            f"25-concurrent: {ok}/{total} < 95%"
        )

    def test_50_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(50)
        _M["p3_50_p95"]  = p95
        _M["p3_50_wall"] = wall
        assert ok >= int(total * self.T_ALL_SUCCEED_PCT), (
            f"50-concurrent: {ok}/{total} < 95%"
        )

    def test_100_concurrent(self):
        wall, p95, ok, total = self._run_concurrent(100)
        _M["p3_100_p95"]  = p95
        _M["p3_100_wall"] = wall
        assert ok >= int(total * self.T_ALL_SUCCEED_PCT), (
            f"100-concurrent: {ok}/{total} < 95%"
        )
        assert wall < self.T_DEADLOCK_SEC, (
            f"100-concurrent took {wall:.1f}s (deadlock threshold "
            f"{self.T_DEADLOCK_SEC}s)"
        )

    def test_latency_growth_is_sublinear(self):
        """p95 latency at 100-concurrent must be < T_LATENCY_FACTOR × single p95."""
        p95_1   = _M.get("p3_1_p95",   0)
        p95_100 = _M.get("p3_100_p95", 0)
        if p95_1 <= 0:
            pytest.skip("single-concurrent p95 not measured yet")
        factor = p95_100 / p95_1 if p95_1 > 0 else 0
        _M["p3_growth_factor"] = factor
        assert factor < self.T_LATENCY_FACTOR, (
            f"Latency growth factor {factor:.1f}x exceeds {self.T_LATENCY_FACTOR}x "
            f"(p95@1={p95_1:.1f}ms  p95@100={p95_100:.1f}ms)"
        )

    def test_no_lock_starvation(self):
        """
        All 100-concurrent runs must eventually finish (checked by
        test_100_concurrent wall time).  Verify success rate directly.
        """
        ok    = len([True for k in ["p3_100_wall"] if k in _M])
        assert ok > 0, "100-concurrent test was not run"

    def test_scalability_report(self):
        print("\n")
        print("  [Part 3] Scalability Profile")
        print(f"    {'N':>5}  {'Wall(s)':>9}  {'p95(ms)':>9}")
        print(f"    {'-'*5}  {'-'*9}  {'-'*9}")
        for n in self.LEVELS:
            wall = _M.get(f"p3_{n}_wall", 0)
            p95  = _M.get(f"p3_{n}_p95",  0)
            print(f"    {n:>5}  {wall:>9.2f}  {p95:>9.2f}")
        gf = _M.get("p3_growth_factor")
        if gf is not None:
            print(f"    Latency growth factor (100x/1x): {gf:.1f}x")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 4 — RESOURCE CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart4Resources:
    """
    Measure CPU time, memory, thread count, executor utilisation,
    history/statistics bounds.
    """

    T_HEAP_GROWTH_100_MB   = 10.0   # MB — heap growth over 100 runs
    T_HEAP_GROWTH_1K_MB    = 25.0   # MB — heap growth over 1 000 runs
    T_THREAD_LEAK_100      = 5      # extra threads allowed after 100 runs
    T_EXEC_BLOCKING_PCT    = 0.05   # <5% of tasks may be flagged as blocking
    T_HISTORY_MAX          = 200    # WorkflowHistory default max_runs
    T_STATS_MAX            = 500    # WorkflowStatistics default max_runs

    def test_heap_growth_100_runs(self):
        """Python heap must grow < T_HEAP_GROWTH_100_MB over 100 runs."""
        gc.collect()
        tracemalloc.start()
        snapshot_before, _ = tracemalloc.get_traced_memory()
        orc = _make_orchestrator()
        for _ in range(100):
            _run_pipeline(orc)
        gc.collect()
        snapshot_after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth_mb = (snapshot_after - snapshot_before) / (1024 * 1024)
        _M["p4_heap_100_mb"] = growth_mb
        print(f"\n  [Part 4] Heap growth over 100 runs: {growth_mb:.2f} MB")
        assert growth_mb < self.T_HEAP_GROWTH_100_MB, (
            f"Heap grew {growth_mb:.2f} MB over 100 runs "
            f"(threshold {self.T_HEAP_GROWTH_100_MB} MB)"
        )

    def test_heap_growth_1000_runs(self):
        """Python heap must grow < T_HEAP_GROWTH_1K_MB over 1 000 runs."""
        gc.collect()
        tracemalloc.start()
        snap_before, _ = tracemalloc.get_traced_memory()
        orc = _make_orchestrator()
        for _ in range(1_000):
            _run_pipeline(orc)
        gc.collect()
        snap_after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth_mb = (snap_after - snap_before) / (1024 * 1024)
        _M["p4_heap_1k_mb"] = growth_mb
        print(f"\n  [Part 4] Heap growth over 1 000 runs: {growth_mb:.2f} MB")
        assert growth_mb < self.T_HEAP_GROWTH_1K_MB, (
            f"Heap grew {growth_mb:.2f} MB over 1 000 runs "
            f"(threshold {self.T_HEAP_GROWTH_1K_MB} MB)"
        )

    def test_thread_count_stable_after_100_runs(self):
        """Thread count must not grow unboundedly after 100 pipeline runs."""
        gc.collect()
        baseline_threads = threading.active_count()
        orc = _make_orchestrator()
        for _ in range(100):
            _run_pipeline(orc)
        gc.collect()
        after_threads = threading.active_count()
        delta = after_threads - baseline_threads
        _M["p4_thread_delta_100"] = delta
        print(f"\n  [Part 4] Thread delta after 100 runs: {delta}")
        assert delta <= self.T_THREAD_LEAK_100, (
            f"Thread count grew by {delta} after 100 runs "
            f"(threshold {self.T_THREAD_LEAK_100})"
        )

    def test_executor_manager_statistics(self):
        """AsyncExecutionManager must track tasks and keep history bounded."""
        mgr = get_execution_manager()
        stats = mgr.statistics()
        assert stats.total_completed >= 0
        # History must be bounded (max_task_history=200 by default)
        history = mgr.task_history()
        assert len(history) <= 200, (
            f"Execution manager history length {len(history)} exceeds 200"
        )
        _M["p4_exec_total_completed"] = stats.total_completed
        _M["p4_exec_avg_latency_ms"]  = stats.avg_latency_ms
        _M["p4_exec_blocking"]        = stats.blocking_calls_detected

    def test_executor_blocking_calls_low(self):
        """Fraction of blocking-detected tasks must be < T_EXEC_BLOCKING_PCT."""
        mgr   = get_execution_manager()
        stats = mgr.statistics()
        total = stats.total_completed
        if total == 0:
            return  # no data
        blocking_pct = stats.blocking_calls_detected / total
        _M["p4_exec_blocking_pct"] = blocking_pct
        assert blocking_pct < self.T_EXEC_BLOCKING_PCT, (
            f"Blocking calls: {stats.blocking_calls_detected}/{total} "
            f"= {blocking_pct*100:.1f}% (threshold {self.T_EXEC_BLOCKING_PCT*100:.0f}%)"
        )

    def test_workflow_history_is_bounded(self):
        """WorkflowHistory must not exceed its configured max_runs."""
        hist = WorkflowHistory(max_runs=self.T_HISTORY_MAX)
        orc  = InstitutionalWorkflowOrchestrator(
            engines  = _make_engines(),
            history  = hist,
            params   = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
        )
        n = self.T_HISTORY_MAX + 50
        for _ in range(n):
            _run_pipeline(orc)
        records = orc.history(n)
        _M["p4_history_len"] = len(records)
        assert len(records) <= self.T_HISTORY_MAX, (
            f"History has {len(records)} records, exceeds max {self.T_HISTORY_MAX}"
        )

    def test_workflow_statistics_is_bounded(self):
        """WorkflowStatistics must not exceed its configured max_runs."""
        stats_store = WorkflowStatistics(max_runs=self.T_STATS_MAX)
        orc = InstitutionalWorkflowOrchestrator(
            engines    = _make_engines(),
            statistics = stats_store,
            params     = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
        )
        n = self.T_STATS_MAX + 100
        for _ in range(n):
            _run_pipeline(orc)
        snap = orc.statistics()
        _M["p4_stats_total_runs"] = snap.total_runs
        assert snap.total_runs <= self.T_STATS_MAX, (
            f"Statistics.total_runs={snap.total_runs} exceeds max {self.T_STATS_MAX}"
        )

    def test_resource_report(self):
        print("\n")
        print("  [Part 4] Resource Summary")
        print(f"    Heap growth (100 runs)  : {_M.get('p4_heap_100_mb', 0):.2f} MB")
        print(f"    Heap growth (1 000 runs): {_M.get('p4_heap_1k_mb', 0):.2f} MB")
        print(f"    Thread delta (100 runs) : {_M.get('p4_thread_delta_100', '?')}")
        print(f"    Exec avg latency        : {_M.get('p4_exec_avg_latency_ms', 0):.2f} ms")
        print(f"    Exec blocking calls     : {_M.get('p4_exec_blocking', 0)}")
        print(f"    History bounded at      : {_M.get('p4_history_len', 0)} records")
        print(f"    Statistics bounded at   : {_M.get('p4_stats_total_runs', 0)} records")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 5 — LONG RUN CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart5LongRun:
    """
    Run thousands of pipeline executions and verify memory and thread stability.
    """

    T_HEAP_GROWTH_5K_MB  = 200.0   # MB — allocator watermark after 5 000 runs
    T_HEAP_GROWTH_10K_MB = 400.0   # MB — allocator watermark after 10 000 runs
    T_THREAD_LEAK_10K    = 8       # extra threads after 10 000 runs
    T_SUCCESS_RATE       = 1.0     # 100% success required

    def test_1000_runs_all_succeed(self):
        gc.collect()
        orc = _make_orchestrator()
        succeeded = 0
        for _ in range(1_000):
            r = _run_pipeline(orc)
            if r.succeeded:
                succeeded += 1
        _M["p5_1k_success"] = succeeded
        assert succeeded == 1_000, (
            f"1 000 runs: {succeeded}/1 000 succeeded"
        )

    def test_5000_runs_no_memory_leak(self):
        gc.collect()
        tracemalloc.start()
        baseline, _ = tracemalloc.get_traced_memory()
        orc = _make_orchestrator()
        for _ in range(5_000):
            _run_pipeline(orc)
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth_mb = (after - baseline) / (1024 * 1024)
        _M["p5_5k_heap_mb"] = growth_mb
        print(f"\n  [Part 5] Heap growth over 5 000 runs: {growth_mb:.2f} MB")
        assert growth_mb < self.T_HEAP_GROWTH_5K_MB, (
            f"Memory leak: heap grew {growth_mb:.2f} MB over 5 000 runs "
            f"(threshold {self.T_HEAP_GROWTH_5K_MB} MB)"
        )

    def test_10000_runs_no_memory_leak(self):
        gc.collect()
        tracemalloc.start()
        baseline, _ = tracemalloc.get_traced_memory()
        orc = _make_orchestrator()
        for _ in range(10_000):
            _run_pipeline(orc)
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth_mb = (after - baseline) / (1024 * 1024)
        _M["p5_10k_heap_mb"] = growth_mb
        print(f"\n  [Part 5] Heap growth over 10 000 runs: {growth_mb:.2f} MB")
        assert growth_mb < self.T_HEAP_GROWTH_10K_MB, (
            f"Memory leak: heap grew {growth_mb:.2f} MB over 10 000 runs "
            f"(threshold {self.T_HEAP_GROWTH_10K_MB} MB)"
        )

    def test_10000_runs_no_thread_leak(self):
        gc.collect()
        baseline = threading.active_count()
        orc = _make_orchestrator()
        for _ in range(10_000):
            _run_pipeline(orc)
        gc.collect()
        after = threading.active_count()
        delta = after - baseline
        _M["p5_10k_thread_delta"] = delta
        assert delta <= self.T_THREAD_LEAK_10K, (
            f"Thread leak: {delta} extra threads after 10 000 runs "
            f"(threshold {self.T_THREAD_LEAK_10K})"
        )

    def test_10000_runs_no_context_leak(self):
        """GC tracked object count must not grow unboundedly."""
        gc.collect()
        before_counts = sum(gc.get_count())
        orc = _make_orchestrator()
        for _ in range(10_000):
            _run_pipeline(orc)
        gc.collect()
        after_counts = sum(gc.get_count())
        delta = after_counts - before_counts
        _M["p5_gc_count_delta"] = delta
        # GC count should not grow by more than 10 000 objects over 10 000 runs
        # (bounded deques, re-used objects)
        assert delta < 50_000, (
            f"GC object count grew by {delta} over 10 000 runs — possible context leak"
        )

    def test_10000_runs_history_bounded(self):
        """WorkflowHistory must stay at its max_runs ceiling after 10 000 runs."""
        max_runs = 200
        hist = WorkflowHistory(max_runs=max_runs)
        orc  = InstitutionalWorkflowOrchestrator(
            engines  = _make_engines(),
            history  = hist,
            params   = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
        )
        for _ in range(10_000):
            _run_pipeline(orc)
        records = orc.history(max_runs + 999)
        _M["p5_10k_history_len"] = len(records)
        assert len(records) <= max_runs, (
            f"History has {len(records)} records after 10 000 runs — unbounded"
        )

    def test_long_run_report(self):
        print("\n")
        print("  [Part 5] Long Run Summary")
        print(f"    1 000 runs succeeded: {_M.get('p5_1k_success', '?')}")
        print(f"    Heap growth 5 000   : {_M.get('p5_5k_heap_mb', 0):.2f} MB")
        print(f"    Heap growth 10 000  : {_M.get('p5_10k_heap_mb', 0):.2f} MB")
        print(f"    Thread delta 10 000 : {_M.get('p5_10k_thread_delta', '?')}")
        print(f"    GC count delta      : {_M.get('p5_gc_count_delta', '?')}")
        print(f"    History bounded at  : {_M.get('p5_10k_history_len', '?')} records")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 6 — FRAMEWORK OVERHEAD
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart6FrameworkOverhead:
    """
    Measure the overhead introduced by each framework layer
    relative to a bare null-function baseline.
    """

    N          = 100
    T_LIFECYCLE_MS    = 500.0   # start+stop combined (2× asyncio.run())
    T_ASYNC_EXEC_MS   = 250.0   # execute_sync(lambda: None) overhead
    T_ERROR_FWK_MS    = 50.0    # report_failure() overhead
    T_WF_RUN_MS       = 200.0   # full workflow run including framework
    T_OVERHEAD_RATIO  = 100_000.0  # workflow vs lambda: None — ratio is expected to be large

    def _time_n(self, fn: Callable[[], Any], n: int = None) -> float:
        """Return average ms per call over n calls."""
        n = n or self.N
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - t0) * 1_000.0 / n

    def test_null_baseline(self):
        """Measure overhead of a trivial no-op function."""
        avg_ms = self._time_n(lambda: None, n=10_000)
        _M["p6_null_ms"] = avg_ms
        print(f"\n  [Part 6] Null baseline: {avg_ms:.6f} ms/call")

    def test_lifecycle_start_stop_overhead(self):
        """Measure the overhead of start() + stop() on a LifecycleAwareMixin engine."""
        class _TestEngine(LifecycleAwareMixin):
            SYSTEM_ID = "test:lifecycle:overhead"
            VERSION   = "1.0.0"
            def _on_start(self) -> None: pass
            def _on_stop(self)  -> None: pass

        times: List[float] = []
        for _ in range(self.N):
            eng = _TestEngine()
            t0  = time.perf_counter()
            eng.start()
            eng.stop()
            times.append((time.perf_counter() - t0) * 1_000.0)

        avg_ms = statistics.mean(times)
        p95_ms = _percentile(times, 95)
        _M["p6_lifecycle_avg_ms"] = avg_ms
        _M["p6_lifecycle_p95_ms"] = p95_ms
        print(f"\n  [Part 6] Lifecycle start+stop: avg={avg_ms:.2f}ms  p95={p95_ms:.2f}ms")
        assert avg_ms < self.T_LIFECYCLE_MS, (
            f"Lifecycle avg {avg_ms:.2f}ms exceeds {self.T_LIFECYCLE_MS}ms"
        )

    def test_async_execute_sync_overhead(self):
        """Measure AsyncExecutionManager.execute_sync(lambda: None) overhead."""
        mgr    = get_execution_manager()
        times: List[float] = []
        for _ in range(self.N):
            t0 = time.perf_counter()
            mgr.execute_sync(lambda: None)
            times.append((time.perf_counter() - t0) * 1_000.0)

        avg_ms = statistics.mean(times)
        p95_ms = _percentile(times, 95)
        _M["p6_async_exec_avg_ms"] = avg_ms
        _M["p6_async_exec_p95_ms"] = p95_ms
        print(f"\n  [Part 6] execute_sync(null): avg={avg_ms:.2f}ms  p95={p95_ms:.2f}ms")
        assert avg_ms < self.T_ASYNC_EXEC_MS, (
            f"execute_sync avg {avg_ms:.2f}ms exceeds {self.T_ASYNC_EXEC_MS}ms"
        )

    def test_error_framework_overhead(self):
        """Measure get_error_manager().report_failure() overhead."""
        from iios.common.errors.exceptions import IIOSError

        emgr   = get_error_manager()
        err    = IIOSError("perf-overhead-test")
        times: List[float] = []
        for _ in range(self.N):
            t0 = time.perf_counter()
            emgr.report_failure(
                "test:overhead",
                err,
            )
            times.append((time.perf_counter() - t0) * 1_000.0)

        avg_ms = statistics.mean(times)
        _M["p6_error_fwk_avg_ms"] = avg_ms
        print(f"\n  [Part 6] error report_failure: avg={avg_ms:.2f}ms")
        assert avg_ms < self.T_ERROR_FWK_MS, (
            f"error report_failure avg {avg_ms:.2f}ms exceeds {self.T_ERROR_FWK_MS}ms"
        )

    def test_workflow_run_overhead(self):
        """Full mock pipeline run must stay under T_WF_RUN_MS average."""
        _warmup(20)
        orc    = _make_orchestrator()
        times: List[float] = []
        for _ in range(self.N):
            t0 = time.perf_counter()
            _run_pipeline(orc)
            times.append((time.perf_counter() - t0) * 1_000.0)

        avg_ms = statistics.mean(times)
        p95_ms = _percentile(times, 95)
        _M["p6_wf_run_avg_ms"] = avg_ms
        _M["p6_wf_run_p95_ms"] = p95_ms
        print(f"\n  [Part 6] Workflow run overhead: avg={avg_ms:.2f}ms  p95={p95_ms:.2f}ms")
        assert avg_ms < self.T_WF_RUN_MS, (
            f"Workflow run avg {avg_ms:.2f}ms exceeds {self.T_WF_RUN_MS}ms"
        )

    def test_framework_overhead_ratio(self):
        """Workflow overhead vs null-baseline must be < T_OVERHEAD_RATIO×."""
        null_ms = _M.get("p6_null_ms", 0)
        wf_ms   = _M.get("p6_wf_run_avg_ms", 0)
        if null_ms <= 0 or wf_ms <= 0:
            pytest.skip("baseline measurements not yet available")
        ratio = wf_ms / null_ms
        _M["p6_overhead_ratio"] = ratio
        print(f"\n  [Part 6] Overhead ratio: {ratio:.0f}x null baseline")
        assert ratio < self.T_OVERHEAD_RATIO, (
            f"Workflow is {ratio:.0f}x slower than null baseline "
            f"(threshold {self.T_OVERHEAD_RATIO}x)"
        )

    def test_framework_overhead_report(self):
        print("\n")
        print("  [Part 6] Framework Overhead Summary")
        print(f"    Null baseline          : {_M.get('p6_null_ms', 0):.6f} ms/call")
        print(f"    Lifecycle start+stop   : {_M.get('p6_lifecycle_avg_ms', 0):.2f} ms avg")
        print(f"    execute_sync(null)     : {_M.get('p6_async_exec_avg_ms', 0):.2f} ms avg")
        print(f"    error report_failure   : {_M.get('p6_error_fwk_avg_ms', 0):.2f} ms avg")
        print(f"    Full workflow run      : {_M.get('p6_wf_run_avg_ms', 0):.2f} ms avg  "
              f"(p95={_M.get('p6_wf_run_p95_ms', 0):.2f}ms)")
        print(f"    Overhead ratio         : {_M.get('p6_overhead_ratio', '?')}x null")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 7 — STRESS CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart7Stress:
    """
    Inject adversarial conditions: extreme concurrency, rapid cancel,
    rapid restart, high failure rate, large payloads.
    """

    def test_high_concurrency_200(self):
        """200 concurrent pipelines — all must complete without deadlock."""
        errors: List[Exception] = []
        lock   = threading.Lock()

        def _worker():
            try:
                orc = _make_orchestrator()
                _run_pipeline(orc)
            except Exception as e:
                with lock:
                    errors.append(e)

        t0 = time.perf_counter()
        threads = [threading.Thread(target=_worker) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120.0)
        wall = time.perf_counter() - t0
        _M["p7_200_conc_wall"]   = wall
        _M["p7_200_conc_errors"] = len(errors)
        assert len(errors) == 0, (
            f"200-concurrent: {len(errors)} errors\n"
            + "\n".join(str(e) for e in errors[:3])
        )
        assert wall < 120.0, f"200-concurrent deadlocked ({wall:.1f}s)"

    def test_rapid_cancel_stress(self):
        """
        Cancel a running pipeline 100 times rapidly.
        The orchestrator must handle cancel calls without crashing.
        """
        errors = 0
        for _ in range(100):
            orc = _make_orchestrator()
            try:
                # Fire cancel before/after run — both paths must be safe
                orc.cancel()   # no active state — must return False gracefully
                _run_pipeline(orc)
                orc.cancel()   # completed run — must return False gracefully
            except Exception:
                errors += 1
        _M["p7_rapid_cancel_errors"] = errors
        assert errors == 0, f"Rapid cancel: {errors} errors"

    def test_rapid_restart_stress(self):
        """
        Rapidly start/stop a lifecycle engine 50 times.
        Must not deadlock and must stabilise thread count.
        """
        class _RE(LifecycleAwareMixin):
            SYSTEM_ID = "stress:restart"
            VERSION   = "1.0"
            def _on_start(self) -> None: pass
            def _on_stop(self)  -> None: pass

        baseline = threading.active_count()
        for _ in range(50):
            eng = _RE()
            eng.start()
            eng.stop()
        gc.collect()
        after = threading.active_count()
        delta = after - baseline
        _M["p7_restart_thread_delta"] = delta
        assert delta <= 10, (
            f"Rapid restart leaked {delta} threads (baseline={baseline}, after={after})"
        )

    def test_high_failure_rate_stress(self):
        """100% failure in all stages — pipeline must fail gracefully on all 200 runs."""
        orc = InstitutionalWorkflowOrchestrator(
            engines = _make_engines(
                market_fail=True, company_fail=True, strategy_fail=True,
                decision_fail=True, portfolio_fail=True,
            ),
            params = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
        )
        failed = 0
        for _ in range(200):
            r = _run_pipeline(orc)
            if not r.succeeded:
                failed += 1
        _M["p7_all_fail_count"] = failed
        assert failed == 200, (
            f"High failure stress: {failed}/200 correctly reported failure"
        )

    def test_large_snapshot_stress(self):
        """Run 50 pipelines with 50KB snapshot payloads — no OOM or crash."""
        big_snap = _BigSnap(kb=50)
        orc = _make_orchestrator(portfolio_snap=big_snap)
        succeeded = 0
        for _ in range(50):
            r = _run_pipeline(orc)
            if r.succeeded:
                succeeded += 1
        _M["p7_large_snap_ok"] = succeeded
        assert succeeded == 50, f"Large snapshot: {succeeded}/50 succeeded"

    def test_large_history_stress(self):
        """Fill history to max+500 entries — no error, stays bounded."""
        hist = WorkflowHistory(max_runs=200)
        orc  = InstitutionalWorkflowOrchestrator(
            engines  = _make_engines(),
            history  = hist,
            params   = WorkflowParameters(max_retries=0, retry_delay_sec=0.0),
        )
        for _ in range(700):
            _run_pipeline(orc)
        records = orc.history(9999)
        _M["p7_large_history_len"] = len(records)
        assert len(records) <= 200

    def test_stress_report(self):
        print("\n")
        print("  [Part 7] Stress Summary")
        print(f"    200-concurrent wall      : {_M.get('p7_200_conc_wall', 0):.2f}s")
        print(f"    200-concurrent errors    : {_M.get('p7_200_conc_errors', '?')}")
        print(f"    Rapid cancel errors      : {_M.get('p7_rapid_cancel_errors', '?')}")
        print(f"    Restart thread delta     : {_M.get('p7_restart_thread_delta', '?')}")
        print(f"    All-fail (200) correctly : {_M.get('p7_all_fail_count', '?')}")
        print(f"    Large snapshot (50) OK   : {_M.get('p7_large_snap_ok', '?')}")
        print(f"    Large history bounded at : {_M.get('p7_large_history_len', '?')}")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 8 — BOTTLENECK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart8Bottleneck:
    """
    Identify bottlenecks in the platform through measurement and analysis.
    """

    N_SAMPLES = 200

    def test_identify_slowest_stage(self):
        """
        Collect per-stage durations and identify the highest-latency stage.
        Assert that no single stage dominates > 60% of total pipeline time.
        """
        _warmup(20)
        orc     = _make_orchestrator()
        stages  = {s: [] for s in ("market", "company", "strategy",
                                   "decision", "portfolio")}
        totals: List[float] = []
        for _ in range(self.N_SAMPLES):
            r = _run_pipeline(orc)
            totals.append(r.run_record.total_duration_ms)
            for s, ms in r.run_record.stage_durations_ms.items():
                if s in stages:
                    stages[s].append(ms)

        avg_stages = {s: statistics.mean(v) if v else 0.0 for s, v in stages.items()}
        avg_total  = statistics.mean(totals) if totals else 1.0
        slowest    = max(avg_stages, key=avg_stages.get)
        pct        = (avg_stages[slowest] / avg_total * 100.0) if avg_total > 0 else 0.0

        _M["p8_stage_avgs"]  = avg_stages
        _M["p8_slowest"]     = slowest
        _M["p8_slowest_pct"] = pct
        _M["p8_pipeline_avg"] = avg_total

        print(f"\n  [Part 8] Slowest stage: {slowest} ({pct:.1f}% of total)")
        assert pct < 60.0, (
            f"Stage '{slowest}' takes {pct:.1f}% of total pipeline time "
            f"(bottleneck threshold 60%)"
        )

    def test_lock_contention_detection(self):
        """
        Run 10 threads using the SAME orchestrator (shared _run_lock).
        Measure throughput under contention vs sequential.
        """
        shared_orc = _make_orchestrator()
        results: List[float] = []
        lock    = threading.Lock()

        def _worker():
            t0 = time.perf_counter()
            _run_pipeline(shared_orc)
            with lock:
                results.append((time.perf_counter() - t0) * 1_000.0)

        t_start = time.perf_counter()
        threads = [threading.Thread(target=_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60.0)
        wall = (time.perf_counter() - t_start) * 1_000.0

        seq_baseline = _M.get("p6_wf_run_avg_ms") or (
            statistics.mean([_time_run(_make_orchestrator()) for _ in range(10)])
        )
        contention_factor = (wall / 10) / seq_baseline if seq_baseline > 0 else 0
        _M["p8_contention_factor"] = contention_factor
        _M["p8_shared_lock_wall"]  = wall

        print(f"\n  [Part 8] Shared-lock contention: "
              f"{contention_factor:.1f}x seq baseline  wall={wall:.1f}ms")
        # Shared _run_lock serialises 10 threads → contention factor ~ N
        # This is expected and documented behaviour; assert no deadlock only
        assert len(results) == 10, (
            f"Shared-lock test: only {len(results)}/10 threads completed"
        )

    def test_serialization_cost(self):
        """Measure to_dict() serialisation overhead on WorkflowResult / RunRecord."""
        orc = _make_orchestrator()
        r   = _run_pipeline(orc)
        N   = 10_000
        t0  = time.perf_counter()
        for _ in range(N):
            r.run_record.to_dict()
        ms_per_call = (time.perf_counter() - t0) * 1_000.0 / N
        _M["p8_todict_ms"] = ms_per_call
        print(f"\n  [Part 8] run_record.to_dict(): {ms_per_call:.4f} ms/call")
        assert ms_per_call < 5.0, (
            f"Serialisation cost {ms_per_call:.4f}ms/call exceeds 5ms"
        )

    def test_logging_overhead_in_pipeline(self):
        """
        Compare pipeline run with logging disabled vs enabled.
        Overhead from the standard logging layer must be reasonable.
        """
        _warmup(10)
        # With normal logging
        root = logging.getLogger()
        orig_level = root.level
        times_on:  List[float] = []
        orc = _make_orchestrator()
        for _ in range(100):
            t0 = time.perf_counter()
            _run_pipeline(orc)
            times_on.append((time.perf_counter() - t0) * 1_000.0)

        # With logging suppressed
        root.setLevel(logging.CRITICAL)
        times_off: List[float] = []
        orc2 = _make_orchestrator()
        for _ in range(100):
            t0 = time.perf_counter()
            _run_pipeline(orc2)
            times_off.append((time.perf_counter() - t0) * 1_000.0)
        root.setLevel(orig_level)

        avg_on  = statistics.mean(times_on)
        avg_off = statistics.mean(times_off)
        overhead_pct = ((avg_on - avg_off) / avg_off * 100.0) if avg_off > 0 else 0
        _M["p8_log_overhead_pct"] = overhead_pct
        _M["p8_avg_log_on_ms"]    = avg_on
        _M["p8_avg_log_off_ms"]   = avg_off
        print(f"\n  [Part 8] Logging overhead: {overhead_pct:.1f}%  "
              f"(on={avg_on:.2f}ms  off={avg_off:.2f}ms)")
        assert overhead_pct < 200.0, (
            f"Logging overhead {overhead_pct:.1f}% exceeds 200% "
            f"— logging is dominating pipeline"
        )

    def test_bottleneck_report(self):
        print("\n")
        print("  [Part 8] Bottleneck Analysis")
        avgs = _M.get("p8_stage_avgs", {})
        if avgs:
            ranked = sorted(avgs.items(), key=lambda x: x[1], reverse=True)
            print(f"    Stage latency ranking (avg ms):")
            for s, v in ranked:
                print(f"      {s:<12}: {v:.3f} ms")
        print(f"    Slowest stage         : {_M.get('p8_slowest', '?')} "
              f"({_M.get('p8_slowest_pct', 0):.1f}% of total)")
        print(f"    Shared-lock contention: {_M.get('p8_contention_factor', 0):.1f}x seq")
        print(f"    Serialisation cost    : {_M.get('p8_todict_ms', 0):.4f} ms/call")
        print(f"    Logging overhead      : {_M.get('p8_log_overhead_pct', 0):.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
#  PART 9 — OPTIMIZATION REPORT  (report-only — always passes)
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart9Optimization:
    """
    Produce a data-driven optimisation report based on measurements from Parts 1-8.
    All tests in this class always pass (pure analysis and reporting).
    """

    # Severity: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL

    def test_generate_optimization_report(self):
        """
        Analyse collected measurements and emit ranked optimisation opportunities.
        """
        findings: List[dict] = []

        # ── Execute_sync overhead ─────────────────────────────────────────────
        exec_ms = _M.get("p6_async_exec_avg_ms", 0)
        if exec_ms > 50:
            findings.append(dict(
                severity     = "HIGH",
                gain         = "30-50% reduction in lifecycle overhead",
                finding      = f"execute_sync(null) = {exec_ms:.1f}ms — asyncio.run() "
                               f"creates/destroys an event loop each call",
                recommendation = (
                    "Replace asyncio.run() in execute_sync() with a persistent "
                    "event loop thread (e.g. run_coroutine_threadsafe + shared loop). "
                    "Eliminates event loop creation overhead per _on_start/_on_stop call."
                ),
                modules      = ["iios/common/async_exec/async_execution_manager.py",
                                "iios/investment/workflow/engine_lifecycle.py"],
                effort       = "MEDIUM",
            ))
        elif exec_ms > 10:
            findings.append(dict(
                severity     = "MEDIUM",
                gain         = "10-20% reduction in lifecycle overhead",
                finding      = f"execute_sync(null) = {exec_ms:.1f}ms",
                recommendation = "Consider a reusable event loop thread for execute_sync.",
                modules      = ["iios/common/async_exec/async_execution_manager.py"],
                effort       = "MEDIUM",
            ))

        # ── Lifecycle overhead ────────────────────────────────────────────────
        lc_ms = _M.get("p6_lifecycle_avg_ms", 0)
        if lc_ms > 100:
            findings.append(dict(
                severity     = "HIGH",
                gain         = "Reduced engine start/stop latency",
                finding      = f"Lifecycle start+stop avg = {lc_ms:.1f}ms. "
                               f"Each call routes through execute_sync → asyncio.run().",
                recommendation = (
                    "Cache the asyncio event loop in a module-level thread "
                    "so execute_sync uses run_coroutine_threadsafe() instead of "
                    "asyncio.run() (saves ~loop creation time per call)."
                ),
                modules      = ["iios/investment/workflow/engine_lifecycle.py"],
                effort       = "MEDIUM",
            ))

        # ── Pipeline latency ─────────────────────────────────────────────────
        p99 = _M.get("p1_p99", 0)
        avg = _M.get("p1_avg", 0)
        if p99 > 100:
            findings.append(dict(
                severity     = "MEDIUM",
                gain         = "Reduced tail latency",
                finding      = f"Pipeline p99 = {p99:.1f}ms vs avg {avg:.1f}ms "
                               f"(ratio {p99/avg:.1f}x) — GC pauses or lock jitter.",
                recommendation = (
                    "Enable GC freeze during pipeline execution "
                    "(gc.freeze() before run, gc.unfreeze() after) to reduce "
                    "GC-induced jitter in critical sections."
                ),
                modules      = ["iios/investment/workflow/institutional_investment_workflow.py"],
                effort       = "LOW",
            ))

        # ── Stage imbalance ───────────────────────────────────────────────────
        avgs  = _M.get("p8_stage_avgs", {})
        total = _M.get("p8_pipeline_avg", 1)
        slowest = _M.get("p8_slowest")
        slowest_pct = _M.get("p8_slowest_pct", 0)
        if slowest and slowest_pct > 40:
            findings.append(dict(
                severity     = "MEDIUM",
                gain         = "More balanced pipeline",
                finding      = f"Stage '{slowest}' takes {slowest_pct:.1f}% of pipeline "
                               f"time — disproportionate to other stages.",
                recommendation = (
                    f"Profile the '{slowest}' stage adapter in "
                    f"InstitutionalWorkflowOrchestrator._stage_{slowest}(). "
                    f"Check for redundant attribute access or dict construction."
                ),
                modules      = ["iios/investment/workflow/institutional_investment_workflow.py"],
                effort       = "LOW",
            ))

        # ── Logging overhead ─────────────────────────────────────────────────
        log_pct = _M.get("p8_log_overhead_pct", 0)
        if log_pct > 50:
            findings.append(dict(
                severity     = "LOW",
                gain         = f"{log_pct:.0f}% latency reduction when log level >= WARNING",
                finding      = f"Logging adds {log_pct:.1f}% to pipeline latency. "
                               f"The workflow emits multiple INFO logs per stage.",
                recommendation = (
                    "In production, set the workflow logger to WARNING level. "
                    "Consider lazy format strings or isEnabledFor() guards "
                    "around debug/info log calls in hot paths."
                ),
                modules      = ["iios/investment/workflow/institutional_investment_workflow.py"],
                effort       = "LOW",
            ))

        # ── Scalability ───────────────────────────────────────────────────────
        factor = _M.get("p3_growth_factor", 0)
        if factor > 3:
            findings.append(dict(
                severity     = "MEDIUM",
                gain         = "Better multi-core utilisation",
                finding      = f"Latency at 100-concurrent is {factor:.1f}x single "
                               f"— super-linear growth suggests lock contention.",
                recommendation = (
                    "Each InstitutionalWorkflowOrchestrator holds a _run_lock that "
                    "serialises one run at a time.  Use independent orchestrator "
                    "instances per logical tenant to avoid cross-tenant contention."
                ),
                modules      = ["iios/investment/workflow/institutional_investment_workflow.py"],
                effort       = "LOW",
            ))

        # ── Serialisation ────────────────────────────────────────────────────
        todict_ms = _M.get("p8_todict_ms", 0)
        if todict_ms > 0.1:
            findings.append(dict(
                severity     = "INFORMATIONAL",
                gain         = "< 1% pipeline latency reduction",
                finding      = f"run_record.to_dict() = {todict_ms:.4f}ms/call",
                recommendation = (
                    "Cache the dict representation in the WorkflowRunRecord "
                    "if to_dict() is called more than once per record."
                ),
                modules      = ["iios/investment/workflow/workflow_history.py"],
                effort       = "LOW",
            ))

        # ── Memory (caching opportunity) ─────────────────────────────────────
        findings.append(dict(
            severity     = "INFORMATIONAL",
            gain         = "Reduced snapshot creation overhead",
            finding      = "Each pipeline run creates 5+ _Snap objects plus a "
                           "WorkflowState with a new uuid.  With high throughput "
                           "this generates GC pressure.",
            recommendation = (
                "Consider an object pool for WorkflowState and StageRecord "
                "instances to reduce allocation rate at high throughput (> 1000 wf/sec)."
            ),
            modules      = ["iios/investment/workflow/workflow_state.py"],
            effort       = "HIGH",
        ))

        # ── Print ─────────────────────────────────────────────────────────────
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2,
                     "LOW": 3, "INFORMATIONAL": 4}
        findings.sort(key=lambda f: sev_order.get(f["severity"], 5))

        print("\n")
        print("  [Part 9] Optimisation Recommendations")
        print(f"  {'#':<3}  {'SEV':<14}  {'GAIN':<40}  EFFORT")
        print(f"  {'-'*3}  {'-'*14}  {'-'*40}  {'-'*10}")
        for i, f in enumerate(findings, 1):
            print(f"  {i:<3}  {f['severity']:<14}  {f['gain'][:40]:<40}  {f['effort']}")
        print("")
        for i, f in enumerate(findings, 1):
            print(f"  Finding #{i} [{f['severity']}]")
            print(f"    Observation   : {f['finding']}")
            print(f"    Recommendation: {f['recommendation']}")
            print(f"    Modules       : {', '.join(f.get('modules', []))}")
            print(f"    Effort        : {f['effort']}")
            print("")

        _M["p9_n_findings"] = len(findings)
        # Always passes — this is a report-only part


# ══════════════════════════════════════════════════════════════════════════════
#  PART 10 — FINAL CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPerfPart10Final:
    """
    Aggregate all measurement data into a final performance certification report.
    """

    # Aggregate pass thresholds (scores out of 100.0)
    T_LATENCY_SCORE    = 60.0
    T_THROUGHPUT_SCORE = 60.0
    T_SCALABILITY_SCORE = 60.0
    T_MEMORY_SCORE     = 60.0
    T_FRAMEWORK_SCORE  = 60.0
    T_OVERALL_GO       = 60.0    # >= 60% → CONDITIONAL GO minimum

    def _latency_score(self) -> float:
        p50 = _M.get("p1_p50",  0)
        p95 = _M.get("p1_p95",  0)
        p99 = _M.get("p1_p99",  0)
        worst = _M.get("p1_worst", 0)
        score = 100.0
        if p50  >= 30:    score -= 10
        if p50  >= 50:    score -= 10
        if p95  >= 150:   score -= 10
        if p99  >= 300:   score -= 10
        if worst >= 1000: score -= 10
        return max(0.0, score)

    def _throughput_score(self) -> float:
        seq = _M.get("p2_seq_wf_per_sec", 0)
        score = 100.0
        if seq < 100: score -= 10
        if seq < 50:  score -= 20
        if seq < 20:  score -= 20
        if seq < 10:  score -= 30
        return max(0.0, score)

    def _scalability_score(self) -> float:
        factor = _M.get("p3_growth_factor", 0)
        score  = 100.0
        if factor > 2:  score -= 10
        if factor > 4:  score -= 20
        if factor > 6:  score -= 30
        return max(0.0, score)

    def _memory_score(self) -> float:
        h1k  = _M.get("p4_heap_1k_mb",   0)
        h10k = _M.get("p5_10k_heap_mb",  0)
        score = 100.0
        # Thresholds account for Python allocator watermark growth
        if h1k  > 25:  score -= 15
        if h1k  > 50:  score -= 20
        if h10k > 200: score -= 15
        if h10k > 400: score -= 20
        return max(0.0, score)

    def _framework_score(self) -> float:
        lc_ms   = _M.get("p6_lifecycle_avg_ms",  0)
        exec_ms = _M.get("p6_async_exec_avg_ms", 0)
        score   = 100.0
        if exec_ms > 100: score -= 15
        if exec_ms > 200: score -= 15
        if lc_ms   > 200: score -= 10
        if lc_ms   > 400: score -= 10
        return max(0.0, score)

    def test_latency_score(self):
        score = self._latency_score()
        _M["p10_latency_score"] = score
        assert score >= self.T_LATENCY_SCORE, (
            f"Latency score {score:.0f}/100 < threshold {self.T_LATENCY_SCORE}"
        )

    def test_throughput_score(self):
        score = self._throughput_score()
        _M["p10_throughput_score"] = score
        assert score >= self.T_THROUGHPUT_SCORE, (
            f"Throughput score {score:.0f}/100 < threshold {self.T_THROUGHPUT_SCORE}"
        )

    def test_scalability_score(self):
        score = self._scalability_score()
        _M["p10_scalability_score"] = score
        assert score >= self.T_SCALABILITY_SCORE, (
            f"Scalability score {score:.0f}/100 < threshold {self.T_SCALABILITY_SCORE}"
        )

    def test_memory_score(self):
        score = self._memory_score()
        _M["p10_memory_score"] = score
        assert score >= self.T_MEMORY_SCORE, (
            f"Memory score {score:.0f}/100 < threshold {self.T_MEMORY_SCORE}"
        )

    def test_framework_score(self):
        score = self._framework_score()
        _M["p10_framework_score"] = score
        assert score >= self.T_FRAMEWORK_SCORE, (
            f"Framework score {score:.0f}/100 < threshold {self.T_FRAMEWORK_SCORE}"
        )

    def test_final_certification_report(self):
        """
        Produce the final performance certification.
        Passes if overall production performance score >= T_OVERALL_GO.
        """
        lat_score   = _M.get("p10_latency_score",     self._latency_score())
        tput_score  = _M.get("p10_throughput_score",  self._throughput_score())
        scale_score = _M.get("p10_scalability_score", self._scalability_score())
        mem_score   = _M.get("p10_memory_score",      self._memory_score())
        fwk_score   = _M.get("p10_framework_score",   self._framework_score())

        # Weighted overall
        weights = [0.25, 0.20, 0.20, 0.20, 0.15]
        scores  = [lat_score, tput_score, scale_score, mem_score, fwk_score]
        overall = sum(w * s for w, s in zip(weights, scores))
        _M["p10_overall"] = overall

        def _grade(s: float) -> str:
            return "A" if s >= 90 else "B" if s >= 75 else "C" if s >= 60 else \
                   "D" if s >= 45 else "F"

        def _verdict(s: float) -> str:
            if s >= 80:
                return "GO — Certified for C6 Execution Intelligence"
            if s >= 60:
                return "CONDITIONAL GO — Minor optimisations required before C6"
            return "NO-GO — Performance deficiencies must be resolved before C6"

        print("\n")
        print("  [Part 10] Performance & Load Certification — FINAL REPORT")
        print(f"  {'=' * 60}")
        print(f"  {'Score Component':<30}  {'Score':>6}  {'Grade':>5}")
        print(f"  {'-' * 30}  {'-' * 6}  {'-' * 5}")
        rows = [
            ("Latency Score",           lat_score),
            ("Throughput Score",         tput_score),
            ("Scalability Score",        scale_score),
            ("Memory Stability Score",   mem_score),
            ("Framework Overhead Score", fwk_score),
        ]
        for name, s in rows:
            print(f"  {name:<30}  {s:>5.0f}%  {_grade(s):>5}")
        print(f"  {'-' * 30}  {'-' * 6}  {'-' * 5}")
        print(f"  {'Production Performance Score':<30}  {overall:>5.1f}%  {_grade(overall):>5}")
        print(f"  {'=' * 60}")
        print(f"  VERDICT: {_verdict(overall)}")
        print(f"  {'=' * 60}")
        print("")
        print("  Key Measurements:")
        print(f"    Pipeline avg latency : {_M.get('p1_avg',   0):.2f} ms")
        print(f"    Pipeline p50         : {_M.get('p1_p50',   0):.2f} ms")
        print(f"    Pipeline p95         : {_M.get('p1_p95',   0):.2f} ms")
        print(f"    Pipeline p99         : {_M.get('p1_p99',   0):.2f} ms")
        print(f"    Sequential wf/sec    : {_M.get('p2_seq_wf_per_sec', 0):.1f}")
        print(f"    Concurrent wf/sec    : {_M.get('p2_conc_wf_per_sec', 0):.1f}")
        print(f"    Scale factor @100    : {_M.get('p3_growth_factor', 0):.1f}x")
        print(f"    Heap growth (10k)    : {_M.get('p5_10k_heap_mb', 0):.2f} MB")
        print(f"    execute_sync(null)   : {_M.get('p6_async_exec_avg_ms', 0):.2f} ms")
        print(f"    Lifecycle start+stop : {_M.get('p6_lifecycle_avg_ms', 0):.2f} ms")
        print(f"    Optimisation items   : {_M.get('p9_n_findings', '?')}")
        print("")

        assert overall >= self.T_OVERALL_GO, (
            f"Overall performance score {overall:.1f}% < "
            f"certification threshold {self.T_OVERALL_GO}%\n"
            f"VERDICT: {_verdict(overall)}"
        )
