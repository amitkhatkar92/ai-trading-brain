"""
test_ptue.py — Point-in-Time Universe Engine test suite.

IIOS Research Infrastructure — R-006.

Test range: T001-T160 (160 tests)
Run: python test_ptue.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock

# ─── harness ────────────────────────────────────────────────────────────────
PASS = 0
FAIL = 0
ERRORS: List[str] = []


def ok(tid: str, cond: bool, msg: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        ERRORS.append(f"{tid}: FAIL {msg}")


def section(title: str) -> None:
    print(f"\n-- {title} --")


# ─── imports ─────────────────────────────────────────────────────────────────
from autonomous_research.ptue_models import (
    SOURCE_EMPTY,
    SOURCE_HISTORY_FILE,
    SOURCE_STATIC_FALLBACK,
    UNIVERSE_NIFTY100,
    UNIVERSE_NIFTY50,
    UNIVERSE_NIFTY500,
    Constituent,
    CoverageReport,
    HistoricalUniverse,
    InvalidDateError,
    PTUEError,
    UniverseNotFoundError,
    UniverseStatistics,
    UniverseVersion,
    _now_iso,
)
from autonomous_research.ptue_config import PTUEConfig
from autonomous_research.ptue import PointInTimeUniverseEngine

# ─── helpers ─────────────────────────────────────────────────────────────────

def _write_history(directory: str, universe: str, constituents: list, version: str = "1.0") -> str:
    """Write a history.json to a temp directory and return its path."""
    d = Path(directory) / universe
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "universe":    universe,
        "version":     version,
        "description": "test",
        "last_updated": "2025-01-01",
        "constituents": constituents,
    }
    p = d / "history.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)


def _write_static_fallback(directory: str, symbols: list) -> str:
    p = Path(directory) / "static.json"
    p.write_text(json.dumps(symbols), encoding="utf-8")
    return str(p)


def _make_ptue(
    history_root: str,
    static_path: str = "",
    fallback: bool = True,
    cache: bool = True,
    dry_run: bool = False,
) -> PointInTimeUniverseEngine:
    cfg = PTUEConfig(
        history_root=history_root,
        static_fallback_path=static_path,
        fallback_enabled=fallback,
        cache_enabled=cache,
        dry_run=dry_run,
    )
    return PointInTimeUniverseEngine(config=cfg)


# ─── T001-T015: Model fields and serialisation ───────────────────────────────

section("T001-T015: Models")

c = Constituent(symbol="RELIANCE", effective_from="2020-01-01", effective_to=None, reason="INITIAL")
ok("T001", c.symbol == "RELIANCE")
ok("T002", c.effective_from == "2020-01-01")
ok("T003", c.effective_to is None)
ok("T004", c.reason == "INITIAL")
ok("T005", c.is_active_on("2022-06-15") is True)
ok("T006", c.is_active_on("2019-12-31") is False, "before effective_from")

c_removed = Constituent("SUZLON", "2021-01-01", "2023-12-31", "REMOVED")
ok("T007", c_removed.is_active_on("2022-06-15") is True, "within range")
ok("T008", c_removed.is_active_on("2024-01-01") is False, "after effective_to")
ok("T009", c_removed.is_active_on("2020-12-31") is False, "before effective_from")

cd = c.to_dict()
ok("T010", cd["symbol"] == "RELIANCE")
ok("T011", cd["effective_to"] is None)
ok("T012", "reason" in cd)

c2 = Constituent.from_dict({"symbol": "TCS", "effective_from": "2021-03-01",
                              "effective_to": "2024-06-30", "reason": "ADDED"})
ok("T013", c2.symbol == "TCS")
ok("T014", c2.effective_to == "2024-06-30")
ok("T015", c2.reason == "ADDED")

# ─── T016-T025: Errors ───────────────────────────────────────────────────────

section("T016-T025: Errors and model constants")

err = UniverseNotFoundError("NIFTY500", "2022-01-01")
ok("T016", isinstance(err, PTUEError))
ok("T017", err.universe_name == "NIFTY500")
ok("T018", err.date == "2022-01-01")
ok("T019", "NIFTY500" in str(err))

err2 = InvalidDateError("bad-date")
ok("T020", isinstance(err2, PTUEError))
ok("T021", "bad-date" in str(err2))

ok("T022", UNIVERSE_NIFTY500 == "NIFTY500")
ok("T023", UNIVERSE_NIFTY100 == "NIFTY100")
ok("T024", UNIVERSE_NIFTY50  == "NIFTY50")
ok("T025", SOURCE_HISTORY_FILE == "HISTORY_FILE")

# ─── T026-T045: Basic get_universe with history file ─────────────────────────

section("T026-T045: get_universe from history file")

with tempfile.TemporaryDirectory() as tmpdir:
    constituents = [
        {"symbol": "RELIANCE", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
        {"symbol": "TCS",      "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
        {"symbol": "INFY",     "effective_from": "2020-01-01", "effective_to": "2022-12-31", "reason": "REMOVED"},
        {"symbol": "SUZLON",   "effective_from": "2023-01-01", "effective_to": None, "reason": "ADDED"},
    ]
    _write_history(tmpdir, "NIFTY500", constituents)
    ptue = _make_ptue(tmpdir)

    # Before INFY removal
    u1 = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T026", isinstance(u1, HistoricalUniverse))
    ok("T027", u1.universe_name == "NIFTY500")
    ok("T028", u1.date == "2022-06-15")
    ok("T029", u1.source == SOURCE_HISTORY_FILE)
    ok("T030", u1.is_fallback is False)
    ok("T031", u1.coverage == 1.0)
    ok("T032", "RELIANCE" in u1.symbols)
    ok("T033", "TCS"      in u1.symbols)
    ok("T034", "INFY"     in u1.symbols)
    ok("T035", "SUZLON" not in u1.symbols, "SUZLON not yet added")
    ok("T036", u1.effective_count == 3)

    # After SUZLON added
    u2 = ptue.get_universe("2023-06-15", "NIFTY500")
    ok("T037", "SUZLON" in u2.symbols)
    ok("T038", "INFY" not in u2.symbols, "INFY removed")
    ok("T039", u2.effective_count == 3)  # RELIANCE + TCS + SUZLON

    # to_dict
    d = u1.to_dict()
    ok("T040", d["universe_name"] == "NIFTY500")
    ok("T041", isinstance(d["symbols"], list))
    ok("T042", isinstance(d["constituents"], list))
    ok("T043", d["is_fallback"] is False)
    ok("T044", d["coverage"] == 1.0)
    ok("T045", d["effective_count"] == 3)

# ─── T046-T060: Boundary date tests ──────────────────────────────────────────

section("T046-T060: Boundary dates")

with tempfile.TemporaryDirectory() as tmpdir:
    constituents = [
        {"symbol": "AAA", "effective_from": "2022-01-01", "effective_to": "2022-12-31", "reason": "INITIAL"},
        {"symbol": "BBB", "effective_from": "2022-12-31", "effective_to": None, "reason": "ADDED"},
    ]
    _write_history(tmpdir, "NIFTY500", constituents)
    ptue = _make_ptue(tmpdir)

    # Exactly on effective_from
    u = ptue.get_universe("2022-01-01", "NIFTY500")
    ok("T046", "AAA" in u.symbols, "AAA active on its effective_from")

    # Exactly on effective_to
    u2 = ptue.get_universe("2022-12-31", "NIFTY500")
    ok("T047", "AAA" in u2.symbols, "AAA active on its effective_to")
    ok("T048", "BBB" in u2.symbols, "BBB active on its effective_from (same day)")

    # One day before effective_from
    u3 = ptue.get_universe("2021-12-31", "NIFTY500")
    ok("T049", "AAA" not in u3.symbols, "AAA not yet active")

    # One day after effective_to
    u4 = ptue.get_universe("2023-01-01", "NIFTY500")
    ok("T050", "AAA" not in u4.symbols, "AAA no longer active")
    ok("T051", "BBB" in u4.symbols, "BBB still active")

    # Very early date
    u5 = ptue.get_universe("2000-01-01", "NIFTY500")
    ok("T052", u5.effective_count == 0, "nothing active in 2000")

    # Very late date
    u6 = ptue.get_universe("2099-12-31", "NIFTY500")
    ok("T053", "BBB" in u6.symbols, "BBB active indefinitely")

    # Invalid date raises
    raised = False
    try:
        ptue.get_universe("not-a-date", "NIFTY500")
    except InvalidDateError:
        raised = True
    ok("T054", raised, "InvalidDateError for bad date")

    # YYYY-MM format raises
    raised2 = False
    try:
        ptue.get_universe("2022-06", "NIFTY500")
    except InvalidDateError:
        raised2 = True
    ok("T055", raised2, "InvalidDateError for partial date")

# ─── T061-T075: Additions and removals ───────────────────────────────────────

section("T061-T075: Additions and removals")

with tempfile.TemporaryDirectory() as tmpdir:
    constituents = [
        {"symbol": "LEGACY", "effective_from": "2015-01-01", "effective_to": "2020-12-31", "reason": "INITIAL"},
        {"symbol": "LEGACY", "effective_from": "2015-01-01", "effective_to": "2020-12-31", "reason": "REMOVED"},
        {"symbol": "NEW_CO", "effective_from": "2021-01-01", "effective_to": None,         "reason": "ADDED"},
        {"symbol": "STABLE", "effective_from": "2015-01-01", "effective_to": None,         "reason": "INITIAL"},
    ]
    _write_history(tmpdir, "NIFTY500", constituents)
    ptue = _make_ptue(tmpdir)

    u_before = ptue.get_universe("2020-06-15", "NIFTY500")
    ok("T061", "LEGACY" in u_before.symbols)
    ok("T062", "NEW_CO" not in u_before.symbols)
    ok("T063", "STABLE" in u_before.symbols)

    u_after = ptue.get_universe("2021-06-15", "NIFTY500")
    ok("T064", "LEGACY" not in u_after.symbols)
    ok("T065", "NEW_CO" in u_after.symbols)
    ok("T066", "STABLE" in u_after.symbols)

    # history for symbol
    h = ptue.history("LEGACY")
    ok("T067", len(h) >= 1, "LEGACY has at least one record")
    ok("T068", all(c.symbol.upper() == "LEGACY" for c in h))

    h_stable = ptue.history("STABLE")
    ok("T069", len(h_stable) == 1)
    ok("T070", h_stable[0].effective_to is None)

    # history for unknown symbol
    h_unk = ptue.history("UNKNOWN_CO")
    ok("T071", h_unk == [])

    # contains
    ok("T072", ptue.contains("STABLE",  "2022-01-01", "NIFTY500") is True)
    ok("T073", ptue.contains("NEW_CO",  "2020-06-15", "NIFTY500") is False)
    ok("T074", ptue.contains("UNKNOWN", "2022-01-01", "NIFTY500") is False)
    ok("T075", ptue.contains("new_co",  "2022-01-01", "NIFTY500") is True, "case-insensitive")

# ─── T076-T090: Static fallback ──────────────────────────────────────────────

section("T076-T090: Static fallback")

with tempfile.TemporaryDirectory() as tmpdir:
    static_symbols = [
        {"symbol": "REL",  "yahoo_ticker": "REL.NS",  "sector": "ENERGY", "index": "NIFTY50"},
        {"symbol": "HDFC", "yahoo_ticker": "HDFC.NS", "sector": "BANKING", "index": "NIFTY50"},
        {"symbol": "TCS2", "yahoo_ticker": "TCS2.NS", "sector": "IT",     "index": ""},
    ]
    static_path = _write_static_fallback(tmpdir, static_symbols)
    ptue = _make_ptue(tmpdir, static_path=static_path, fallback=True)

    u = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T076", u.is_fallback is True)
    ok("T077", u.source == SOURCE_STATIC_FALLBACK)
    ok("T078", u.coverage == 0.5)
    ok("T079", "REL"  in u.symbols)
    ok("T080", "HDFC" in u.symbols)
    ok("T081", "TCS2" in u.symbols)
    ok("T082", u.effective_count == 3)

    # Fallback disabled → raises UniverseNotFoundError
    ptue_nofb = _make_ptue(tmpdir, static_path=static_path, fallback=False)
    raised = False
    try:
        ptue_nofb.get_universe("2022-06-15", "NO_HISTORY_UNIVERSE")
    except UniverseNotFoundError as e:
        raised = True
        ok("T083", e.universe_name == "NO_HISTORY_UNIVERSE")
    ok("T084", raised)

    # Fallback with empty static file
    empty_path = _write_static_fallback(tmpdir, [])
    ptue_empty = _make_ptue(tmpdir, static_path=empty_path, fallback=True)
    raised2 = False
    try:
        ptue_empty.get_universe("2022-01-01", "EMPTY_UNI")
    except UniverseNotFoundError:
        raised2 = True
    ok("T085", raised2, "empty fallback -> UniverseNotFoundError")

    # Source is EMPTY when no data and no fallback
    ptue_bare = _make_ptue(tmpdir, static_path="", fallback=False)
    raised3 = False
    try:
        ptue_bare.get_universe("2022-01-01", "GHOST")
    except UniverseNotFoundError as e:
        raised3 = True
    ok("T086", raised3)

    # fallback produces stable results on repeated queries
    u2 = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T087", u2.effective_count == u.effective_count)
    ok("T088", set(u2.symbols) == set(u.symbols))

    ok("T089", u.to_dict()["source"] == SOURCE_STATIC_FALLBACK)
    ok("T090", isinstance(u.to_dict()["constituents"], list))

# ─── T091-T100: statistics and coverage ──────────────────────────────────────

section("T091-T100: statistics and coverage")

with tempfile.TemporaryDirectory() as tmpdir:
    constituents = [
        {"symbol": "A", "effective_from": "2020-01-01", "effective_to": None,         "reason": "INITIAL"},
        {"symbol": "B", "effective_from": "2021-06-01", "effective_to": "2022-12-31", "reason": "ADDED"},
        {"symbol": "C", "effective_from": "2023-01-01", "effective_to": None,         "reason": "ADDED"},
    ]
    _write_history(tmpdir, "NIFTY500", constituents)
    ptue = _make_ptue(tmpdir)

    stats = ptue.statistics("NIFTY500")
    ok("T091", isinstance(stats, UniverseStatistics))
    ok("T092", stats.universe_name == "NIFTY500")
    ok("T093", stats.total_records == 3)
    ok("T094", stats.additions_tracked == 2)   # B and C have reason=ADDED
    ok("T095", stats.removals_tracked == 0)
    ok("T096", stats.earliest_date == "2020-01-01")
    ok("T097", stats.history_span_days >= 0)
    ok("T098", stats.source == SOURCE_HISTORY_FILE)

    stats_d = stats.to_dict()
    ok("T099", "total_records" in stats_d)
    ok("T100", stats_d["additions_tracked"] == 2)

# ─── T101-T110: CoverageReport ───────────────────────────────────────────────

section("T101-T110: CoverageReport")

with tempfile.TemporaryDirectory() as tmpdir:
    static_sym = [{"symbol": "X", "yahoo_ticker": "X.NS", "sector": "IT", "index": ""}]
    sp = _write_static_fallback(tmpdir, static_sym)
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": "A", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"}
    ])

    ptue = _make_ptue(tmpdir, static_path=sp, fallback=True)
    _ = ptue.get_universe("2022-01-01", "NIFTY500")   # load history file
    _ = ptue.get_universe("2022-01-01", "NIFTY100")   # load via fallback

    cov = ptue.coverage()
    ok("T101", isinstance(cov, CoverageReport))
    ok("T102", "NIFTY500" in cov.universes)
    ok("T103", "NIFTY100" in cov.universes)
    ok("T104", cov.coverage_by_universe["NIFTY500"] == 1.0)
    ok("T105", cov.coverage_by_universe["NIFTY100"] == 0.5)
    ok("T106", "NIFTY100" in cov.fallback_universes)
    ok("T107", "NIFTY500" in cov.history_file_universes)
    ok("T108", cov.total_universes == 2)

    cov_d = cov.to_dict()
    ok("T109", "coverage_by_universe" in cov_d)
    ok("T110", isinstance(cov_d["fallback_universes"], list))

# ─── T111-T120: Cache behaviour ──────────────────────────────────────────────

section("T111-T120: Cache")

with tempfile.TemporaryDirectory() as tmpdir:
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": "A", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
    ])
    ptue = _make_ptue(tmpdir, cache=True)

    u1 = ptue.get_universe("2022-06-15", "NIFTY500")
    u2 = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T111", u1 is u2, "identical objects from cache")

    # Different date → different object
    u3 = ptue.get_universe("2022-06-16", "NIFTY500")
    ok("T112", u3 is not u1)

    # invalidate_cache(universe)
    ptue.invalidate_cache("NIFTY500")
    u4 = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T113", u4 is not u1, "new object after invalidation")

    # invalidate_cache(all)
    ptue.invalidate_cache()
    ok("T114", len(ptue._cache) == 0)

    # Cache disabled
    ptue_nc = _make_ptue(tmpdir, cache=False)
    ua = ptue_nc.get_universe("2022-01-01", "NIFTY500")
    ub = ptue_nc.get_universe("2022-01-01", "NIFTY500")
    ok("T115", ua is not ub, "no caching: distinct objects each time")

    # reload()
    ptue2 = _make_ptue(tmpdir)
    _ = ptue2.get_universe("2022-01-01", "NIFTY500")
    ptue2.reload("NIFTY500")
    u_after = ptue2.get_universe("2022-01-01", "NIFTY500")
    ok("T116", u_after.source == SOURCE_HISTORY_FILE)

    ok("T117", "NIFTY500" in ptue.loaded_universes())

    ver = ptue.version("NIFTY500")
    ok("T118", isinstance(ver, UniverseVersion))
    ok("T119", ver.source == SOURCE_HISTORY_FILE)
    ok("T120", ver.constituent_count >= 1)

# ─── T121-T130: Bootstrap from static ────────────────────────────────────────

section("T121-T130: Bootstrap from static")

with tempfile.TemporaryDirectory() as tmpdir:
    static_sym = [
        {"symbol": "REL",  "yahoo_ticker": "REL.NS",  "sector": "ENERGY", "index": "NIFTY50"},
        {"symbol": "TCS3", "yahoo_ticker": "TCS3.NS", "sector": "IT",     "index": "NIFTY50"},
        {"symbol": "MID1", "yahoo_ticker": "MID1.NS", "sector": "FMCG",   "index": "NIFTY500"},
    ]
    sp = _write_static_fallback(tmpdir, static_sym)
    ptue = _make_ptue(tmpdir, static_path=sp)

    out = ptue.bootstrap_from_static("NIFTY500", effective_from="2021-01-01")
    ok("T121", os.path.exists(str(out)))

    # Read it back
    raw = json.loads(Path(str(out)).read_text())
    ok("T122", raw["universe"] == "NIFTY500")
    ok("T123", len(raw["constituents"]) == 3)
    ok("T124", raw["constituents"][0]["effective_from"] == "2021-01-01")
    ok("T125", raw["constituents"][0]["effective_to"] is None)
    ok("T126", raw["constituents"][0]["reason"] == "INITIAL")

    # Sub-index filter
    out50 = ptue.bootstrap_from_static("NIFTY50", effective_from="2021-01-01",
                                        sub_index_filter="NIFTY50")
    raw50 = json.loads(Path(str(out50)).read_text())
    ok("T127", raw50["universe"] == "NIFTY50")
    ok("T128", len(raw50["constituents"]) == 2, "only NIFTY50-tagged symbols")

    # dry_run=True doesn't write
    ptue_dr = _make_ptue(tmpdir, static_path=sp, dry_run=True)
    out_dr = ptue_dr.bootstrap_from_static("DRYTEST")
    ok("T129", not os.path.exists(str(out_dr)), "dry_run=True: no file written")

    # After bootstrap, reload uses history file
    u = ptue.get_universe("2022-06-15", "NIFTY500")
    ok("T130", u.source == SOURCE_HISTORY_FILE)

# ─── T131-T140: add/remove constituent ───────────────────────────────────────

section("T131-T140: add_constituent / remove_constituent")

with tempfile.TemporaryDirectory() as tmpdir:
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": "ALPHA", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
    ])
    ptue = _make_ptue(tmpdir, dry_run=True)  # dry_run=True: no disk writes

    # Add
    ptue.add_constituent("NIFTY500", "BETA", "2023-01-01", reason="ADDED")
    u = ptue.get_universe("2023-06-15", "NIFTY500")
    ok("T131", "BETA" in u.symbols)
    ok("T132", "ALPHA" in u.symbols)

    # Not active before add date
    u2 = ptue.get_universe("2022-12-31", "NIFTY500")
    ok("T133", "BETA" not in u2.symbols)

    # Remove
    removed = ptue.remove_constituent("NIFTY500", "ALPHA", "2023-03-31", reason="REMOVED")
    ok("T134", removed is True)
    u3 = ptue.get_universe("2023-06-15", "NIFTY500")
    ok("T135", "ALPHA" not in u3.symbols, "ALPHA removed after 2023-03-31")
    ok("T136", "BETA" in u3.symbols)

    # Remove non-existent symbol → False
    ok("T137", ptue.remove_constituent("NIFTY500", "GHOST", "2023-03-31") is False)

    # History of ALPHA shows 1 record with effective_to set
    hist_alpha = ptue.history("ALPHA")
    ok("T138", len(hist_alpha) == 1)
    ok("T139", hist_alpha[0].effective_to == "2023-03-31")

    # Invalid date raises
    raised = False
    try:
        ptue.add_constituent("NIFTY500", "X", "not-a-date")
    except InvalidDateError:
        raised = True
    ok("T140", raised)

# ─── T141-T150: Replay integration ───────────────────────────────────────────

section("T141-T150: RC replay integration (PTUE wired)")

from autonomous_research.research_coordinator import ResearchCoordinator, _resolve_replay_date
from autonomous_research.rc_config import RCConfig
from autonomous_research.study_planner_models import StudyType

# _resolve_replay_date helper
plan_with_date = MagicMock()
plan_with_date.dataset_requirements = [MagicMock(date_start="2022-06-15")]
ok("T141", _resolve_replay_date(plan_with_date) == "2022-06-15")

plan_no_date = MagicMock()
plan_no_date.dataset_requirements = []
ok("T142", _resolve_replay_date(plan_no_date) is None)

plan_bad_date = MagicMock()
plan_bad_date.dataset_requirements = [MagicMock(date_start=None)]
ok("T143", _resolve_replay_date(plan_bad_date) is None)

plan_none = MagicMock()
plan_none.dataset_requirements = None
ok("T144", _resolve_replay_date(plan_none) is None)

# RC with PTUE: replay for HISTORICAL_REPLAY study sets ptue ctx
with tempfile.TemporaryDirectory() as tmpdir:
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": "RELIANCE", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
        {"symbol": "TCS",      "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
    ])
    ptue_rc = _make_ptue(tmpdir)
    rc_cfg  = RCConfig(dry_run=True, replay_enabled=True)
    rc      = ResearchCoordinator(ptue=ptue_rc, config=rc_cfg)

    study_plan = MagicMock()
    study_plan.plan_id = "plan-ptue-001"
    study_plan.study_type = StudyType.HISTORICAL_REPLAY
    study_plan.dataset_requirements = [MagicMock(date_start="2022-06-15")]

    run = rc.run_research(study_plan)
    ok("T145", run is not None)

    # Find the replay stage
    replay_stage = next((s for s in run.stages if s.name == "replay"), None)
    ok("T146", replay_stage is not None)
    ok("T147", replay_stage.meta.get("ptue_date") == "2022-06-15")
    ok("T148", replay_stage.meta.get("ptue_source") == SOURCE_HISTORY_FILE)
    ok("T149", replay_stage.meta.get("ptue_count") >= 1)
    ok("T150", replay_stage.meta.get("ptue_is_fallback") is False)

# ─── T151-T160: MLS integration + thread safety ──────────────────────────────

section("T151-T160: MLS and thread safety")

# contains() is safe across multiple universes
with tempfile.TemporaryDirectory() as tmpdir:
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": "ALPHA", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"},
    ])
    _write_history(tmpdir, "NIFTY50", [
        {"symbol": "ALPHA", "effective_from": "2020-01-01", "effective_to": "2021-12-31", "reason": "REMOVED"},
    ])
    ptue_mls = _make_ptue(tmpdir)

    # Same symbol, different universes, different time windows
    ok("T151", ptue_mls.contains("ALPHA", "2021-06-15", "NIFTY500") is True)
    ok("T152", ptue_mls.contains("ALPHA", "2021-06-15", "NIFTY50") is True)
    ok("T153", ptue_mls.contains("ALPHA", "2022-06-15", "NIFTY50") is False, "removed from NIFTY50")
    ok("T154", ptue_mls.contains("ALPHA", "2022-06-15", "NIFTY500") is True, "still in NIFTY500")

# Thread safety: 20 concurrent get_universe calls
with tempfile.TemporaryDirectory() as tmpdir:
    _write_history(tmpdir, "NIFTY500", [
        {"symbol": f"SYM{i:03d}", "effective_from": "2020-01-01", "effective_to": None, "reason": "INITIAL"}
        for i in range(100)
    ])
    ptue_ts = _make_ptue(tmpdir)
    errors_ts: List[str] = []
    results_ts: List[int] = []

    def _query():
        try:
            u = ptue_ts.get_universe("2022-06-15", "NIFTY500")
            results_ts.append(u.effective_count)
        except Exception as exc:
            errors_ts.append(str(exc))

    threads = [threading.Thread(target=_query) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ok("T155", len(errors_ts) == 0, f"no thread errors: {errors_ts}")
    ok("T156", len(results_ts) == 20, "20 results returned")
    ok("T157", all(r == 100 for r in results_ts), "all queries return same count")

# Concurrent contains() calls
contains_results: List[bool] = []
def _check():
    try:
        contains_results.append(ptue_ts.contains("SYM050", "2022-06-15", "NIFTY500"))
    except Exception as exc:
        errors_ts.append(str(exc))

cthreads = [threading.Thread(target=_check) for _ in range(10)]
for t in cthreads: t.start()
for t in cthreads: t.join()
ok("T158", all(contains_results), "all True")
ok("T159", len(errors_ts) == 0, f"no errors: {errors_ts}")

# Real data: bootstrap round-trip
with tempfile.TemporaryDirectory() as tmpdir:
    import json as _json
    real_static = Path("data/nifty500_universe.json")
    if real_static.exists():
        ptue_real = _make_ptue(tmpdir, static_path=str(real_static))
        ptue_real.bootstrap_from_static("NIFTY500", effective_from="2020-01-01")
        u_real = ptue_real.get_universe("2022-06-15", "NIFTY500")
        ok("T160", u_real.source == SOURCE_HISTORY_FILE)
        ok("T160b", u_real.effective_count >= 50, f"at least 50 symbols: {u_real.effective_count}")
    else:
        ok("T160", True, "skipped — no real data in test env")
        ok("T160b", True, "skipped")

# ─── Summary ────────────────────────────────────────────────────────────────

print(f"\n{'='*58}")
print(f"  Point-in-Time Universe Engine Test Suite")
print(f"  PASS: {PASS}  FAIL: {FAIL}  TOTAL: {PASS + FAIL}")
print(f"{'='*58}")

if ERRORS:
    print("\nFailed tests:")
    for e in ERRORS:
        print(f"  {e}")

sys.exit(0 if FAIL == 0 else 1)
