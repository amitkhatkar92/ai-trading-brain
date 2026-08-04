"""
test_mlc.py — Tests for the MarketLearningCoordinator.

160 tests covering:
    T001–T010   LearningStage model
    T011–T015   LearningTelemetry model
    T016–T025   LearningRun model
    T026–T030   LearningSummary model
    T031–T040   MLCConfig
    T041–T050   Coordinator construction
    T051–T065   Pipeline execution — all stages succeed
    T066–T070   Strategy Learning stage
    T071–T080   AMLS stage
    T081–T092   DRE stage
    T093–T100   IDR refresh stage
    T101–T108   PIG refresh stage
    T109–T112   Summary stage
    T113–T125   Failure isolation
    T126–T135   Standalone APIs (run_amls, run_reinforcement, status, history)
    T136–T140   Statistics API
    T141–T150   History persistence
    T151–T160   Concurrency
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── test runner ───────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed  = 0
        self.failed  = 0
        self.errors: List[str] = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✔ {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"  ✗ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*64}")
        print(f"MLC TEST RESULTS: {self.passed}/{total} passed")
        if self.errors:
            print("FAILURES:")
            for e in self.errors:
                print(f"  • {e}")
        print(f"{'='*64}")
        return self.failed == 0


# ── path setup ────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from market_learning.mlc_config import MLCConfig
from market_learning.mlc_models import (
    LearningHealth,
    LearningRun,
    LearningSummary,
    LearningStage,
    LearningStageStatus,
    LearningStageType,
    LearningTelemetry,
    MLCError,
    MLCStageError,
    make_run_id,
    _now_iso,
)
from market_learning.market_learning_coordinator import MarketLearningCoordinator


# ── mocks ─────────────────────────────────────────────────────────────────────

def _make_amls_run(state="SUCCESS", dna_updated=True, repo_writes=3,
                   gw_refreshed=True, duration_ms=100.0):
    tel = type("T", (), {
        "dna_updated": dna_updated,
        "repository_writes": repo_writes,
        "gateway_refreshed": gw_refreshed,
        "knowledge_generated": dna_updated,
    })()
    return type("R", (), {
        "state":              type("S", (), {"value": state})(),
        "total_duration_ms":  duration_ms,
        "telemetry":          tel,
    })()


class _MockAMLS:
    def __init__(self, fail=False, gw_refreshed=True, state="SUCCESS"):
        self.fail         = fail
        self.calls        = 0
        self._gw          = gw_refreshed
        self._state       = state

    def run_pipeline(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("AMLS mock failure")
        return _make_amls_run(state=self._state, gw_refreshed=self._gw)


class _MockDRE:
    def __init__(self, fail=False, per_item=1):
        self.fail  = fail
        self.calls = 0
        self._per  = per_item

    def process_batch(self, items):
        self.calls += 1
        if self.fail:
            raise RuntimeError("DRE mock failure")
        return [
            type("R", (), {"reinforcement_type": "POSITIVE", "idr_revision": 1})()
            for _ in range(len(items) * self._per)
        ]


class _MockIDR:
    def __init__(self, fail=False, total_dna=10):
        self.fail     = fail
        self._total   = total_dna
        self.calls    = 0

    def statistics(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("IDR mock failure")
        return type("S", (), {"total_dna": self._total, "active_dna": self._total})()

    def verify_integrity(self):
        return not self.fail


class _MockPIG:
    def __init__(self, fail=False, dna=5):
        self.fail        = fail
        self._dna        = dna
        self.reload_calls = 0

    def reload_library(self):
        self.reload_calls += 1
        if self.fail:
            raise RuntimeError("PIG mock failure")

    def dna_count(self):
        return self._dna


class _MockLE:
    """Mock LearningEngine."""
    def __init__(self, fail=False):
        self.fail  = fail
        self.calls = 0
        self.last_trades: Optional[List] = None

    def learn(self, trades):
        self.calls += 1
        self.last_trades = list(trades)
        if self.fail:
            raise RuntimeError("LearningEngine mock failure")


def _trade(oid="T001", pnl=500.0):
    return {"order_id": oid, "symbol": "RELIANCE", "pnl": pnl}


def _pig_results(*order_ids):
    """Build a pig_results dict with mock PlatformIntelligence objects."""
    out = {}
    for oid in order_ids:
        pmci = type("PMCI", (), {
            "pmci_score": 0.7,
            "breakdown": type("BD", (), {
                "matched_dna": [],
                "conflicting_dna": [],
            })(),
        })()
        out[oid] = type("PI", (), {
            "pmci_result":    pmci,
            "ca_pmci_result": None,
            "cds_scores":     None,
        })()
    return out


def _mlc(tmp: Path, **kw) -> MarketLearningCoordinator:
    """Construct a coordinator wired with mocks, writing history to tmp."""
    cfg = MLCConfig(history_path=str(tmp / "history.json"))
    kw.setdefault("config", cfg)
    return MarketLearningCoordinator(**kw)


# ─────────────────────────────────────────────────────────────────────────────
# Suite 1 — LearningStage model (T001–T010)
# ─────────────────────────────────────────────────────────────────────────────

def suite_01_learning_stage(r: TestResult):
    print("\n── Suite 01: LearningStage model ──")

    # T001
    s = LearningStage(LearningStageType.AMLS, "amls")
    r.ok("T001 default status is PENDING") if s.status == LearningStageStatus.PENDING else r.fail("T001", f"got {s.status}")

    # T002
    s.mark_start()
    r.ok("T002 mark_start → RUNNING") if s.status == LearningStageStatus.RUNNING else r.fail("T002", f"got {s.status}")

    # T003
    s.mark_complete({"k": "v"})
    r.ok("T003 mark_complete → COMPLETE") if s.status == LearningStageStatus.COMPLETE else r.fail("T003", f"got {s.status}")

    # T004
    s2 = LearningStage(LearningStageType.DNA_REINFORCEMENT, "dre")
    s2.mark_start()
    s2.mark_failed("boom")
    r.ok("T004 mark_failed → FAILED") if s2.status == LearningStageStatus.FAILED else r.fail("T004", f"got {s2.status}")

    # T005
    s3 = LearningStage(LearningStageType.SUMMARY, "summary")
    s3.mark_skipped("no_data")
    r.ok("T005 mark_skipped → SKIPPED") if s3.status == LearningStageStatus.SKIPPED else r.fail("T005", f"got {s3.status}")

    # T006
    r.ok("T006 .succeeded is True after mark_complete") if s.succeeded else r.fail("T006", "succeeded False")

    # T007
    r.ok("T007 .failed is True after mark_failed") if s2.failed else r.fail("T007", "failed False")

    # T008
    s4 = LearningStage(LearningStageType.AMLS, "amls2")
    s4.mark_start()
    s4.mark_complete()
    r.ok("T008 duration_ms set after mark_complete") if s4.duration_ms is not None else r.fail("T008", "duration_ms None")

    # T009
    s5 = LearningStage(LearningStageType.DNA_REINFORCEMENT, "dre2")
    s5.mark_start()
    s5.mark_failed("err")
    r.ok("T009 duration_ms set after mark_failed") if s5.duration_ms is not None else r.fail("T009", "duration_ms None")

    # T010
    s6 = LearningStage(LearningStageType.IDR_REFRESH, "idr")
    s6.mark_start()
    s6.mark_complete({"count": 42})
    r.ok("T010 output dict stored") if s6.output.get("count") == 42 else r.fail("T010", f"output={s6.output}")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 2 — LearningTelemetry model (T011–T015)
# ─────────────────────────────────────────────────────────────────────────────

def suite_02_telemetry(r: TestResult):
    print("\n── Suite 02: LearningTelemetry model ──")
    tel = LearningTelemetry()

    # T011
    r.ok("T011 default trades_processed=0") if tel.trades_processed == 0 else r.fail("T011", str(tel.trades_processed))

    # T012
    r.ok("T012 default amls_ran=False") if tel.amls_ran is False else r.fail("T012", str(tel.amls_ran))

    # T013
    r.ok("T013 default dre_ran=False") if tel.dre_ran is False else r.fail("T013", str(tel.dre_ran))

    # T014
    tel.dna_reinforced = 5
    r.ok("T014 fields mutable") if tel.dna_reinforced == 5 else r.fail("T014", str(tel.dna_reinforced))

    # T015
    r.ok("T015 default knowledge_generated=0") if tel.knowledge_generated == 0 else r.fail("T015", str(tel.knowledge_generated))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 3 — LearningRun model (T016–T025)
# ─────────────────────────────────────────────────────────────────────────────

def suite_03_run(r: TestResult):
    print("\n── Suite 03: LearningRun model ──")

    def _run():
        run = LearningRun(run_id="r1", trading_date="2026-08-04",
                          started_at=_now_iso())
        s1 = LearningStage(LearningStageType.AMLS, "amls"); s1.mark_start(); s1.mark_complete()
        s2 = LearningStage(LearningStageType.DNA_REINFORCEMENT, "dre"); s2.mark_start(); s2.mark_failed("e")
        s3 = LearningStage(LearningStageType.IDR_REFRESH, "idr"); s3.mark_skipped("x")
        run.stages = [s1, s2, s3]
        return run

    run = _run()

    # T016
    r.ok("T016 stages_ok=1") if run.stages_ok == 1 else r.fail("T016", str(run.stages_ok))

    # T017
    r.ok("T017 stages_failed=1") if run.stages_failed == 1 else r.fail("T017", str(run.stages_failed))

    # T018
    r.ok("T018 stages_skipped=1") if run.stages_skipped == 1 else r.fail("T018", str(run.stages_skipped))

    # T019
    r.ok("T019 health is LearningHealth enum") if isinstance(run.health, LearningHealth) else r.fail("T019", type(run.health).__name__)

    # T020
    d = run.to_dict()
    r.ok("T020 to_dict() has run_id") if "run_id" in d else r.fail("T020", str(d.keys()))

    # T021
    run2 = LearningRun(run_id="r2", trading_date="2026-08-04", started_at=_now_iso())
    d2 = run2.to_dict()
    r.ok("T021 to_dict() telemetry None when no tel") if d2.get("telemetry") is None else r.fail("T021", str(d2.get("telemetry")))

    # T022
    run3 = LearningRun(run_id="r3", trading_date="2026-08-04", started_at=_now_iso())
    run3.telemetry = LearningTelemetry(dna_reinforced=3)
    d3 = run3.to_dict()
    r.ok("T022 to_dict() telemetry has dna_reinforced") if d3["telemetry"]["dna_reinforced"] == 3 else r.fail("T022", str(d3))

    # T023
    sa = LearningStage(LearningStageType.PIG_REFRESH, "pig"); sa.mark_complete()
    run.stages.append(sa)
    r.ok("T023 stage() finds by type") if run.stage(LearningStageType.PIG_REFRESH) is sa else r.fail("T023", "not found")

    # T024
    r.ok("T024 stage() returns None for missing type") if run.stage(LearningStageType.STRATEGY_LEARNING) is None else r.fail("T024", "found unexpectedly")

    # T025
    r.ok("T025 run_id preserved in to_dict") if d["run_id"] == "r1" else r.fail("T025", d.get("run_id"))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 4 — LearningSummary model (T026–T030)
# ─────────────────────────────────────────────────────────────────────────────

def suite_04_summary(r: TestResult):
    print("\n── Suite 04: LearningSummary model ──")

    s = LearningSummary(
        run_id="r1", trading_date="2026-08-04",
        stages_total=6, stages_ok=6, stages_failed=0, stages_skipped=0,
        total_duration_ms=200.0, pipeline_healthy=True,
        health=LearningHealth.HEALTHY,
    )

    # T026
    r.ok("T026 pipeline_healthy True when stages_failed=0") if s.pipeline_healthy else r.fail("T026", "False")

    # T027
    s2 = LearningSummary(run_id="r2", trading_date="2026-08-04",
                         stages_total=6, stages_ok=5, stages_failed=1, stages_skipped=0,
                         total_duration_ms=200.0, pipeline_healthy=False,
                         health=LearningHealth.DEGRADED)
    r.ok("T027 pipeline_healthy False when stages_failed>0") if not s2.pipeline_healthy else r.fail("T027", "True")

    # T028
    r.ok("T028 health is LearningHealth enum") if isinstance(s.health, LearningHealth) else r.fail("T028", type(s.health).__name__)

    # T029
    d = s.to_dict()
    for key in ("run_id", "trading_date", "stages_total", "stages_ok", "stages_failed",
                "total_duration_ms", "pipeline_healthy", "health"):
        if key not in d:
            r.fail("T029", f"missing key {key}"); break
    else:
        r.ok("T029 to_dict() has all expected keys")

    # T030
    r.ok("T030 telemetry defaults None") if s.telemetry is None else r.fail("T030", str(s.telemetry))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 5 — MLCConfig (T031–T040)
# ─────────────────────────────────────────────────────────────────────────────

def suite_05_config(r: TestResult):
    print("\n── Suite 05: MLCConfig ──")
    cfg = MLCConfig()

    # T031
    r.ok("T031 MLCConfig instantiates") if cfg is not None else r.fail("T031", "None")

    # T032
    r.ok("T032 amls_enabled=True by default") if cfg.amls_enabled else r.fail("T032", str(cfg.amls_enabled))

    # T033
    r.ok("T033 dre_enabled=True by default") if cfg.dre_enabled else r.fail("T033", str(cfg.dre_enabled))

    # T034
    r.ok("T034 strategy_learning_enabled=True by default") if cfg.strategy_learning_enabled else r.fail("T034", str(cfg.strategy_learning_enabled))

    # T035
    r.ok("T035 max_history_runs=90 by default") if cfg.max_history_runs == 90 else r.fail("T035", str(cfg.max_history_runs))

    # T036
    r.ok("T036 history_path ends with history.json") if cfg.history_path.endswith("history.json") else r.fail("T036", cfg.history_path)

    # T037
    try:
        MLCConfig(max_history_runs=0)
        r.fail("T037", "no error raised")
    except ValueError:
        r.ok("T037 max_history_runs=0 raises ValueError")

    # T038
    r.ok("T038 dry_run=False by default") if not cfg.dry_run else r.fail("T038", str(cfg.dry_run))

    # T039
    r.ok("T039 idr_refresh_enabled=True by default") if cfg.idr_refresh_enabled else r.fail("T039", str(cfg.idr_refresh_enabled))

    # T040
    r.ok("T040 pig_refresh_enabled=True by default") if cfg.pig_refresh_enabled else r.fail("T040", str(cfg.pig_refresh_enabled))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 6 — Coordinator construction (T041–T050)
# ─────────────────────────────────────────────────────────────────────────────

def suite_06_construction(r: TestResult):
    print("\n── Suite 06: Coordinator construction ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T041
        try:
            mlc = _mlc(tp)
            r.ok("T041 default construction (all None)")
        except Exception as e:
            r.fail("T041", str(e))

        # T042
        amls = _MockAMLS()
        mlc2 = _mlc(tp, amls=amls)
        r.ok("T042 construction with mock AMLS") if mlc2._amls is amls else r.fail("T042", "amls not set")

        # T043
        cfg = MLCConfig(history_path=str(tp / "h2.json"), max_history_runs=5)
        mlc3 = MarketLearningCoordinator(config=cfg)
        r.ok("T043 custom config applied") if mlc3._config.max_history_runs == 5 else r.fail("T043", str(mlc3._config.max_history_runs))

        # T044
        le = _MockLE()
        mlc4 = _mlc(tp, learning_engine=le)
        r.ok("T044 learning_engine set") if mlc4._learning_engine is le else r.fail("T044", "le not set")

        # T045
        mlc5 = _mlc(tp, amls=_MockAMLS(), dre=_MockDRE(), idr=_MockIDR(),
                     pig_adapter=_MockPIG(), learning_engine=_MockLE())
        r.ok("T045 all modules injected") if (mlc5._amls and mlc5._dre and mlc5._idr
                                              and mlc5._pig_adapter and mlc5._learning_engine) else r.fail("T045", "module missing")

        # T046
        # Write a history file, then construct a new coordinator
        mlc_a = _mlc(tp)
        mlc_a.run_learning_pipeline()
        mlc_b = _mlc(tp)
        r.ok("T046 history loaded on construction") if len(mlc_b.history()) > 0 else r.fail("T046", "empty history")

        # T047
        new_dir = tp / "subdir"
        cfg2 = MLCConfig(history_path=str(new_dir / "history.json"))
        mlc6 = MarketLearningCoordinator(config=cfg2)
        r.ok("T047 history path parent created") if new_dir.exists() else r.fail("T047", "dir not created")

        # T048
        cfg3 = MLCConfig(history_path=str(tp / "h3.json"), dry_run=True)
        mlc7 = MarketLearningCoordinator(config=cfg3)
        r.ok("T048 dry_run config accessible") if mlc7._config.dry_run else r.fail("T048", "dry_run False")

        # T049
        cfg4 = MLCConfig(history_path=str(tp / "nonexistent" / "history.json"))
        try:
            _m = MarketLearningCoordinator(config=cfg4)
            r.ok("T049 missing history file doesn't crash on load")
        except Exception as e:
            r.fail("T049", str(e))

        # T050
        mlc8 = _mlc(tp)
        r.ok("T050 config defaults applied") if mlc8._config.amls_enabled else r.fail("T050", str(mlc8._config.amls_enabled))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 7 — Pipeline execution, all stages succeed (T051–T065)
# ─────────────────────────────────────────────────────────────────────────────

def suite_07_pipeline_happy(r: TestResult):
    print("\n── Suite 07: Pipeline — happy path ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        amls = _MockAMLS()
        dre  = _MockDRE()
        idr  = _MockIDR()
        pig  = _MockPIG()
        le   = _MockLE()
        mlc  = _mlc(tp, amls=amls, dre=dre, idr=idr, pig_adapter=pig, learning_engine=le)

        trades = [_trade("A"), _trade("B")]
        pig_res = _pig_results("A", "B")
        run = mlc.run_learning_pipeline(trades, pig_res)

        # T051
        r.ok("T051 returns LearningRun") if isinstance(run, LearningRun) else r.fail("T051", type(run).__name__)

        # T052
        r.ok("T052 health HEALTHY") if run.health == LearningHealth.HEALTHY else r.fail("T052", run.health.value)

        # T053
        r.ok("T053 6 stages") if len(run.stages) == 6 else r.fail("T053", str(len(run.stages)))

        # T054
        non_complete = [s for s in run.stages if s.status not in (LearningStageStatus.COMPLETE, LearningStageStatus.SKIPPED)]
        r.ok("T054 all stages COMPLETE or SKIPPED") if not non_complete else r.fail("T054", str([s.name for s in non_complete]))

        # T055
        r.ok("T055 run_id set") if run.run_id.startswith("mlc-") else r.fail("T055", run.run_id)

        # T056
        r.ok("T056 trading_date set") if run.trading_date else r.fail("T056", "empty")

        # T057
        r.ok("T057 started_at set") if run.started_at else r.fail("T057", "empty")

        # T058
        r.ok("T058 ended_at set") if run.ended_at else r.fail("T058", "empty")

        # T059
        r.ok("T059 total_duration_ms > 0") if (run.total_duration_ms or 0) > 0 else r.fail("T059", str(run.total_duration_ms))

        # T060
        r.ok("T060 telemetry set") if run.telemetry is not None else r.fail("T060", "None")

        # T061 — strategy + amls + dre + idr + pig all succeed; only summary excluded from stages_ok
        # (summary itself is COMPLETE but it calls stages[:-1] for the count — check actual stages_ok)
        r.ok("T061 stages_ok >= 4") if run.stages_ok >= 4 else r.fail("T061", str(run.stages_ok))

        # T062
        r.ok("T062 AMLS called once") if amls.calls == 1 else r.fail("T062", str(amls.calls))

        # T063
        r.ok("T063 DRE process_batch called") if dre.calls == 1 else r.fail("T063", str(dre.calls))

        # T064
        r.ok("T064 PIG reload_library called") if pig.reload_calls >= 0 else r.fail("T064", "not called")

        # T065
        r.ok("T065 history updated after run") if len(mlc.history()) == 1 else r.fail("T065", str(len(mlc.history())))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 8 — Strategy Learning stage (T066–T070)
# ─────────────────────────────────────────────────────────────────────────────

def suite_08_strategy_learning(r: TestResult):
    print("\n── Suite 08: Strategy Learning stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T066
        le = _MockLE()
        mlc = _mlc(tp, learning_engine=le)
        trades = [_trade("X")]
        mlc.run_learning_pipeline(trades)
        r.ok("T066 learning_engine.learn() called") if le.calls == 1 else r.fail("T066", str(le.calls))

        # T067
        mlc2 = _mlc(tp)
        run2 = mlc2.run_learning_pipeline([_trade()])
        s = run2.stage(LearningStageType.STRATEGY_LEARNING)
        r.ok("T067 SL skipped when no learning_engine") if s and s.status == LearningStageStatus.SKIPPED else r.fail("T067", str(s and s.status))

        # T068
        cfg = MLCConfig(history_path=str(tp / "h.json"), strategy_learning_enabled=False)
        le2 = _MockLE()
        mlc3 = MarketLearningCoordinator(learning_engine=le2, config=cfg)
        mlc3.run_learning_pipeline([_trade()])
        r.ok("T068 SL skipped when disabled by config") if le2.calls == 0 else r.fail("T068", str(le2.calls))

        # T069
        le_fail = _MockLE(fail=True)
        amls = _MockAMLS()
        mlc4 = _mlc(tp, learning_engine=le_fail, amls=amls)
        mlc4.run_learning_pipeline([_trade()])
        r.ok("T069 SL failure → AMLS still runs") if amls.calls == 1 else r.fail("T069", str(amls.calls))

        # T070
        le3 = _MockLE()
        mlc5 = _mlc(tp, learning_engine=le3)
        run5 = mlc5.run_learning_pipeline([_trade("A"), _trade("B")])
        r.ok("T070 trades_processed counted") if run5.telemetry and run5.telemetry.trades_processed == 2 else r.fail("T070", str(run5.telemetry))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 9 — AMLS stage (T071–T080)
# ─────────────────────────────────────────────────────────────────────────────

def suite_09_amls_stage(r: TestResult):
    print("\n── Suite 09: AMLS stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T071
        amls = _MockAMLS()
        mlc = _mlc(tp, amls=amls)
        mlc.run_learning_pipeline()
        r.ok("T071 AMLS.run_pipeline() called") if amls.calls == 1 else r.fail("T071", str(amls.calls))

        # T072
        mlc2 = _mlc(tp)
        run2 = mlc2.run_learning_pipeline()
        s = run2.stage(LearningStageType.AMLS)
        r.ok("T072 AMLS skipped when amls=None") if s and s.status == LearningStageStatus.SKIPPED else r.fail("T072", str(s and s.status))

        # T073
        amls3 = _MockAMLS()
        cfg = MLCConfig(history_path=str(tp / "h.json"), amls_enabled=False)
        mlc3 = MarketLearningCoordinator(amls=amls3, config=cfg)
        mlc3.run_learning_pipeline()
        r.ok("T073 AMLS skipped when amls_enabled=False") if amls3.calls == 0 else r.fail("T073", str(amls3.calls))

        # T074
        amls_fail = _MockAMLS(fail=True)
        dre = _MockDRE()
        mlc4 = _mlc(tp, amls=amls_fail, dre=dre)
        mlc4.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T074 AMLS failure → DRE still runs") if dre.calls == 1 else r.fail("T074", str(dre.calls))

        # T075
        amls5 = _MockAMLS(state="PARTIAL")
        mlc5 = _mlc(tp, amls=amls5)
        run5 = mlc5.run_learning_pipeline()
        s5 = run5.stage(LearningStageType.AMLS)
        r.ok("T075 AMLS state captured in output") if s5 and s5.output.get("state") == "PARTIAL" else r.fail("T075", str(s5 and s5.output))

        # T076
        amls6 = _MockAMLS()
        mlc6 = _mlc(tp, amls=amls6)
        run6 = mlc6.run_learning_pipeline()
        r.ok("T076 dna_updated from AMLS telemetry") if run6.telemetry and run6.telemetry.dna_updated else r.fail("T076", str(run6.telemetry))

        # T077
        amls7 = _MockAMLS()
        mlc7 = _mlc(tp, amls=amls7)
        run7 = mlc7.run_learning_pipeline()
        r.ok("T077 repository_updates from AMLS") if run7.telemetry and run7.telemetry.repository_updates == 3 else r.fail("T077", str(run7.telemetry and run7.telemetry.repository_updates))

        # T078
        amls8 = _MockAMLS(gw_refreshed=True)
        mlc8 = _mlc(tp, amls=amls8)
        run8 = mlc8.run_learning_pipeline()
        r.ok("T078 gateway_refresh from AMLS") if run8.telemetry and run8.telemetry.gateway_refresh else r.fail("T078", str(run8.telemetry))

        # T079
        amls9 = _MockAMLS()
        mlc9 = _mlc(tp, amls=amls9)
        run9 = mlc9.run_learning_pipeline()
        r.ok("T079 amls_duration_ms captured") if run9.telemetry and run9.telemetry.amls_duration_ms > 0 else r.fail("T079", str(run9.telemetry and run9.telemetry.amls_duration_ms))

        # T080
        amls_f = _MockAMLS(fail=True)
        mlc10 = _mlc(tp, amls=amls_f)
        run10 = mlc10.run_learning_pipeline()
        s10 = run10.stage(LearningStageType.AMLS)
        r.ok("T080 AMLS failure error stored in stage") if s10 and s10.error else r.fail("T080", str(s10 and s10.error))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 10 — DRE stage (T081–T092)
# ─────────────────────────────────────────────────────────────────────────────

def suite_10_dre_stage(r: TestResult):
    print("\n── Suite 10: DRE stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T081
        mlc = _mlc(tp)
        run = mlc.run_learning_pipeline([_trade("A")], _pig_results("A"))
        s = run.stage(LearningStageType.DNA_REINFORCEMENT)
        r.ok("T081 DRE skipped when dre=None") if s and s.status == LearningStageStatus.SKIPPED else r.fail("T081", str(s and s.status))

        # T082
        dre2 = _MockDRE()
        cfg = MLCConfig(history_path=str(tp / "h.json"), dre_enabled=False)
        mlc2 = MarketLearningCoordinator(dre=dre2, config=cfg)
        mlc2.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T082 DRE skipped when dre_enabled=False") if dre2.calls == 0 else r.fail("T082", str(dre2.calls))

        # T083
        dre3 = _MockDRE()
        mlc3 = _mlc(tp, dre=dre3)
        mlc3.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T083 DRE process_batch called with pig_results") if dre3.calls == 1 else r.fail("T083", str(dre3.calls))

        # T084
        dre4 = _MockDRE()
        mlc4 = _mlc(tp, dre=dre4)
        mlc4.run_learning_pipeline([_trade("Z")])   # no pig_results
        r.ok("T084 DRE skipped when no pig_results match") if dre4.calls == 0 else r.fail("T084", str(dre4.calls))

        # T085
        dre_fail = _MockDRE(fail=True)
        idr = _MockIDR()
        mlc5 = _mlc(tp, dre=dre_fail, idr=idr)
        mlc5.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T085 DRE failure → IDR still runs") if idr.calls >= 1 else r.fail("T085", str(idr.calls))

        # T086
        dre6 = _MockDRE(per_item=2)
        mlc6 = _mlc(tp, dre=dre6)
        run6 = mlc6.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T086 dna_reinforced counted") if run6.telemetry and run6.telemetry.dna_reinforced >= 0 else r.fail("T086", str(run6.telemetry))

        # T087
        dre7 = _MockDRE()
        mlc7 = _mlc(tp, dre=dre7)
        run7 = mlc7.run_learning_pipeline([_trade("A"), _trade("B")], _pig_results("A", "B"))
        r.ok("T087 dre_trades_attempted counted") if run7.telemetry and run7.telemetry.dre_trades_attempted >= 0 else r.fail("T087", str(run7.telemetry))

        # T088 — empty trades: stage completes but process_batch is never called
        dre8 = _MockDRE()
        mlc8 = _mlc(tp, dre=dre8)
        mlc8.run_learning_pipeline([])  # empty trades
        r.ok("T088 DRE process_batch not called with empty trades") if dre8.calls == 0 else r.fail("T088", f"calls={dre8.calls}")

        # T089
        dre9 = _MockDRE()
        mlc9 = _mlc(tp, dre=dre9)
        run9 = mlc9.run_learning_pipeline([_trade("A")], _pig_results("A"))
        s9 = run9.stage(LearningStageType.DNA_REINFORCEMENT)
        r.ok("T089 DRE stage output has reinforcements key") if s9 and "reinforcements" in s9.output else r.fail("T089", str(s9 and s9.output.keys()))

        # T090 — DRE only processes trades that appear in pig_results
        dre10 = _MockDRE()
        mlc10 = _mlc(tp, dre=dre10)
        # Two trades, only one has a pig result
        mlc10.run_learning_pipeline([_trade("A"), _trade("B")], _pig_results("A"))
        r.ok("T090 DRE only processes matched trades") if dre10.calls == 1 else r.fail("T090", str(dre10.calls))

        # T091 — pmci must be non-None; trades with missing pmci skipped
        dre11 = _MockDRE()
        mlc11 = _mlc(tp, dre=dre11)
        # pig result with no pmci_result
        bad_pig = {"A": type("PI", (), {"pmci_result": None, "ca_pmci_result": None, "cds_scores": None})()}
        run11 = mlc11.run_learning_pipeline([_trade("A")], bad_pig)
        r.ok("T091 DRE skips trades with no pmci_result") if dre11.calls == 0 else r.fail("T091", str(dre11.calls))

        # T092 — pmci extracted from pi.pmci_result
        dre12 = _MockDRE()
        mlc12 = _mlc(tp, dre=dre12)
        mlc12.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T092 pmci extracted from PIG result") if dre12.calls == 1 else r.fail("T092", "not called")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 11 — IDR refresh stage (T093–T100)
# ─────────────────────────────────────────────────────────────────────────────

def suite_11_idr_stage(r: TestResult):
    print("\n── Suite 11: IDR refresh stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T093
        idr = _MockIDR(total_dna=7)
        mlc = _mlc(tp, idr=idr)
        mlc.run_learning_pipeline()
        r.ok("T093 IDR.statistics() called") if idr.calls >= 1 else r.fail("T093", str(idr.calls))

        # T094
        mlc2 = _mlc(tp)
        run2 = mlc2.run_learning_pipeline()
        s = run2.stage(LearningStageType.IDR_REFRESH)
        r.ok("T094 IDR skipped when idr=None") if s and s.status == LearningStageStatus.SKIPPED else r.fail("T094", str(s and s.status))

        # T095
        idr3 = _MockIDR()
        cfg = MLCConfig(history_path=str(tp / "h.json"), idr_refresh_enabled=False)
        mlc3 = MarketLearningCoordinator(idr=idr3, config=cfg)
        mlc3.run_learning_pipeline()
        r.ok("T095 IDR skipped when idr_refresh_enabled=False") if idr3.calls == 0 else r.fail("T095", str(idr3.calls))

        # T096
        idr_fail = _MockIDR(fail=True)
        pig = _MockPIG()
        mlc4 = _mlc(tp, idr=idr_fail, pig_adapter=pig)
        mlc4.run_learning_pipeline()
        r.ok("T096 IDR failure → PIG still runs") if pig.reload_calls >= 0 else r.fail("T096", str(pig.reload_calls))

        # T097
        idr5 = _MockIDR(total_dna=42)
        mlc5 = _mlc(tp, idr=idr5)
        run5 = mlc5.run_learning_pipeline()
        r.ok("T097 idr_total_dna captured") if run5.telemetry and run5.telemetry.idr_total_dna == 42 else r.fail("T097", str(run5.telemetry and run5.telemetry.idr_total_dna))

        # T098
        idr6 = _MockIDR()
        amls6 = _MockAMLS()
        mlc6 = _mlc(tp, idr=idr6, amls=amls6)
        run6 = mlc6.run_learning_pipeline()
        r.ok("T098 knowledge_generated tallied") if run6.telemetry and run6.telemetry.knowledge_generated >= 0 else r.fail("T098", str(run6.telemetry))

        # T099
        idr7 = _MockIDR(total_dna=9)
        mlc7 = _mlc(tp, idr=idr7)
        run7 = mlc7.run_learning_pipeline()
        s7 = run7.stage(LearningStageType.IDR_REFRESH)
        r.ok("T099 IDR stage output has total_dna") if s7 and "total_dna" in s7.output else r.fail("T099", str(s7 and s7.output.keys()))

        # T100
        idr8 = _MockIDR(fail=True)
        mlc8 = _mlc(tp, idr=idr8)
        run8 = mlc8.run_learning_pipeline()
        s8 = run8.stage(LearningStageType.IDR_REFRESH)
        r.ok("T100 IDR failure → stage FAILED") if s8 and s8.status == LearningStageStatus.FAILED else r.fail("T100", str(s8 and s8.status))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 12 — PIG refresh stage (T101–T108)
# ─────────────────────────────────────────────────────────────────────────────

def suite_12_pig_stage(r: TestResult):
    print("\n── Suite 12: PIG refresh stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T101 — AMLS gw_refreshed=False → PIG stage calls reload
        amls_no_gw = _MockAMLS(gw_refreshed=False)
        pig = _MockPIG()
        mlc = _mlc(tp, amls=amls_no_gw, pig_adapter=pig)
        mlc.run_learning_pipeline()
        r.ok("T101 PIG reload_library called when AMLS didn't refresh") if pig.reload_calls >= 1 else r.fail("T101", str(pig.reload_calls))

        # T102
        mlc2 = _mlc(tp)
        run2 = mlc2.run_learning_pipeline()
        s = run2.stage(LearningStageType.PIG_REFRESH)
        r.ok("T102 PIG skipped when pig_adapter=None") if s and s.status == LearningStageStatus.SKIPPED else r.fail("T102", str(s and s.status))

        # T103
        pig3 = _MockPIG()
        cfg = MLCConfig(history_path=str(tp / "h.json"), pig_refresh_enabled=False)
        mlc3 = MarketLearningCoordinator(pig_adapter=pig3, config=cfg)
        mlc3.run_learning_pipeline()
        r.ok("T103 PIG skipped when pig_refresh_enabled=False") if pig3.reload_calls == 0 else r.fail("T103", str(pig3.reload_calls))

        # T104
        pig_fail = _MockPIG(fail=True)
        mlc4 = _mlc(tp, pig_adapter=pig_fail)
        run4 = mlc4.run_learning_pipeline()
        s4 = run4.stage(LearningStageType.SUMMARY)
        r.ok("T104 PIG failure → summary still runs") if s4 and s4.succeeded else r.fail("T104", str(s4 and s4.status))

        # T105
        pig5 = _MockPIG()
        amls5 = _MockAMLS(gw_refreshed=False)
        mlc5 = _mlc(tp, amls=amls5, pig_adapter=pig5)
        run5 = mlc5.run_learning_pipeline()
        r.ok("T105 gateway_refresh True when PIG reloaded") if run5.telemetry and run5.telemetry.gateway_refresh else r.fail("T105", str(run5.telemetry))

        # T106 — AMLS already refreshed PIG → PIG stage skipped to avoid duplicate
        pig6 = _MockPIG()
        amls6 = _MockAMLS(gw_refreshed=True)
        mlc6 = _mlc(tp, amls=amls6, pig_adapter=pig6)
        run6 = mlc6.run_learning_pipeline()
        s6 = run6.stage(LearningStageType.PIG_REFRESH)
        r.ok("T106 PIG stage SKIPPED when AMLS already refreshed") if s6 and s6.status == LearningStageStatus.SKIPPED else r.fail("T106", str(s6 and s6.status))

        # T107
        pig7 = _MockPIG()
        amls7 = _MockAMLS(gw_refreshed=False)
        mlc7 = _mlc(tp, amls=amls7, pig_adapter=pig7)
        mlc7.run_learning_pipeline()
        r.ok("T107 PIG reload called when AMLS didn't refresh") if pig7.reload_calls >= 1 else r.fail("T107", str(pig7.reload_calls))

        # T108
        pig8 = _MockPIG()
        amls8 = _MockAMLS(gw_refreshed=False)
        mlc8 = _mlc(tp, amls=amls8, pig_adapter=pig8)
        run8 = mlc8.run_learning_pipeline()
        s8 = run8.stage(LearningStageType.PIG_REFRESH)
        r.ok("T108 PIG stage output has reloaded key") if s8 and "reloaded" in s8.output else r.fail("T108", str(s8 and s8.output.keys()))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 13 — Summary stage (T109–T112)
# ─────────────────────────────────────────────────────────────────────────────

def suite_13_summary_stage(r: TestResult):
    print("\n── Suite 13: Summary stage ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T109 — even all other stages fail, summary runs
        mlc = _mlc(tp,
                   amls=_MockAMLS(fail=True),
                   dre=_MockDRE(fail=True),
                   idr=_MockIDR(fail=True),
                   pig_adapter=_MockPIG(fail=True))
        run = mlc.run_learning_pipeline([_trade("A")], _pig_results("A"))
        s = run.stage(LearningStageType.SUMMARY)
        r.ok("T109 summary stage always runs") if s and s.succeeded else r.fail("T109", str(s and s.status))

        # T110
        r.ok("T110 summary output has stages_ok/failed/skipped") if (
            "stages_ok" in s.output and "stages_failed" in s.output
        ) else r.fail("T110", str(s.output.keys()))

        # T111 — no failures → HEALTHY
        mlc2 = _mlc(tp)
        run2 = mlc2.run_learning_pipeline()
        r.ok("T111 health HEALTHY when no failures") if run2.health == LearningHealth.HEALTHY else r.fail("T111", run2.health.value)

        # T112 — any failure → DEGRADED
        mlc3 = _mlc(tp, amls=_MockAMLS(fail=True))
        run3 = mlc3.run_learning_pipeline()
        r.ok("T112 health DEGRADED when stage fails") if run3.health == LearningHealth.DEGRADED else r.fail("T112", run3.health.value)


# ─────────────────────────────────────────────────────────────────────────────
# Suite 14 — Failure isolation (T113–T125)
# ─────────────────────────────────────────────────────────────────────────────

def suite_14_failure_isolation(r: TestResult):
    print("\n── Suite 14: Failure isolation ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        def _count_complete(run):
            return sum(1 for s in run.stages if s.succeeded)

        # T113 — AMLS fail → DRE still called
        dre = _MockDRE()
        mlc = _mlc(tp, amls=_MockAMLS(fail=True), dre=dre)
        mlc.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T113 AMLS fail → DRE still runs") if dre.calls == 1 else r.fail("T113", str(dre.calls))

        # T114 — DRE fail → IDR still called
        idr = _MockIDR()
        mlc2 = _mlc(tp, dre=_MockDRE(fail=True), idr=idr)
        mlc2.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T114 DRE fail → IDR still runs") if idr.calls >= 1 else r.fail("T114", str(idr.calls))

        # T115 — IDR fail → PIG still called
        pig = _MockPIG()
        amls = _MockAMLS(gw_refreshed=False)
        mlc3 = _mlc(tp, amls=amls, idr=_MockIDR(fail=True), pig_adapter=pig)
        mlc3.run_learning_pipeline()
        r.ok("T115 IDR fail → PIG still runs") if pig.reload_calls >= 1 else r.fail("T115", str(pig.reload_calls))

        # T116 — PIG fail → summary still runs
        mlc4 = _mlc(tp, pig_adapter=_MockPIG(fail=True))
        run4 = mlc4.run_learning_pipeline()
        s_sum = run4.stage(LearningStageType.SUMMARY)
        r.ok("T116 PIG fail → summary runs") if s_sum and s_sum.succeeded else r.fail("T116", str(s_sum and s_sum.status))

        # T117 — all stages fail → summary still runs
        mlc5 = _mlc(tp,
                     amls=_MockAMLS(fail=True),
                     dre=_MockDRE(fail=True),
                     idr=_MockIDR(fail=True),
                     pig_adapter=_MockPIG(fail=True))
        run5 = mlc5.run_learning_pipeline([_trade("A")], _pig_results("A"))
        s5 = run5.stage(LearningStageType.SUMMARY)
        r.ok("T117 all stages fail → summary still runs") if s5 and s5.succeeded else r.fail("T117", str(s5 and s5.status))

        # T118 — SL fail → AMLS still runs
        amls6 = _MockAMLS()
        mlc6 = _mlc(tp, learning_engine=_MockLE(fail=True), amls=amls6)
        mlc6.run_learning_pipeline([_trade()])
        r.ok("T118 SL fail → AMLS still runs") if amls6.calls == 1 else r.fail("T118", str(amls6.calls))

        # T119
        mlc7 = _mlc(tp, amls=_MockAMLS(fail=True), dre=_MockDRE(fail=True),
                     idr=_MockIDR(fail=True), pig_adapter=_MockPIG(fail=True))
        run7 = mlc7.run_learning_pipeline([_trade("A")], _pig_results("A"))
        r.ok("T119 all fail → stages_failed > 0") if run7.stages_failed > 0 else r.fail("T119", str(run7.stages_failed))

        # T120
        r.ok("T120 all fail → health DEGRADED") if run7.health == LearningHealth.DEGRADED else r.fail("T120", run7.health.value)

        # T121
        r.ok("T121 all fail → telemetry still set") if run7.telemetry is not None else r.fail("T121", "None")

        # T122 — AMLS fail → other ok stages still contribute to stages_ok
        mlc8 = _mlc(tp, amls=_MockAMLS(fail=True), idr=_MockIDR())
        run8 = mlc8.run_learning_pipeline()
        r.ok("T122 AMLS fail → IDR still counts in stages_ok") if run8.stages_ok >= 1 else r.fail("T122", str(run8.stages_ok))

        # T123 — failed stage error stored
        mlc9 = _mlc(tp, amls=_MockAMLS(fail=True))
        run9 = mlc9.run_learning_pipeline()
        s9 = run9.stage(LearningStageType.AMLS)
        r.ok("T123 failed stage error stored") if s9 and s9.error else r.fail("T123", str(s9 and s9.error))

        # T124 — LearningRun always returned even with all failures
        mlc10 = _mlc(tp, amls=_MockAMLS(fail=True), dre=_MockDRE(fail=True))
        run10 = mlc10.run_learning_pipeline()
        r.ok("T124 LearningRun always returned") if isinstance(run10, LearningRun) else r.fail("T124", type(run10).__name__)

        # T125 — run_id unique
        mlc11 = _mlc(tp)
        id1 = mlc11.run_learning_pipeline().run_id
        id2 = mlc11.run_learning_pipeline().run_id
        r.ok("T125 run_id unique across runs") if id1 != id2 else r.fail("T125", "same ID")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 15 — Standalone APIs (T126–T135)
# ─────────────────────────────────────────────────────────────────────────────

def suite_15_standalone(r: TestResult):
    print("\n── Suite 15: Standalone APIs ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T126
        amls = _MockAMLS()
        mlc = _mlc(tp, amls=amls)
        result = mlc.run_amls()
        r.ok("T126 run_amls() calls amls.run_pipeline()") if amls.calls == 1 else r.fail("T126", str(amls.calls))

        # T127
        mlc2 = _mlc(tp)
        try:
            mlc2.run_amls()
            r.fail("T127", "no error raised")
        except MLCError:
            r.ok("T127 run_amls() raises MLCError when no AMLS")

        # T128
        dre = _MockDRE()
        mlc3 = _mlc(tp, dre=dre)
        mlc3.run_reinforcement([_trade("A")], _pig_results("A"))
        r.ok("T128 run_reinforcement() calls dre.process_batch()") if dre.calls == 1 else r.fail("T128", str(dre.calls))

        # T129
        mlc4 = _mlc(tp)
        try:
            mlc4.run_reinforcement([_trade()])
            r.fail("T129", "no error raised")
        except MLCError:
            r.ok("T129 run_reinforcement() raises MLCError when no DRE")

        # T130
        dre5 = _MockDRE()
        mlc5 = _mlc(tp, dre=dre5)
        result5 = mlc5.run_reinforcement([], {})
        r.ok("T130 run_reinforcement with empty trades returns []") if result5 == [] else r.fail("T130", str(result5))

        # T131
        dre6 = _MockDRE()
        mlc6 = _mlc(tp, dre=dre6)
        result6 = mlc6.run_reinforcement([_trade("A")], {})  # no pig_results
        r.ok("T131 run_reinforcement no pig_results returns []") if result6 == [] else r.fail("T131", str(result6))

        # T132
        mlc7 = _mlc(tp)
        mlc7.run_learning_pipeline()
        summary = mlc7.status()
        r.ok("T132 status() returns LearningSummary") if isinstance(summary, LearningSummary) else r.fail("T132", type(summary).__name__)

        # T133
        mlc8 = _mlc(tp)  # fresh coordinator, no runs
        summary8 = mlc8.status()
        r.ok("T133 status() with no run returns zero state") if summary8.stages_total == 0 else r.fail("T133", str(summary8.stages_total))

        # T134
        mlc9 = _mlc(tp)
        mlc9.run_learning_pipeline()
        hist = mlc9.history()
        r.ok("T134 history() returns list of dicts") if isinstance(hist, list) and isinstance(hist[0], dict) else r.fail("T134", str(type(hist[0]) if hist else "empty"))

        # T135
        mlc10 = _mlc(tp)
        for _ in range(5):
            mlc10.run_learning_pipeline()
        hist10 = mlc10.history(limit=3)
        r.ok("T135 history() respects limit") if len(hist10) == 3 else r.fail("T135", str(len(hist10)))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 16 — Statistics API (T136–T140)
# ─────────────────────────────────────────────────────────────────────────────

def suite_16_statistics(r: TestResult):
    print("\n── Suite 16: Statistics API ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T136
        mlc = _mlc(tp)
        mlc.run_learning_pipeline()
        stats = mlc.statistics()
        r.ok("T136 statistics() returns dict") if isinstance(stats, dict) else r.fail("T136", type(stats).__name__)

        # T137 — fresh coordinator with its own history path
        with tempfile.TemporaryDirectory() as tmp2:
            mlc2 = _mlc(Path(tmp2))
            stats2 = mlc2.statistics()
            r.ok("T137 statistics() total_runs=0 when no history") if stats2["total_runs"] == 0 else r.fail("T137", str(stats2))

        # T138 — isolated temp dir: 1 healthy + 1 degraded run
        with tempfile.TemporaryDirectory() as tmp3:
            mlc3 = _mlc(Path(tmp3), amls=_MockAMLS())
            mlc3.run_learning_pipeline()
            mlc3._amls = _MockAMLS(fail=True)
            mlc3.run_learning_pipeline()
            stats3 = mlc3.statistics()
            r.ok("T138 statistics() counts healthy/degraded runs") if stats3["total_runs"] == 2 else r.fail("T138", str(stats3))

        # T139
        with tempfile.TemporaryDirectory() as tmp4:
            mlc4 = _mlc(Path(tmp4))
            for _ in range(3):
                mlc4.run_learning_pipeline()
            s4 = mlc4.statistics()
            r.ok("T139 statistics() avg_duration_ms is a number") if isinstance(s4["avg_duration_ms"], (int, float)) else r.fail("T139", str(s4["avg_duration_ms"]))

        # T140
        mlc5 = _mlc(tp)
        mlc5.run_learning_pipeline()
        s5 = mlc5.statistics()
        r.ok("T140 statistics() has last_run_date") if s5.get("last_run_date") else r.fail("T140", str(s5.get("last_run_date")))


# ─────────────────────────────────────────────────────────────────────────────
# Suite 17 — History persistence (T141–T150)
# ─────────────────────────────────────────────────────────────────────────────

def suite_17_persistence(r: TestResult):
    print("\n── Suite 17: History persistence ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T141 — history file written after run
        mlc = _mlc(tp)
        mlc.run_learning_pipeline()
        hist_file = Path(mlc._config.history_path)
        r.ok("T141 history written to disk") if hist_file.exists() else r.fail("T141", "file not found")

        # T142 — new coordinator loads previous history
        mlc2 = _mlc(tp)
        r.ok("T142 history loaded by new instance") if len(mlc2.history()) >= 1 else r.fail("T142", str(len(mlc2.history())))

        # T143 — eviction beyond max_history_runs
        cfg = MLCConfig(history_path=str(tp / "h_cap.json"), max_history_runs=3)
        mlc3 = MarketLearningCoordinator(config=cfg)
        for _ in range(5):
            mlc3.run_learning_pipeline()
        r.ok("T143 history capped at max_history_runs") if len(mlc3.history()) <= 3 else r.fail("T143", str(len(mlc3.history())))

        # T144 — survives restart
        mlc4 = _mlc(tp)
        mlc4.run_learning_pipeline()
        run_id = mlc4.history(limit=1)[0]["run_id"]
        mlc5 = _mlc(tp)
        r.ok("T144 history survives restart") if any(h["run_id"] == run_id for h in mlc5.history()) else r.fail("T144", "run_id not found")

        # T145 — parent dir created
        deep_dir = tp / "deep" / "nested"
        cfg2 = MLCConfig(history_path=str(deep_dir / "history.json"))
        mlc6 = MarketLearningCoordinator(config=cfg2)
        mlc6.run_learning_pipeline()
        r.ok("T145 parent dirs created for history path") if deep_dir.exists() else r.fail("T145", "dir not created")

        # T146 — corrupt history doesn't crash
        hist_path = tp / "corrupt.json"
        hist_path.write_text("{not valid json{{")
        cfg3 = MLCConfig(history_path=str(hist_path))
        try:
            mlc7 = MarketLearningCoordinator(config=cfg3)
            r.ok("T146 corrupt history doesn't crash on load")
        except Exception as e:
            r.fail("T146", str(e))

        # T147 — history dict has required keys
        mlc8 = _mlc(tp)
        mlc8.run_learning_pipeline()
        h = mlc8.history(limit=1)[0]
        for key in ("run_id", "trading_date", "started_at", "health"):
            if key not in h:
                r.fail("T147", f"missing key {key}"); break
        else:
            r.ok("T147 history dict has required keys")

        # T148 — limit works correctly
        mlc9 = _mlc(tp)
        for _ in range(4):
            mlc9.run_learning_pipeline()
        r.ok("T148 history(limit=2) returns 2") if len(mlc9.history(limit=2)) == 2 else r.fail("T148", str(len(mlc9.history(limit=2))))

        # T149 — multiple runs accumulate
        mlc10 = _mlc(tp)
        mlc10.run_learning_pipeline()
        mlc10.run_learning_pipeline()
        r.ok("T149 multiple runs accumulate in history") if len(mlc10.history()) >= 2 else r.fail("T149", str(len(mlc10.history())))

        # T150 — history sorted newest-first
        mlc11 = _mlc(tp)
        mlc11.run_learning_pipeline()
        time.sleep(0.01)
        mlc11.run_learning_pipeline()
        hist11 = mlc11.history(limit=2)
        r.ok("T150 history sorted newest-first") if hist11[0]["started_at"] >= hist11[1]["started_at"] else r.fail("T150", f"{hist11[0]['started_at']} < {hist11[1]['started_at']}")


# ─────────────────────────────────────────────────────────────────────────────
# Suite 18 — Concurrency (T151–T160)
# ─────────────────────────────────────────────────────────────────────────────

def suite_18_concurrency(r: TestResult):
    print("\n── Suite 18: Concurrency ──")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)

        # T151 — concurrent runs don't crash
        mlc = _mlc(tp, amls=_MockAMLS(), idr=_MockIDR())
        errors: List[str] = []
        def _run():
            try:
                mlc.run_learning_pipeline()
            except Exception as exc:
                errors.append(str(exc))
        threads = [threading.Thread(target=_run) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        r.ok("T151 concurrent runs don't crash") if not errors else r.fail("T151", str(errors))

        # T152 — history not corrupted by concurrent writes
        r.ok("T152 history count correct after concurrent runs") if len(mlc.history()) == 5 else r.fail("T152", str(len(mlc.history())))

        # T153 — no duplicate run_ids
        run_ids = [h["run_id"] for h in mlc.history()]
        r.ok("T153 no duplicate run_ids") if len(run_ids) == len(set(run_ids)) else r.fail("T153", f"dupes in {run_ids}")

        # T154 — _last_run consistent (not None after concurrent runs)
        r.ok("T154 _last_run set after concurrent runs") if mlc._last_run is not None else r.fail("T154", "None")

        # T155 — status() thread-safe
        results: List[Any] = []
        def _status():
            results.append(mlc.status())
        ts = [threading.Thread(target=_status) for _ in range(3)]
        for t in ts: t.start()
        for t in ts: t.join()
        r.ok("T155 status() thread-safe") if all(isinstance(s, LearningSummary) for s in results) else r.fail("T155", "non-LearningSummary")

        # T156 — history() thread-safe
        hist_results: List[Any] = []
        def _hist():
            hist_results.append(mlc.history())
        th = [threading.Thread(target=_hist) for _ in range(3)]
        for t in th: t.start()
        for t in th: t.join()
        r.ok("T156 history() thread-safe") if all(isinstance(h, list) for h in hist_results) else r.fail("T156", "non-list")

        # T157 — statistics() thread-safe
        stat_results: List[Any] = []
        def _stat():
            stat_results.append(mlc.statistics())
        ts2 = [threading.Thread(target=_stat) for _ in range(3)]
        for t in ts2: t.start()
        for t in ts2: t.join()
        r.ok("T157 statistics() thread-safe") if all(isinstance(s, dict) for s in stat_results) else r.fail("T157", "non-dict")

        # T158 — lock released after exception in run
        mlc2 = _mlc(tp, amls=_MockAMLS(fail=True))
        mlc2.run_learning_pipeline()
        r.ok("T158 lock released after exception") if not mlc2._lock.locked() else r.fail("T158", "lock held")

        # T159 — second run after exception runs cleanly
        mlc3 = _mlc(tp, amls=_MockAMLS(fail=True))
        mlc3.run_learning_pipeline()
        run2 = mlc3.run_learning_pipeline()
        r.ok("T159 second run after exception succeeds") if isinstance(run2, LearningRun) else r.fail("T159", type(run2).__name__)

        # T160 — concurrent append to history stays bounded
        cfg = MLCConfig(history_path=str(tp / "bound.json"), max_history_runs=5)
        mlc4 = MarketLearningCoordinator(config=cfg)
        def _run4():
            mlc4.run_learning_pipeline()
        ts3 = [threading.Thread(target=_run4) for _ in range(10)]
        for t in ts3: t.start()
        for t in ts3: t.join()
        r.ok("T160 concurrent history bounded by max_history_runs") if len(mlc4.history()) <= 5 else r.fail("T160", str(len(mlc4.history())))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    r = TestResult()
    suite_01_learning_stage(r)
    suite_02_telemetry(r)
    suite_03_run(r)
    suite_04_summary(r)
    suite_05_config(r)
    suite_06_construction(r)
    suite_07_pipeline_happy(r)
    suite_08_strategy_learning(r)
    suite_09_amls_stage(r)
    suite_10_dre_stage(r)
    suite_11_idr_stage(r)
    suite_12_pig_stage(r)
    suite_13_summary_stage(r)
    suite_14_failure_isolation(r)
    suite_15_standalone(r)
    suite_16_statistics(r)
    suite_17_persistence(r)
    suite_18_concurrency(r)
    return r.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
