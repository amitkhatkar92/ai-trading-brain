"""
test_knowledge_vs_strategy_001.py

Validation tests for KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001.
Tests verify data integrity, key empirical findings, and model definitions.

Methodology: READ-ONLY. All tests query production databases on VPS or use
pre-computed research results. No writes, no strategy changes, no orders.

Run on VPS: python3 test_knowledge_vs_strategy_001.py
Run locally (with results JSON): python3 test_knowledge_vs_strategy_001.py --local
"""

import json
import os
import sys
import sqlite3
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

IS_VPS = os.path.exists("/root/ai-trading-brain/data/control_tower.db")
DATA_DIR = Path("/root/ai-trading-brain/data") if IS_VPS else Path(".")

def _find_file(name: str) -> Path:
    """Find a result file in CWD, /tmp, or workspace root."""
    for base in [Path("."), Path("/tmp"), Path("/root/ai-trading-brain")]:
        candidate = base / name
        if candidate.exists():
            return candidate
    return Path(name)  # fallback to CWD (will report missing)

RESULTS_JSON = _find_file("knowledge_vs_strategy_results.json")
COMBO_JSON = _find_file("knowledge_combination_analysis.json")
SUMMARY_CSV = _find_file("strategy_incremental_value_summary.csv")

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results: List[Dict[str, Any]] = []


