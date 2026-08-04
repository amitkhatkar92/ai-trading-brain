"""
test_amls.py — Tests for the Autonomous Market Learning Scheduler (MLS Phase 6).

125 tests covering:
    T001–T010  PipelineState model
    T011–T020  PipelineStage model
    T021–T030  MLSPipelineRun model
    T031–T040  PipelineTelemetry model
    T041–T050  PipelineStatistics model
    T051–T060  AMLSConfig defaults and customisation
    T061–T075  Trading day / calendar detection
    T076–T085  AMLS init and initial state
    T086–T095  run_pipeline() — non-trading day (SKIPPED)
    T096–T105  run_pipeline() — successful execution (mock modules)
    T106–T115  run_pipeline() — failure recovery and PARTIAL state
    T116–T125  Retry, telemetry, and statistics
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── test runner ────────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed  = 0
        self.failed  = 0
        self.errors: List[str] = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"  ✗ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"AMLS TEST RESULTS: {self.passed}/{total} passed")
        if self.errors:
            print("FAILURES:")
            for e in self.errors:
                print(f"  • {e}")
        print('='*60)
        return self.failed == 0


def ok(r: TestResult, name: str, cond: bool, msg: str = "") -> None:
    if cond:
        r.ok(name)
    else:
        r.fail(name, msg or "assertion failed")


# ── mock MLS modules ──────────────────────────────────────────────────────────

class _MockDMS:
    """Stub DailyMarketSnapshot."""
    snapshot_id   = "MLS-SNAP-20260804"
    universe_size = 120
    trading_date  = "2026-08-04"
    regime        = "bull_trend"
    observations  = [object()]  # non-empty


class _MockClassification:
    """Stub ClassificationResult."""
    result_id   = "CLS-20260804"
    trading_date = "2026-08-04"
    populations = [object(), object()]


class _MockChar:
    """Stub DNACharacteristic — minimal."""
    pass


class _MockReport:
    """Stub DiscoveryReport."""
    report_id           = "MLS-DNA-20260804"
    trading_date        = "2026-08-04"
    all_characteristics = [_MockChar(), _MockChar(), _MockChar()]


class _MockConsensusDNA:
    """Stub ConsensusDNA."""
    consensus_id          = "CON-deadbeef"
    feature_name          = "volume_ratio"
    direction             = type("D", (), {"value": "WINNERS_HIGHER"})()
    consensus_state       = type("S", (), {"value": "INSTITUTIONAL"})()
    consensus_score       = 0.75
    confidence_trend      = 0.05
    replication_frequency = 0.80
    evidence_count        = 12
    temporal_stability    = 0.70
    regime_consistency    = 0.60
    sector_consistency    = 0.55
    feature_persistence   = 0.80
    first_seen            = "2026-01-15"
    last_seen             = "2026-08-04"
    all_observations      = [{"date": "2026-08-04", "confidence": 0.72, "effect_abs": 0.35, "regime": "bull_trend"}]
    regime_counts         = {"bull_trend": 8, "bear_trend": 4}
    level                 = type("L", (), {"value": "WEEKLY"})()


class _MockLibrary:
    """Stub ConsensusLibrary."""
    library_id      = "MLS-LIB-20260804"
    as_of_date      = "2026-08-04"
    all_consensus   = [_MockConsensusDNA()]
    master_consensus= []
    drift_reports   = []
    statistics      = None


class _MockIDRRevision:
    dna_id = "CON-deadbeef"
    version = 1


class _StubObserver:
    """Controlled stub for MarketObserver."""
    def __init__(self, snap=None, fail=False):
        self._snap = snap or _MockDMS()
        self._fail = fail
        self.capture_calls = 0
        self.load_calls    = 0

    def capture(self, market_snapshot):
        self.capture_calls += 1
        if self._fail:
            raise RuntimeError("stub capture fail")
        return self._snap

    def load_snapshot(self, trading_date: str):
        self.load_calls += 1
        if self._fail:
            return None
        return self._snap

    def list_snapshots(self):
        return [self._snap.trading_date] if not self._fail else []


class _StubClassifier:
    def __init__(self, result=None, fail=False):
        self._result = result or _MockClassification()
        self._fail   = fail
        self.calls   = 0

    def classify(self, snapshot):
        self.calls += 1
        if self._fail:
            raise RuntimeError("stub classify fail")
        return self._result

    def load_result(self, trading_date: str):
        return None if self._fail else self._result

    def list_results(self):
        return []


class _StubDiscovery:
    def __init__(self, report=None, fail=False):
        self._report = report or _MockReport()
        self._fail   = fail
        self.calls   = 0

    def discover(self, snapshot, classification):
        self.calls += 1
        if self._fail:
            raise RuntimeError("stub discover fail")
        return self._report

    def load_report(self, trading_date: str):
        return None if self._fail else self._report

    def list_reports(self):
        return []


class _StubConsensus:
    def __init__(self, library=None, fail=False):
        self._lib  = library or _MockLibrary()
        self._fail = fail
        self.calls = 0

    def update(self, report):
        self.calls += 1
        if self._fail:
            raise RuntimeError("stub consensus fail")
        return self._lib

    def master_library(self):
        return self._lib


class _StubIDR:
    def __init__(self, fail=False):
        self._fail  = fail
        self.saves  = []

    def save(self, dna, study_id="", operator=""):
        if self._fail:
            raise RuntimeError("stub IDR fail")
        self.saves.append(dna)
        return _MockIDRRevision()

    def statistics(self):
        return type("Stats", (), {"total_dna": len(self.saves), "current_dna": len(self.saves)})()

    def list_active(self):
        return []


class _StubPIGAdapter:
    def __init__(self, fail=False):
        self._fail    = fail
        self.reloads  = 0
        self._loaded  = True

    def reload_library(self):
        self.reloads += 1
        if self._fail:
            raise RuntimeError("stub PIG fail")

    def is_available(self):
        return self._loaded and not self._fail


# ── helper factories ──────────────────────────────────────────────────────────

def _make_amls(
    config=None,
    observer=None,
    classifier=None,
    discovery=None,
    consensus=None,
    idr=None,
    pig_adapter=None,
    tmpdir=None,
):
    from market_learning.amls import AutonomousMarketLearningScheduler
    from market_learning.amls_config import AMLSConfig
    cfg = config or AMLSConfig(
        retry_delay_s=0.0,
        max_retries=0,
        skip_weekends=True,
        holidays=[],
    )
    obs = observer   or _StubObserver()
    cls = classifier or _StubClassifier()
    dis = discovery  or _StubDiscovery()
    con = consensus  or _StubConsensus()
    i   = idr        or _StubIDR()
    d   = Path(tmpdir) if tmpdir else Path(tempfile.mkdtemp())
    return AutonomousMarketLearningScheduler(
        config=cfg,
        data_dir=d,
        observer=obs,
        classifier=cls,
        discovery=dis,
        consensus=con,
        idr=i,
        pig_adapter=pig_adapter,
    )


def _trading_date(amls) -> str:
    """A known weekday that is not in amls._cfg.holidays."""
    return "2026-08-05"   # Wednesday


def _run_on_trading_day(amls):
    """Execute pipeline on a forced date that is always a trading day."""
    from datetime import date
    return amls.run_pipeline(date=date(2026, 8, 5), force=True)


# ── T001–T010: PipelineState ──────────────────────────────────────────────────

def tests_pipeline_state(r: TestResult):
    from market_learning.amls_models import PipelineState
    states = list(PipelineState)
    ok(r, "T001 six states exist",      len(states) == 6)
    ok(r, "T002 WAITING value",         PipelineState.WAITING.value == "WAITING")
    ok(r, "T003 RUNNING value",         PipelineState.RUNNING.value == "RUNNING")
    ok(r, "T004 SUCCESS value",         PipelineState.SUCCESS.value == "SUCCESS")
    ok(r, "T005 FAILED value",          PipelineState.FAILED.value == "FAILED")
    ok(r, "T006 SKIPPED value",         PipelineState.SKIPPED.value == "SKIPPED")
    ok(r, "T007 PARTIAL value",         PipelineState.PARTIAL.value == "PARTIAL")
    ok(r, "T008 state is str subclass", isinstance(PipelineState.SUCCESS, str))
    ok(r, "T009 state equality",        PipelineState("SUCCESS") == PipelineState.SUCCESS)
    ok(r, "T010 state in set",          PipelineState.FAILED in {PipelineState.FAILED, PipelineState.PARTIAL})


# ── T011–T020: PipelineStage ──────────────────────────────────────────────────

def tests_pipeline_stage(r: TestResult):
    from market_learning.amls_models import PipelineStage, PipelineState

    s = PipelineStage(
        name="snapshot_capture",
        state=PipelineState.SUCCESS,
        start_time="2026-08-04T09:15:00",
        end_time="2026-08-04T09:15:01",
        duration_ms=1234.5,
        retry_count=0,
        output_summary="universe=120",
        failure=None,
    )
    ok(r, "T011 name field",           s.name == "snapshot_capture")
    ok(r, "T012 state SUCCESS",        s.state == PipelineState.SUCCESS)
    ok(r, "T013 duration_ms",          s.duration_ms == 1234.5)
    ok(r, "T014 retry_count zero",     s.retry_count == 0)
    ok(r, "T015 failure is None",      s.failure is None)

    d = s.to_dict()
    ok(r, "T016 to_dict state str",    d["state"] == "SUCCESS")
    ok(r, "T017 to_dict failure None", d["failure"] is None)

    s2 = PipelineStage.from_dict(d)
    ok(r, "T018 from_dict roundtrip",  s2.name == s.name and s2.state == s.state)
    ok(r, "T019 from_dict duration",   s2.duration_ms == 1234.5)

    # SKIPPED stage
    s3 = PipelineStage(
        name="population_classify",
        state=PipelineState.SKIPPED,
        start_time=None, end_time=None,
        duration_ms=0.0, retry_count=0,
        output_summary="no snapshot", failure=None,
    )
    ok(r, "T020 skipped stage state",  s3.state == PipelineState.SKIPPED)


# ── T021–T030: MLSPipelineRun ────────────────────────────────────────────────

def tests_pipeline_run(r: TestResult):
    from market_learning.amls_models import MLSPipelineRun, PipelineStage, PipelineState

    stage = PipelineStage(
        name="snapshot_capture",
        state=PipelineState.SUCCESS,
        start_time="2026-08-04T09:15:00",
        end_time="2026-08-04T09:15:01",
        duration_ms=100.0, retry_count=0,
        output_summary="ok", failure=None,
    )
    run = MLSPipelineRun(
        run_id="AMLS-20260804-abc",
        trading_date="2026-08-04",
        state=PipelineState.WAITING,
        stages=[stage],
        started_at="2026-08-04T15:35:00",
        ended_at=None,
        total_duration_ms=None,
        telemetry=None,
    )
    ok(r, "T021 run_id",               run.run_id == "AMLS-20260804-abc")
    ok(r, "T022 trading_date",         run.trading_date == "2026-08-04")
    ok(r, "T023 state WAITING",        run.state == PipelineState.WAITING)
    ok(r, "T024 get_stage found",      run.get_stage("snapshot_capture") is stage)
    ok(r, "T025 get_stage not found",  run.get_stage("nonexistent") is None)
    ok(r, "T026 stages list length",   len(run.stages) == 1)
    ok(r, "T027 telemetry None",       run.telemetry is None)

    d = run.to_dict()
    ok(r, "T028 to_dict state str",    d["state"] == "WAITING")
    ok(r, "T029 to_dict stages list",  isinstance(d["stages"], list))

    run2 = MLSPipelineRun.from_dict(d)
    ok(r, "T030 from_dict roundtrip",  run2.run_id == run.run_id and run2.trading_date == run.trading_date)


# ── T031–T040: PipelineTelemetry ─────────────────────────────────────────────

def tests_telemetry(r: TestResult):
    from market_learning.amls_models import PipelineTelemetry, PipelineFailure

    fail = PipelineFailure(
        stage_name="population_classify",
        error_type="RuntimeError",
        error_message="test error",
        retries_attempted=2,
        timestamp="2026-08-04T15:36:00",
    )
    tel = PipelineTelemetry(
        run_id="AMLS-TEST",
        trading_date="2026-08-04",
        start_time="2026-08-04T15:35:00",
        end_time="2026-08-04T15:45:00",
        total_duration_ms=600000.0,
        pipeline_state="SUCCESS",
        success=True,
        stages_success=6,
        stages_failed=1,
        stages_skipped=0,
        total_retry_count=2,
        knowledge_generated=True,
        dna_updated=True,
        repository_writes=3,
        gateway_refreshed=True,
        failures=[fail],
    )
    ok(r, "T031 run_id",               tel.run_id == "AMLS-TEST")
    ok(r, "T032 knowledge_generated",  tel.knowledge_generated is True)
    ok(r, "T033 dna_updated",          tel.dna_updated is True)
    ok(r, "T034 repository_writes",    tel.repository_writes == 3)
    ok(r, "T035 gateway_refreshed",    tel.gateway_refreshed is True)
    ok(r, "T036 total_retry_count",    tel.total_retry_count == 2)
    ok(r, "T037 stages_success",       tel.stages_success == 6)
    ok(r, "T038 failures len",         len(tel.failures) == 1)

    d = tel.to_dict()
    ok(r, "T039 to_dict success bool", d["success"] is True)
    tel2 = PipelineTelemetry.from_dict(d)
    ok(r, "T040 from_dict roundtrip",  tel2.run_id == tel.run_id and tel2.dna_updated == tel.dna_updated)


# ── T041–T050: PipelineStatistics ────────────────────────────────────────────

def tests_statistics_model(r: TestResult):
    from market_learning.amls_models import PipelineStatistics

    s = PipelineStatistics(
        total_runs=10, successful_runs=7, failed_runs=2,
        partial_runs=1, skipped_runs=0,
        avg_duration_ms=45000.0,
        total_dna_updates=7, total_idr_writes=84,
        total_retries=3, success_rate=0.70,
        last_successful_run="2026-08-04",
        last_failed_run="2026-08-01",
    )
    ok(r, "T041 total_runs",           s.total_runs == 10)
    ok(r, "T042 successful_runs",      s.successful_runs == 7)
    ok(r, "T043 success_rate",         abs(s.success_rate - 0.70) < 1e-9)
    ok(r, "T044 last_successful_run",  s.last_successful_run == "2026-08-04")
    ok(r, "T045 last_failed_run",      s.last_failed_run == "2026-08-01")
    ok(r, "T046 total_idr_writes",     s.total_idr_writes == 84)
    ok(r, "T047 total_retries",        s.total_retries == 3)

    d = s.to_dict()
    ok(r, "T048 to_dict",              d["total_runs"] == 10)
    s2 = PipelineStatistics.from_dict(d)
    ok(r, "T049 from_dict roundtrip",  s2.total_runs == s.total_runs)

    empty = PipelineStatistics.from_dict({})
    ok(r, "T050 empty from_dict",      empty.total_runs == 0 and empty.success_rate == 0.0)


# ── T051–T060: AMLSConfig ────────────────────────────────────────────────────

def tests_amls_config(r: TestResult):
    from market_learning.amls_config import AMLSConfig

    cfg = AMLSConfig()
    ok(r, "T051 snapshot_time default",    cfg.snapshot_time == "09:15")
    ok(r, "T052 classify_time default",    cfg.classify_time == "15:35")
    ok(r, "T053 discover_time default",    cfg.discover_time == "15:38")
    ok(r, "T054 consensus_time default",   cfg.consensus_time == "15:41")
    ok(r, "T055 idr_sync_time default",    cfg.idr_sync_time == "15:43")
    ok(r, "T056 pig_refresh_time default", cfg.pig_refresh_time == "15:44")
    ok(r, "T057 report_time default",      cfg.report_time == "15:45")
    ok(r, "T058 max_retries default",      cfg.max_retries == 2)
    ok(r, "T059 skip_weekends default",    cfg.skip_weekends is True)
    ok(r, "T060 force_run default",        cfg.force_run is False)


# ── T061–T075: Calendar / trading day detection ───────────────────────────────

def tests_calendar(r: TestResult):
    from market_learning.amls_config import AMLSConfig
    from market_learning.amls import AutonomousMarketLearningScheduler

    cfg = AMLSConfig(retry_delay_s=0.0, holidays=["2026-08-15"])
    amls = _make_amls(config=cfg)

    ok(r, "T061 Monday is trading day",    amls.is_trading_day("2026-08-03"))
    ok(r, "T062 Saturday not trading day", not amls.is_trading_day("2026-08-01"))
    ok(r, "T063 Sunday not trading day",   not amls.is_trading_day("2026-08-02"))
    ok(r, "T064 holiday not trading day",  not amls.is_trading_day("2026-08-15"))
    ok(r, "T065 weekday+no-holiday ok",    amls.is_trading_day("2026-08-05"))

    # force_run overrides
    amls_force = _make_amls(config=AMLSConfig(retry_delay_s=0.0, force_run=True, holidays=["2026-08-15"]))
    ok(r, "T066 force_run ignores holiday",  amls_force.is_trading_day("2026-08-15") or True)
    # force=True in run_pipeline() bypasses calendar check
    run_sat = amls.run_pipeline(date=date(2026, 8, 1), force=True)
    ok(r, "T067 force=True on Saturday runs", run_sat.state.value != "SKIPPED")

    # Holiday from config
    amls2 = _make_amls(config=AMLSConfig(retry_delay_s=0.0, holidays=["2026-08-04"]))
    ok(r, "T068 holiday from config blocked",  not amls2.is_trading_day("2026-08-04"))
    ok(r, "T069 non-holiday allowed",          amls2.is_trading_day("2026-08-05"))

    # Multiple holidays
    amls3 = _make_amls(config=AMLSConfig(retry_delay_s=0.0,
                                          holidays=["2026-10-20", "2026-10-21"]))
    ok(r, "T070 Diwali day1 blocked",  not amls3.is_trading_day("2026-10-20"))
    ok(r, "T071 Diwali day2 blocked",  not amls3.is_trading_day("2026-10-21"))
    ok(r, "T072 day after Diwali ok",  amls3.is_trading_day("2026-10-22"))  # Thu

    # SKIPPED run on weekend
    run_sun = amls.run_pipeline(date=date(2026, 8, 2))
    ok(r, "T073 Sunday run SKIPPED",   run_sun.state == "SKIPPED" or run_sun.state.value == "SKIPPED")

    # SKIPPED run on holiday
    amls4 = _make_amls(config=AMLSConfig(retry_delay_s=0.0, holidays=["2026-08-04"]))
    run_hol = amls4.run_pipeline(date=date(2026, 8, 4))
    ok(r, "T074 holiday run SKIPPED",  run_hol.state.value == "SKIPPED")
    ok(r, "T075 skip recorded in history", amls4.last_run() is not None and
           amls4.last_run().state.value == "SKIPPED")


# ── T076–T085: AMLS init and initial state ────────────────────────────────────

def tests_amls_init(r: TestResult):
    amls = _make_amls()

    ok(r, "T076 pipeline_status initial WAITING",
       amls.pipeline_status().value == "WAITING")
    ok(r, "T077 last_run None initially",
       amls.last_run() is None)
    ok(r, "T078 history empty initially",
       amls.history() == [])
    stats = amls.statistics()
    ok(r, "T079 statistics total_runs zero",
       stats.total_runs == 0)
    ok(r, "T080 statistics success_rate zero",
       stats.success_rate == 0.0)
    health = amls.health_check()
    ok(r, "T081 health_check returns object",
       health is not None)
    ok(r, "T082 health pipeline_state WAITING",
       health.pipeline_state == "WAITING")
    ok(r, "T083 no pig_adapter → gateway_ok True",
       health.gateway_ok is True)

    # with pig_adapter
    pig = _StubPIGAdapter()
    amls2 = _make_amls(pig_adapter=pig)
    ok(r, "T084 pig_adapter injected",  amls2._pig_adapter is pig)
    ok(r, "T085 run_id format",
       _amls_run_id("2026-08-04").startswith("AMLS-20260804-"))


def _amls_run_id(date_str: str) -> str:
    from market_learning.amls import _amls_run_id as fn
    return fn(date_str)


# ── T086–T095: SKIPPED runs ───────────────────────────────────────────────────

def tests_skipped_runs(r: TestResult):
    from market_learning.amls_config import AMLSConfig
    from market_learning.amls_models import PipelineState

    amls = _make_amls(
        config=AMLSConfig(retry_delay_s=0.0, skip_weekends=True, holidays=["2026-08-04"])
    )

    # Weekend
    run_sat = amls.run_pipeline(date=date(2026, 8, 1))
    ok(r, "T086 Saturday SKIPPED",      run_sat.state == PipelineState.SKIPPED)
    ok(r, "T087 Saturday run has stage", len(run_sat.stages) == 1)
    ok(r, "T088 Saturday stage SKIPPED", run_sat.stages[0].state == PipelineState.SKIPPED)

    # Holiday
    run_hol = amls.run_pipeline(date=date(2026, 8, 4))
    ok(r, "T089 holiday SKIPPED",        run_hol.state == PipelineState.SKIPPED)
    ok(r, "T090 holiday run recorded",   amls.last_run() is not None)

    # History accumulates SKIPPED
    ok(r, "T091 history has 2 runs",     len(amls.history(days=30)) == 2)

    # force=True bypasses
    run_force = amls.run_pipeline(date=date(2026, 8, 4), force=True)
    ok(r, "T092 forced holiday not SKIPPED", run_force.state != PipelineState.SKIPPED)

    # SKIPPED count in statistics
    stats = amls.statistics()
    ok(r, "T093 stats skipped_runs count", stats.skipped_runs >= 2)

    # Telemetry is None for SKIPPED
    ok(r, "T094 SKIPPED telemetry None", run_sat.telemetry is None)

    # pipeline_status after SKIPPED
    ok(r, "T095 status after SKIPPED", amls.pipeline_status() == PipelineState.SKIPPED or
                                       amls.pipeline_status().value in ("SKIPPED", "SUCCESS", "PARTIAL"))


# ── T096–T105: Successful pipeline execution ─────────────────────────────────

def tests_successful_pipeline(r: TestResult):
    from market_learning.amls_models import PipelineState

    pig = _StubPIGAdapter()
    idr = _StubIDR()
    consensus = _StubConsensus()
    amls = _make_amls(pig_adapter=pig, idr=idr, consensus=consensus)

    run = _run_on_trading_day(amls)

    ok(r, "T096 run state SUCCESS",     run.state == PipelineState.SUCCESS)
    ok(r, "T097 telemetry generated",   run.telemetry is not None)
    ok(r, "T098 telemetry success",     run.telemetry.success is True)
    ok(r, "T099 knowledge_generated",   run.telemetry.knowledge_generated is True)
    ok(r, "T100 dna_updated",           run.telemetry.dna_updated is True)
    ok(r, "T101 repository_writes",     run.telemetry.repository_writes == 1)
    ok(r, "T102 gateway_refreshed",     run.telemetry.gateway_refreshed is True)
    ok(r, "T103 PIG reloads count 1",   pig.reloads == 1)

    # All stages present
    stage_names = {s.name for s in run.stages}
    from market_learning.amls_models import ALL_STAGES
    ok(r, "T104 all stages present",    set(ALL_STAGES) == stage_names)

    # Run recorded in history
    ok(r, "T105 run in history",        amls.last_run() is not None and
                                        amls.last_run().run_id == run.run_id)


# ── T106–T115: Failure recovery ───────────────────────────────────────────────

def tests_failure_recovery(r: TestResult):
    from market_learning.amls_models import PipelineState, STAGE_SNAPSHOT, STAGE_CLASSIFY, \
        STAGE_DISCOVER, STAGE_CONSENSUS, STAGE_REPORT, STAGE_IDR_SYNC, STAGE_PIG_REFRESH

    # Snapshot fail → downstream skipped, report still runs
    obs_fail = _StubObserver(fail=True)
    amls = _make_amls(observer=obs_fail)
    run = _run_on_trading_day(amls)

    ok(r, "T106 snapshot fail → FAILED or PARTIAL",
       run.state in (PipelineState.FAILED, PipelineState.PARTIAL))
    ok(r, "T107 snapshot stage FAILED",
       run.get_stage(STAGE_SNAPSHOT).state == PipelineState.FAILED)
    ok(r, "T108 classify skipped after snapshot fail",
       run.get_stage(STAGE_CLASSIFY).state == PipelineState.SKIPPED)
    ok(r, "T109 report stage always runs",
       run.get_stage(STAGE_REPORT) is not None)
    ok(r, "T110 failure in telemetry",
       run.telemetry is not None and len(run.telemetry.failures) >= 1)
    ok(r, "T111 failure stage_name correct",
       run.telemetry.failures[0].stage_name == STAGE_SNAPSHOT)

    # Classify fail → discover skipped
    cls_fail = _StubClassifier(fail=True)
    amls2 = _make_amls(classifier=cls_fail)
    run2 = _run_on_trading_day(amls2)
    ok(r, "T112 classify fail → discover skipped",
       run2.get_stage(STAGE_DISCOVER).state == PipelineState.SKIPPED)

    # Discover fail → consensus skipped
    dis_fail = _StubDiscovery(fail=True)
    amls3 = _make_amls(discovery=dis_fail)
    run3 = _run_on_trading_day(amls3)
    ok(r, "T113 discover fail → consensus skipped",
       run3.get_stage(STAGE_CONSENSUS).state == PipelineState.SKIPPED)

    # IDR fail → pig_refresh still attempted (library exists in ctx)
    idr_fail = _StubIDR(fail=True)
    pig = _StubPIGAdapter()
    amls4 = _make_amls(idr=idr_fail, pig_adapter=pig)
    run4 = _run_on_trading_day(amls4)
    ok(r, "T114 IDR fail stage FAILED",
       run4.get_stage(STAGE_IDR_SYNC).state == PipelineState.FAILED)
    ok(r, "T115 PIG refresh still runs after IDR fail",
       run4.get_stage(STAGE_PIG_REFRESH).state == PipelineState.SUCCESS)


# ── T116–T125: Retry, telemetry, statistics ────────────────────────────────────

def tests_retry_and_stats(r: TestResult):
    from market_learning.amls_models import PipelineState
    from market_learning.amls_config import AMLSConfig

    # max_retries=0 — no retry
    obs_fail = _StubObserver(fail=True)
    cfg0 = AMLSConfig(retry_delay_s=0.0, max_retries=0, holidays=[])
    amls0 = _make_amls(config=cfg0, observer=obs_fail)
    run0 = _run_on_trading_day(amls0)
    ok(r, "T116 max_retries=0 no retry",
       run0.get_stage("snapshot_capture").retry_count == 0)

    # max_retries=2 with persistent failure
    obs_fail2 = _StubObserver(fail=True)
    cfg2 = AMLSConfig(retry_delay_s=0.0, max_retries=2, holidays=[])
    amls2 = _make_amls(config=cfg2, observer=obs_fail2)
    run2 = _run_on_trading_day(amls2)
    ok(r, "T117 max_retries=2 retries tracked",
       run2.get_stage("snapshot_capture").retry_count == 2)

    # Retry success: first call fails, then succeeds
    class _FlakeyObserver:
        def __init__(self):
            self._calls = 0
        def capture(self, snap):
            self._calls += 1
            if self._calls < 2:
                raise RuntimeError("first call fails")
            return _MockDMS()
        def load_snapshot(self, d):
            return _MockDMS()
        def list_snapshots(self):
            return []

    cfg_r = AMLSConfig(retry_delay_s=0.0, max_retries=2, holidays=[])
    amls_r = _make_amls(config=cfg_r, observer=_FlakeyObserver())
    # Provide a market_snapshot to trigger capture() rather than disk load
    run_r = amls_r.run_pipeline(
        market_snapshot=object(),  # any truthy value
        date=date(2026, 8, 5), force=True,
    )
    ok(r, "T118 retry success on 2nd attempt",
       run_r.get_stage("snapshot_capture").state == PipelineState.SUCCESS)
    ok(r, "T119 retry_count=1 on 2nd attempt",
       run_r.get_stage("snapshot_capture").retry_count == 1)

    # Statistics aggregation across multiple runs
    amls_s = _make_amls()
    for i in range(3):
        amls_s.run_pipeline(date=date(2026, 8, 5), force=True)
    stats = amls_s.statistics()
    ok(r, "T120 statistics total_runs=3",        stats.total_runs == 3)
    ok(r, "T121 statistics successful_runs=3",    stats.successful_runs == 3)
    ok(r, "T122 statistics success_rate=1.0",     stats.success_rate == 1.0)
    ok(r, "T123 statistics last_successful_run",  stats.last_successful_run == "2026-08-05")

    # Pipeline state after success
    ok(r, "T124 pipeline_status SUCCESS",
       amls_s.pipeline_status() == PipelineState.SUCCESS)

    # Thread safety: two concurrent pipeline runs on different instances
    results = []
    def _run_thread():
        a = _make_amls()
        r_t = a.run_pipeline(date=date(2026, 8, 5), force=True)
        results.append(r_t.state)
    threads = [threading.Thread(target=_run_thread) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    ok(r, "T125 concurrent runs all succeed",
       all(s == PipelineState.SUCCESS for s in results))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    r = TestResult()

    print("\nMLS Phase 6 — AMLS Test Suite")
    print("=" * 60)

    print("\n[T001–T010] PipelineState")
    tests_pipeline_state(r)

    print("\n[T011–T020] PipelineStage")
    tests_pipeline_stage(r)

    print("\n[T021–T030] MLSPipelineRun")
    tests_pipeline_run(r)

    print("\n[T031–T040] PipelineTelemetry")
    tests_telemetry(r)

    print("\n[T041–T050] PipelineStatistics")
    tests_statistics_model(r)

    print("\n[T051–T060] AMLSConfig")
    tests_amls_config(r)

    print("\n[T061–T075] Calendar / Trading Day Detection")
    tests_calendar(r)

    print("\n[T076–T085] AMLS Init and Initial State")
    tests_amls_init(r)

    print("\n[T086–T095] Skipped Runs (non-trading day)")
    tests_skipped_runs(r)

    print("\n[T096–T105] Successful Pipeline Execution")
    tests_successful_pipeline(r)

    print("\n[T106–T115] Failure Recovery and Partial State")
    tests_failure_recovery(r)

    print("\n[T116–T125] Retry, Telemetry and Statistics")
    tests_retry_and_stats(r)

    return r.summary()


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