def test(test_id: str, name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    results.append({
        "id": test_id,
        "name": name,
        "status": status,
        "detail": detail,
    })
    marker = "OK" if condition else "XX"
    print(f"  [{marker}] {test_id}: {name}")
    if not condition:
        print(f"       DETAIL: {detail}")


def skip(test_id: str, name: str, reason: str) -> None:
    results.append({"id": test_id, "name": name, "status": SKIP, "detail": reason})
    print(f"  [−] {test_id}: {name}  (SKIP: {reason})")


# ---------------------------------------------------------------------------
# T001-T010: Research Results JSON Integrity
# ---------------------------------------------------------------------------

def test_results_json_integrity() -> None:
    print("\n=== T001-T010: Results JSON Integrity ===")

    if not RESULTS_JSON.exists():
        skip("T001", "Results JSON exists", f"{RESULTS_JSON} not found")
        for tid in ["T002", "T003", "T004", "T005", "T006", "T007", "T008", "T009", "T010"]:
            skip(tid, "Results JSON field check", "parent file missing")
        return

    with open(RESULTS_JSON) as f:
        r = json.load(f)

    test("T001", "Results JSON is valid JSON and is a dict", isinstance(r, dict))
    test("T002", "audit_id is correct", r.get("audit_id") == "KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001")
    test("T003", "overall_verdict is non-empty string", isinstance(r.get("overall_verdict"), str) and len(r["overall_verdict"]) > 5)
    test("T004", "section_4 above_20dma winner_mean > control_mean",
         r.get("section_4_market_leader_feature_analysis", {}).get("feature_discriminators", {}).get("above_20dma", {}).get("winner_mean", 0) >
         r.get("section_4_market_leader_feature_analysis", {}).get("feature_discriminators", {}).get("above_20dma", {}).get("control_mean", 1))
    test("T005", "section_4 volume_ratio winner_mean > control_mean",
         r.get("section_4_market_leader_feature_analysis", {}).get("feature_discriminators", {}).get("volume_ratio", {}).get("winner_mean", 0) >
         r.get("section_4_market_leader_feature_analysis", {}).get("feature_discriminators", {}).get("volume_ratio", {}).get("control_mean", 1))
    test("T006", "section_5 model_A precision > model_D precision",
         r.get("section_5_strong_mover_selection_simulation", {}).get("models", {}).get("model_A", {}).get("avg_precision_at_6", 0) >
         r.get("section_5_strong_mover_selection_simulation", {}).get("models", {}).get("model_D", {}).get("avg_precision_at_6", 1))
    test("T007", "section_6 knowledge edge reverses at day 5",
         r.get("section_6_market_leader_outcome_distributions", {}).get("outcomes", {}).get("return_5d", {}).get("diff", 0) < 0,
         "Edge should be negative at day 5 (control outperforms)")
    test("T008", "section_7 all strategies have WR < 0.50",
         all(v.get("win_rate", 1.0) < 0.50
             for v in r.get("section_7_strategy_performance_from_learning_db", {}).get("strategies", {}).values()))
    test("T009", "section_9 approved confidence > rejected confidence",
         r.get("section_9_decision_quality_analysis", {}).get("approved", {}).get("avg_confidence", 0) >
         r.get("section_9_decision_quality_analysis", {}).get("rejected", {}).get("avg_confidence", 1))
    test("T010", "section_10 bad_rate = 0.5 (50% blocked signals are grade D)",
         abs(r.get("section_10_todays_blocked_signals", {}).get("bad_rate", -1) - 0.5) < 0.01)


# ---------------------------------------------------------------------------
# T011-T020: Knowledge Combination JSON Integrity
# ---------------------------------------------------------------------------

def test_combination_json_integrity() -> None:
    print("\n=== T011-T020: Knowledge Combination JSON Integrity ===")

    if not COMBO_JSON.exists():
        for tid in ["T011", "T012", "T013", "T014", "T015", "T016", "T017", "T018", "T019", "T020"]:
            skip(tid, "Combination JSON check", f"{COMBO_JSON} not found")
        return

    with open(COMBO_JSON) as f:
        c = json.load(f)

    test("T011", "Combination JSON is valid dict", isinstance(c, dict))
    test("T012", "feature_combination_analysis section exists", "feature_combination_analysis" in c)
    test("T013", "signal_decay_analysis section exists", "signal_decay_analysis" in c)
    test("T014", "day_1 edge is positive",
         c.get("signal_decay_analysis", {}).get("holding_periods", {}).get("day_1", {}).get("edge", -1) > 0)
    test("T015", "day_5 edge is negative (momentum reverses)",
         c.get("signal_decay_analysis", {}).get("holding_periods", {}).get("day_5", {}).get("edge", 1) < 0)
    test("T016", "Model A precision > Model C precision",
         c.get("feature_combination_analysis", {}).get("model_comparison", {}).get("model_A_pure_volume", {}).get("precision_at_6", 0) >
         c.get("feature_combination_analysis", {}).get("model_comparison", {}).get("model_C_knowledge_sector", {}).get("precision_at_6", 1))
    test("T017", "Model B precision = 0 (data gap documented)",
         c.get("feature_combination_analysis", {}).get("model_comparison", {}).get("model_B_signal_births", {}).get("precision_at_6", -1) == 0.0)
    test("T018", "time_horizon_mismatch_analysis section exists", "time_horizon_mismatch_analysis" in c)
    test("T019", "sector_alignment_gap section exists", "sector_alignment_gap" in c)
    test("T020", "sector filter at Layer 3 is false (gap identified)",
         c.get("sector_alignment_gap", {}).get("finding") == "NO_SECTOR_FILTER_IN_LAYER_3")


# ---------------------------------------------------------------------------
# T021-T030: Strategy Incremental Value CSV Integrity
# ---------------------------------------------------------------------------

def test_summary_csv_integrity() -> None:
    print("\n=== T021-T030: Summary CSV Integrity ===")

    if not SUMMARY_CSV.exists():
        for tid in [f"T0{i}" for i in range(21, 31)]:
            skip(tid, "Summary CSV check", f"{SUMMARY_CSV} not found")
        return

    rows = {}
    with open(SUMMARY_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows[row["metric"]] = row["value"]

    test("T021", "CSV has audit_id row", "audit_id" in rows)
    test("T022", "approved_signals_n is 1185",
         rows.get("approved_signals_n") == "1185")
    test("T023", "rejected_signals_n is 167",
         rows.get("rejected_signals_n") == "167")
    test("T024", "debate_confidence_gap is 0.680",
         abs(float(rows.get("debate_confidence_gap", 0)) - 0.680) < 0.01)
    test("T025", "signal_births_outcome_gap is ALL_UNKNOWN",
         rows.get("signal_births_outcome_gap") == "ALL_UNKNOWN")
    test("T026", "strategies_above_50pct_wr is 0",
         rows.get("strategies_above_50pct_wr") == "0")
    test("T027", "knowledge_edge_day5_pct is negative",
         float(rows.get("knowledge_edge_day5_pct", 1)) < 0)
    test("T028", "today_bad_rate is 0.5",
         abs(float(rows.get("today_bad_rate", 0)) - 0.5) < 0.01)
    test("T029", "score_discriminates_useful_vs_bad is false",
         rows.get("score_discriminates_useful_vs_bad", "true").lower() == "false")
    test("T030", "time_horizon_mismatch is true",
         rows.get("time_horizon_mismatch", "false").lower() == "true")


# ---------------------------------------------------------------------------
# T031-T050: Live Database Tests (VPS only)
# ---------------------------------------------------------------------------

def test_live_databases() -> None:
    print("\n=== T031-T050: Live Database Tests (VPS only) ===")

    if not IS_VPS:
        for tid in range(31, 51):
            skip(f"T0{tid}", "VPS database test", "Not running on VPS")
        return

    # ct_decisions
    ct_db = sqlite3.connect(DATA_DIR / "control_tower.db")
    ct_db.row_factory = sqlite3.Row

    approved = ct_db.execute("SELECT COUNT(*) as n, AVG(confidence) as avg_conf, AVG(technical_score) as avg_tech FROM ct_decisions WHERE decision='APPROVED'").fetchone()
    rejected = ct_db.execute("SELECT COUNT(*) as n, AVG(confidence) as avg_conf FROM ct_decisions WHERE decision='REJECTED'").fetchone()

    test("T031", "ct_decisions approved count ≥ 1185",
         approved["n"] >= 1185, f"n={approved['n']}")
    test("T032", "ct_decisions rejected count ≥ 167",
         rejected["n"] >= 167, f"n={rejected['n']}")
    test("T033", "approved avg_confidence > rejected avg_confidence",
         (approved["avg_conf"] or 0) > (rejected["avg_conf"] or 1),
         f"approved={approved['avg_conf']:.3f} rejected={rejected['avg_conf']:.3f}")
    test("T034", "approved avg_confidence > 6.5",
         (approved["avg_conf"] or 0) > 6.5, f"avg_conf={approved['avg_conf']:.3f}")
    # avg_technical only meaningful when IS NOT NULL — re-query with filter
    approved_tech = ct_db.execute(
        "SELECT AVG(technical_score) as avg_tech FROM ct_decisions WHERE decision='APPROVED' AND technical_score IS NOT NULL AND technical_score > 0"
    ).fetchone()
    test("T035", "approved avg_technical (non-null) > 7.0",
         (approved_tech["avg_tech"] or 0) > 7.0, f"avg_tech={approved_tech['avg_tech']}")
    ct_db.close()

    # market_behavior.db
    mb_db = sqlite3.connect(DATA_DIR / "market_behavior.db")
    mb_db.row_factory = sqlite3.Row

    signal_count = mb_db.execute("SELECT COUNT(*) as n FROM signal_births").fetchone()["n"]
    traded_count = mb_db.execute("SELECT COUNT(*) as n FROM signal_births WHERE trade_executed=1").fetchone()["n"]
    unknown_count = mb_db.execute("SELECT COUNT(*) as n FROM signal_births WHERE final_state='UNKNOWN'").fetchone()["n"]
    nonzero_move = mb_db.execute("SELECT COUNT(*) as n FROM signal_births WHERE actual_move_pct != 0.0").fetchone()["n"]

    test("T036", "signal_births count ≥ 3335", signal_count >= 3335, f"n={signal_count}")
    test("T037", "signal_births trade_executed=0 for ALL rows",
         traded_count == 0, f"traded={traded_count} (should be 0)")
    # T038: verify no signals have a resolved outcome (WIN/LOSS/etc) — all are unresolved
    resolved_count = mb_db.execute(
        "SELECT COUNT(*) as n FROM signal_births WHERE final_state IN ('WIN','LOSS','BREAK_EVEN','PARTIAL','FILLED','CLOSED')"
    ).fetchone()["n"]
    test("T038", "signal_births has no resolved final_state (data gap confirmed)",
         resolved_count == 0, f"resolved={resolved_count} (should be 0 -- OIOS outcomes not populated)")
    test("T039", "signal_births actual_move_pct=0 for ALL rows",
         nonzero_move == 0, f"nonzero={nonzero_move} (should be 0 — data gap confirmed)")

    # market leaders
    leaders = mb_db.execute("SELECT COUNT(*) as n FROM market_leaders_daily").fetchone()["n"]
    winners = mb_db.execute("SELECT COUNT(*) as n FROM market_leaders_daily WHERE leader_type='WINNER'").fetchone()["n"]

    test("T040", "market_leaders_daily count ≥ 1410", leaders >= 1410, f"n={leaders}")
    test("T041", "market leaders include winners", winners > 0, f"winners={winners}")

    # feature analysis
    above_20dma_winner = mb_db.execute("""
        SELECT AVG(mf.feature_value) as avg_val
        FROM market_leader_features mf
        JOIN market_leaders_daily ml ON ml.leader_id = mf.leader_id
        WHERE mf.feature_name='above_20dma' AND ml.leader_type='WINNER'
    """).fetchone()["avg_val"]

    above_20dma_control = mb_db.execute("""
        SELECT AVG(mf.feature_value) as avg_val
        FROM market_leader_features mf
        JOIN market_leaders_daily ml ON ml.leader_id = mf.leader_id
        WHERE mf.feature_name='above_20dma' AND ml.leader_type!='WINNER'
    """).fetchone()["avg_val"]

    test("T042", "above_20dma winner mean > 0.75",
         (above_20dma_winner or 0) > 0.75, f"winner={above_20dma_winner:.3f}")
    test("T043", "above_20dma control mean < 0.50",
         (above_20dma_control or 1) < 0.50, f"control={above_20dma_control:.3f}")
    test("T044", "above_20dma winner > control (non-overlapping expected)",
         (above_20dma_winner or 0) > (above_20dma_control or 1),
         f"winner={above_20dma_winner:.3f} control={above_20dma_control:.3f}")

    vol_winner = mb_db.execute("""
        SELECT AVG(mf.feature_value) as avg_val
        FROM market_leader_features mf
        JOIN market_leaders_daily ml ON ml.leader_id = mf.leader_id
        WHERE mf.feature_name='volume_ratio' AND ml.leader_type='WINNER'
    """).fetchone()["avg_val"]

    vol_control = mb_db.execute("""
        SELECT AVG(mf.feature_value) as avg_val
        FROM market_leader_features mf
        JOIN market_leaders_daily ml ON ml.leader_id = mf.leader_id
        WHERE mf.feature_name='volume_ratio' AND ml.leader_type!='WINNER'
    """).fetchone()["avg_val"]

    test("T045", "volume_ratio winner mean > 2.5",
         (vol_winner or 0) > 2.5, f"winner={vol_winner:.3f}")
    test("T046", "volume_ratio control mean < 2.0",
         (vol_control or 3) < 2.0, f"control={vol_control:.3f}")
    test("T047", "volume_ratio winner > 2× control",
         (vol_winner or 0) > 2 * (vol_control or 1e9),
         f"winner={vol_winner:.3f} control={vol_control:.3f}")
    mb_db.close()

    # market_leader_outcomes — signal decay
    mb_db2 = sqlite3.connect(DATA_DIR / "market_behavior.db")
    mb_db2.row_factory = sqlite3.Row

    ret_1d_winner = mb_db2.execute("""
        SELECT AVG(mlo.return_1d) as avg_ret
        FROM market_leader_outcomes mlo
        JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id
        WHERE ml.leader_type='WINNER' AND mlo.return_1d IS NOT NULL
    """).fetchone()["avg_ret"]

    ret_1d_control = mb_db2.execute("""
        SELECT AVG(mlo.return_1d) as avg_ret
        FROM market_leader_outcomes mlo
        JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id
        WHERE ml.leader_type!='WINNER' AND mlo.return_1d IS NOT NULL
    """).fetchone()["avg_ret"]

    ret_5d_winner = mb_db2.execute("""
        SELECT AVG(mlo.return_5d) as avg_ret
        FROM market_leader_outcomes mlo
        JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id
        WHERE ml.leader_type='WINNER' AND mlo.return_5d IS NOT NULL
    """).fetchone()["avg_ret"]

    ret_5d_control = mb_db2.execute("""
        SELECT AVG(mlo.return_5d) as avg_ret
        FROM market_leader_outcomes mlo
        JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id
        WHERE ml.leader_type!='WINNER' AND mlo.return_5d IS NOT NULL
    """).fetchone()["avg_ret"]

    test("T048", "winner return_1d > control return_1d (1-day knowledge edge)",
         (ret_1d_winner or 0) > (ret_1d_control or -1e9),
         f"winner={ret_1d_winner:.3f}% control={ret_1d_control:.3f}%")
    test("T049", "winner return_5d < control return_5d (edge reverses at 5d)",
         (ret_5d_winner or 1e9) < (ret_5d_control or -1e9),
         f"winner={ret_5d_winner:.3f}% control={ret_5d_control:.3f}%")
    test("T050", "winner 1d edge > 0.1%",
         ((ret_1d_winner or 0) - (ret_1d_control or 0)) > 0.1,
         f"edge={(ret_1d_winner or 0) - (ret_1d_control or 0):.3f}%")

    mb_db2.close()


# ---------------------------------------------------------------------------
# T051-T060: Strategy Performance Tests (VPS only)
# ---------------------------------------------------------------------------

def test_strategy_performance() -> None:
    print("\n=== T051-T060: Strategy Performance Tests (VPS only) ===")

    if not IS_VPS:
        for tid in range(51, 61):
            skip(f"T0{tid}", "Strategy performance test", "Not running on VPS")
        return

    ldb_path = DATA_DIR / "learning_db.json"
    if not ldb_path.exists():
        for tid in range(51, 61):
            skip(f"T0{tid}", "learning_db test", "File not found")
        return

    with open(ldb_path) as f:
        ldb = json.load(f)

    stats = ldb.get("strategy_stats", {})

    test("T051", "learning_db has strategy_stats key", "strategy_stats" in ldb)
    test("T052", "At least 6 strategies tracked", len(stats) >= 6, f"n={len(stats)}")
    test("T053", "Mean_Reversion is in stats", "Mean_Reversion" in stats)
    test("T054", "Momentum_Retest is in stats", "Momentum_Retest" in stats)
    test("T055", "Mean_Reversion WR < 0.25",
         stats.get("Mean_Reversion", {}).get("win_rate", 1) < 0.25,
         f"wr={stats.get('Mean_Reversion', {}).get('win_rate', 'N/A')}")
    test("T056", "Momentum_Retest WR < 0.15",
         stats.get("Momentum_Retest", {}).get("win_rate", 1) < 0.15,
         f"wr={stats.get('Momentum_Retest', {}).get('win_rate', 'N/A')}")
    test("T057", "Momentum_Retest total_pnl < 0",
         stats.get("Momentum_Retest", {}).get("total_pnl", 0) < 0,
         f"pnl={stats.get('Momentum_Retest', {}).get('total_pnl', 'N/A')}")
    test("T058", "No strategy has WR ≥ 0.50 (all below governance threshold)",
         all(v.get("win_rate", 0) < 0.50 for v in stats.values()),
         "Found strategy above governance threshold")
    test("T059", "Mean_Reversion total_pnl > 0 (asymmetric payoff)",
         stats.get("Mean_Reversion", {}).get("total_pnl", -1) > 0,
         f"pnl={stats.get('Mean_Reversion', {}).get('total_pnl', 'N/A')}")
    test("T060", "Trend_Pullback WR = 0.0",
         stats.get("Trend_Pullback", {}).get("win_rate", 1) == 0.0,
         f"wr={stats.get('Trend_Pullback', {}).get('win_rate', 'N/A')}")


# ---------------------------------------------------------------------------
# T061-T070: Architectural Constraint Tests
# ---------------------------------------------------------------------------

def test_architectural_constraints() -> None:
    print("\n=== T061-T070: Architectural Constraint Tests ===")

    if not IS_VPS:
        for tid in range(61, 71):
            skip(f"T0{tid}", "Architecture constraint test", "Not running on VPS")
        return

    ct_db = sqlite3.connect(DATA_DIR / "control_tower.db")
    ct_db.row_factory = sqlite3.Row

    # Breakout_Volume is the most approved strategy
    top_strategy = ct_db.execute("""
        SELECT strategy, COUNT(*) as n FROM ct_decisions
        WHERE decision='APPROVED'
        GROUP BY strategy ORDER BY n DESC LIMIT 1
    """).fetchone()

    test("T061", "Breakout_Volume is most approved strategy",
         top_strategy["strategy"] == "Breakout_Volume",
         f"top={top_strategy['strategy']} n={top_strategy['n']}")

    # Equity_Breakout is most rejected strategy
    top_rejected = ct_db.execute("""
        SELECT strategy, COUNT(*) as n FROM ct_decisions
        WHERE decision='REJECTED'
        GROUP BY strategy ORDER BY n DESC LIMIT 1
    """).fetchone()

    test("T062", "Equity_Breakout is most rejected strategy",
         top_rejected["strategy"] == "Equity_Breakout",
         f"top_rejected={top_rejected['strategy']}")

    # Approved confidence is meaningfully above threshold (6.5)
    avg_approved_conf = ct_db.execute(
        "SELECT AVG(confidence) as c FROM ct_decisions WHERE decision='APPROVED'"
    ).fetchone()["c"]
    test("T063", "Approved avg confidence is above 6.5 threshold",
         (avg_approved_conf or 0) > 6.5, f"avg_conf={avg_approved_conf:.3f}")

    # Rejected confidence should be below 6.5 (because they failed the threshold)
    avg_rejected_conf = ct_db.execute(
        "SELECT AVG(confidence) as c FROM ct_decisions WHERE decision='REJECTED'"
    ).fetchone()["c"]
    test("T064", "Rejected avg confidence is below approved",
         (avg_rejected_conf or 0) < (avg_approved_conf or -1),
         f"approved={avg_approved_conf:.3f} rejected={avg_rejected_conf:.3f}")

    # Confidence gap > 0.5
    test("T065", "Debate confidence gap > 0.5",
         ((avg_approved_conf or 0) - (avg_rejected_conf or 0)) > 0.5,
         f"gap={(avg_approved_conf or 0) - (avg_rejected_conf or 0):.3f}")

    ct_db.close()

    # signal_births data gap is verifiable
    mb_db = sqlite3.connect(DATA_DIR / "market_behavior.db")
    mb_db.row_factory = sqlite3.Row
    all_zero = mb_db.execute("SELECT COUNT(*) as n FROM signal_births WHERE ABS(actual_move_pct) > 0.001").fetchone()["n"]
    test("T066", "Data gap confirmed: signal_births actual_move_pct=0 for ALL rows",
         all_zero == 0, f"non-zero rows: {all_zero}")
    all_unknown = mb_db.execute("SELECT COUNT(*) as n FROM signal_births WHERE final_state != 'UNKNOWN'").fetchone()["n"]
    test("T067", "Data gap confirmed: signal_births final_state=UNKNOWN for ALL rows",
         all_unknown == 0, f"non-UNKNOWN rows: {all_unknown}")
    mb_db.close()

    # Paper trades count
    pt_path = DATA_DIR / "paper_trades.csv"
    if pt_path.exists():
        with open(pt_path) as f:
            pt_rows = list(csv.DictReader(f))
        test("T068", "paper_trades.csv has ≥ 40 rows",
             len(pt_rows) >= 40, f"n={len(pt_rows)}")
    else:
        skip("T068", "paper_trades.csv count", "File not found")

    # Architecture invariant: strategy gate before debate
    # This is a code-level invariant; validate by checking that
    # EARLY_ABORT_LOW_WR signals never appear in ct_decisions
    early_abort_in_ct = sqlite3.connect(DATA_DIR / "control_tower.db")
    early_abort_in_ct.row_factory = sqlite3.Row
    abort_in_ct = early_abort_in_ct.execute(
        "SELECT COUNT(*) as n FROM ct_decisions WHERE rejection_reason LIKE '%EARLY_ABORT%'"
    ).fetchone()["n"]
    test("T069", "EARLY_ABORT_LOW_WR signals do NOT appear in ct_decisions (strategy gate before debate)",
         abort_in_ct == 0, f"EARLY_ABORT in ct_decisions: {abort_in_ct}")
    early_abort_in_ct.close()

    # n_trading_dates >= 45 (47 confirmed in audit)
    mb_db3 = sqlite3.connect(DATA_DIR / "market_behavior.db")
    mb_db3.row_factory = sqlite3.Row
    n_dates = mb_db3.execute("SELECT COUNT(DISTINCT trade_date) as n FROM market_leaders_daily").fetchone()["n"]
    test("T070", "market_leaders_daily has ≥ 45 trading dates",
         n_dates >= 45, f"n_dates={n_dates}")
    mb_db3.close()


# ---------------------------------------------------------------------------
# T071-T075: Key Finding Assertion Tests
# ---------------------------------------------------------------------------

def test_key_findings() -> None:
    print("\n=== T071-T075: Key Finding Assertions ===")

    if not RESULTS_JSON.exists():
        for tid in range(71, 76):
            skip(f"T0{tid}", "Key finding assertion", f"{RESULTS_JSON} missing")
        return

    with open(RESULTS_JSON) as f:
        r = json.load(f)

    # Verdict
    verdict = r.get("overall_verdict", "")
    test("T071", "Verdict is STRATEGY_GATE_WORKING variant",
         "STRATEGY_GATE_WORKING" in verdict, f"verdict={verdict}")

    # Sector filter gap identified
    summary = r.get("summary", {})
    test("T072", "Sector filter gap identified in knowledge failure modes",
         "sector" in summary.get("Q8_knowledge_failure_modes", "").lower())

    # OIOS fix identified as improvement lever
    q12 = summary.get("Q12_improvement_levers", [])
    oios_mentioned = any("oios" in lever.lower() or "outcome" in lever.lower() for lever in q12)
    test("T073", "OIOS outcome fix identified as improvement lever", oios_mentioned, f"Q12={q12}")

    # Time horizon mismatch identified
    q13 = summary.get("Q13_final_verdict", "")
    test("T074", "Time horizon mismatch identified in final verdict",
         "time" in q13.lower() or "horizon" in q13.lower() or "1-day" in q13.lower(),
         f"Q13={q13}")

    # Data gap acknowledged
    q11 = summary.get("Q11_data_infrastructure_gaps", [])
    test("T075", "signal_births data gap documented",
         any("signal" in g.lower() for g in q11), f"Q11={q11}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001 — Test Suite")
    print(f"Environment: {'VPS' if IS_VPS else 'LOCAL'}")
    print("=" * 60)

    test_results_json_integrity()
    test_combination_json_integrity()
    test_summary_csv_integrity()
    test_live_databases()
    test_strategy_performance()
    test_architectural_constraints()
    test_key_findings()

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["status"] == PASS)
    failed = sum(1 for r in results if r["status"] == FAIL)
    skipped = sum(1 for r in results if r["status"] == SKIP)

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} passed  |  {failed} failed  |  {skipped} skipped")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if r["status"] == FAIL:
                print(f"  ✗ {r['id']}: {r['name']}")
                if r["detail"]:
                    print(f"    {r['detail']}")

    # Write results to JSON
    out = {
        "test_suite": "test_knowledge_vs_strategy_001",
        "audit_id": "KNOWLEDGE_VS_STRATEGY_VALUE_AUDIT_001",
        "total": total, "passed": passed, "failed": failed, "skipped": skipped,
        "tests": results
    }
    out_path = Path("test_kvs_001_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nDetailed results written to {out_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
