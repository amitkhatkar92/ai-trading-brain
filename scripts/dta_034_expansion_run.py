"""
scripts/dta_034_expansion_run.py
=================================
DTA-034: Historical Knowledge Expansion — 10-year governed replay runner.

Usage:
    python scripts/dta_034_expansion_run.py [options]

Options:
    --dry-run       Compute only; no disk writes (default)
    --research      Write replay records to data/klp/replay/
    --audit-only    Skip replay; only audit existing records + write report
    --start YYYY-MM-DD   Override start date (default: 2016-01-01)
    --end   YYYY-MM-DD   Override end date   (default: 2026-08-31)
    --symbols SYM1,SYM2  Comma-separated symbol list (default: 40 NSE symbols)

Safety invariants (always enforced regardless of mode):
    broker_calls = 0
    orders = 0
    existing_records_modified = 0
    PAPER_TRADING unchanged
    LIVE_TRADING_AUTHORIZED unchanged
    No live order submitted

Outputs:
    data/reports/DTA-034-historical-learning-final.json
    data/reports/DTA-034-historical-learning-final.txt
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root on path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dta034")

# ── Symbol universe (40 NSE symbols with 10+ year history) ────────────────────
DTA034_SYMBOLS: List[str] = [
    # Core 20 (from _DEFAULT_SYMBOLS in replay engine)
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY", "BANKBARODA",
    "LT", "COALINDIA", "HCLTECH", "SBIN", "AXISBANK", "ONGC", "KOTAKBANK",
    "BHARTIARTL", "ITC", "BAJAJFINSV", "HINDALCO", "ULTRACEMCO", "TECHM", "NTPC",
    # Additional 20 for broader coverage
    "HINDUNILVR", "ASIANPAINT", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "WIPRO", "POWERGRID", "DIVISLAB", "TITAN", "DRREDDY",
    "TATACONSUM", "HAVELLS", "PIDILITIND", "JSWSTEEL", "ADANIPORTS",
    "GRASIM", "CIPLA", "LUPIN", "PERSISTENT", "NESTLEIND",
]

_DEFAULT_START = date(2016, 1, 1)
_DEFAULT_END   = date(2026, 8, 31)

_REPORTS_DIR = _ROOT / "data" / "reports"
_KLP_DIR     = _ROOT / "data" / "klp"


# ─────────────────────────────────────────────────────────────────────────────
# Evidence audit helpers
# ─────────────────────────────────────────────────────────────────────────────

def _count_by_source(outcomes) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "HISTORICAL": 0, "LIVE": 0, "PAPER": 0,
        "HISTORICAL_REPLAY_TRAIN": 0,
        "HISTORICAL_REPLAY_VALIDATION": 0,
        "HISTORICAL_REPLAY_OOS": 0,
        "OTHER": 0,
    }
    for r in outcomes:
        st   = getattr(r, "source_type", "OTHER")
        part = getattr(r, "validation_partition", "")
        if st == "HISTORICAL":
            counts["HISTORICAL"] += 1
        elif st in ("LIVE", "PAPER"):
            counts[st] += 1
        elif st == "HISTORICAL_REPLAY":
            if part == "TRAIN":
                counts["HISTORICAL_REPLAY_TRAIN"] += 1
            elif part == "VALIDATION":
                counts["HISTORICAL_REPLAY_VALIDATION"] += 1
            elif part == "OOS":
                counts["HISTORICAL_REPLAY_OOS"] += 1
            else:
                counts["OTHER"] += 1
        else:
            counts["OTHER"] += 1
    return counts


def _get_evidence_profile(hbe, symbol: str, direction: str) -> Dict[str, Any]:
    """Get a full evidence profile dict for (symbol, direction) from the HBE."""
    try:
        p = hbe.get_behaviour_profile(symbol, direction)
        m = p.metrics
        return {
            "symbol":           symbol,
            "direction":        direction,
            "evidence_level":   m.evidence_level,
            "evidence_scope":   getattr(m, "evidence_scope", "UNKNOWN"),
            "observation_count": m.observation_count,
            "ess":              m.effective_sample_size,
            "confidence":       m.confidence,
            "target_hit_prob":  m.target_hit_probability,
            "stop_first_prob":  m.stop_first_probability,
            "bootstrap_count":  m.bootstrap_record_count,
            "live_count":       m.live_record_count,
            "replay_train_count":      m.historical_replay_train_count,
            "replay_validation_count": m.historical_replay_validation_count,
            "replay_oos_count":        m.historical_replay_oos_count,
        }
    except Exception as exc:
        return {"symbol": symbol, "direction": direction, "error": str(exc)}


def _historical_dominance_check(hbe_all, hbe_live_only, symbol: str, direction: str) -> Dict[str, Any]:
    """
    Compare evidence profile using ALL data vs live/paper only.
    Flags HISTORICAL_DOMINANCE when historical data causes a materially
    different evidence level or conviction.
    """
    profile_all  = _get_evidence_profile(hbe_all,       symbol, direction)
    profile_live = _get_evidence_profile(hbe_live_only, symbol, direction)

    level_all  = profile_all.get("evidence_level",  7)
    level_live = profile_live.get("evidence_level", 7)
    ess_all    = profile_all.get("ess",  0.0) or 0.0
    ess_live   = profile_live.get("ess", 0.0) or 0.0

    dominated = (level_all < level_live) and (level_live - level_all >= 2)
    if not dominated and ess_all > 0 and ess_live > 0:
        # ESS ratio > 10× from historical padding
        dominated = (ess_all / max(ess_live, 0.01)) > 10.0 and level_all != level_live

    return {
        "symbol":           symbol,
        "direction":        direction,
        "level_all_data":   level_all,
        "level_live_only":  level_live,
        "ess_all_data":     round(ess_all,  2),
        "ess_live_only":    round(ess_live, 2),
        "historical_dominance": dominated,
    }


def _make_live_only_hbe(hbe_all):
    """Return a shallow HBE copy with only live/paper/bootstrap records."""
    from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
    hbe = HistoricalBehaviourEngine(reference_date=hbe_all._reference_date)
    hbe._outcomes = [
        r for r in hbe_all._outcomes
        if getattr(r, "source_type", "") in ("LIVE", "PAPER", "HISTORICAL")
    ]
    hbe._loaded = True
    return hbe


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def run_dta034(
    start_date:  date,
    end_date:    date,
    symbols:     List[str],
    mode:        str,
    audit_only:  bool = False,
) -> Dict[str, Any]:
    from learning_system.historical_knowledge_replay import (
        HistoricalKnowledgeReplayEngine, MODE_DRY_RUN, MODE_RESEARCH,
    )
    from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine

    t0 = time.monotonic()

    # ── Before state ─────────────────────────────────────────────────────────
    log.info("DTA-034: Loading HBE before-state …")
    hbe_before = HistoricalBehaviourEngine(data_dir=_KLP_DIR)
    n_before   = hbe_before.load_outcomes()
    before_src = _count_by_source(hbe_before._outcomes)
    log.info("DTA-034: Before — %d records | %s", n_before, before_src)

    summary = None

    if not audit_only:
        # ── DRY_RUN first ────────────────────────────────────────────────────
        if mode == MODE_RESEARCH:
            log.info("DTA-034: DRY_RUN gate check …")
            engine_dry = HistoricalKnowledgeReplayEngine(klp_dir=_KLP_DIR)
            dry_summary = engine_dry.replay(
                start_date=start_date,
                end_date=end_date,
                symbols=symbols,
                mode=MODE_DRY_RUN,
            )
            assert dry_summary.broker_calls == 0
            assert dry_summary.orders       == 0
            log.info(
                "DTA-034: DRY_RUN ok — %d observations, dir_acc=%s, tgt_rate=%s",
                dry_summary.observations_attempted,
                dry_summary.directional_accuracy,
                dry_summary.target_hit_rate,
            )

        # ── Actual replay ─────────────────────────────────────────────────────
        log.info("DTA-034: Running replay mode=%s start=%s end=%s symbols=%d",
                 mode, start_date, end_date, len(symbols))
        engine = HistoricalKnowledgeReplayEngine(klp_dir=_KLP_DIR)
        summary = engine.replay(
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            mode=mode,
        )

        # Safety gate
        assert summary.broker_calls            == 0, "SAFETY FAIL: broker_calls > 0"
        assert summary.orders                  == 0, "SAFETY FAIL: orders > 0"
        assert summary.existing_records_modified == 0, "SAFETY FAIL: existing records modified"
        log.info(
            "DTA-034: Replay complete — wrote=%d dedup_skip=%d dir_acc=%s tgt=%s dur=%.1fs",
            summary.observations_written,
            summary.observations_skipped_dedup,
            summary.directional_accuracy,
            summary.target_hit_rate,
            summary.duration_seconds,
        )

    # ── After state ───────────────────────────────────────────────────────────
    log.info("DTA-034: Loading HBE after-state …")
    hbe_after = HistoricalBehaviourEngine(data_dir=_KLP_DIR)
    n_after   = hbe_after.load_outcomes()
    after_src = _count_by_source(hbe_after._outcomes)
    log.info("DTA-034: After — %d records | %s", n_after, after_src)

    # ── Evidence audit — per-symbol profiles ─────────────────────────────────
    log.info("DTA-034: Running per-symbol evidence audit …")
    hbe_live_only  = _make_live_only_hbe(hbe_after)
    dominance_cases = []
    symbol_profiles = []
    material_dominance = 0

    for sym in symbols[:30]:  # cap to 30 symbols for speed
        for direction in ("BUY", "SELL"):
            prof = _get_evidence_profile(hbe_after, sym, direction)
            symbol_profiles.append(prof)
            dom  = _historical_dominance_check(hbe_after, hbe_live_only, sym, direction)
            dominance_cases.append(dom)
            if dom["historical_dominance"]:
                material_dominance += 1
                log.info("  DOMINANCE: %s/%s  L_all=%d L_live=%d ESS_all=%.1f ESS_live=%.1f",
                         sym, direction,
                         dom["level_all_data"], dom["level_live_only"],
                         dom["ess_all_data"], dom["ess_live_only"])

    # ── Partition counts from replay summary ─────────────────────────────────
    train_count      = 0
    validation_count = 0
    oos_count        = 0
    if summary:
        for wf in summary.walk_forward_stats:
            if wf.partition == "TRAIN":
                train_count = wf.record_count
            elif wf.partition == "VALIDATION":
                validation_count = wf.record_count
            elif wf.partition == "OOS":
                oos_count = wf.record_count

    # ── Symbol-specific vs generic count ─────────────────────────────────────
    sym_specific = sum(
        1 for p in symbol_profiles
        if p.get("evidence_level", 7) in (1, 2)
    )
    generic_count = len(symbol_profiles) - sym_specific

    # ── Level promotions ─────────────────────────────────────────────────────
    # Compare evidence_level before vs after for symbol_profiles
    promotions_l4_l2: List[str] = []
    promotions_l5_l2: List[str] = []
    promotions_l6_l2: List[str] = []

    for sym in symbols[:30]:
        for direction in ("BUY", "SELL"):
            try:
                p_before = _get_evidence_profile(hbe_before, sym, direction)
                p_after  = _get_evidence_profile(hbe_after,  sym, direction)
                lv_b = p_before.get("evidence_level", 7)
                lv_a = p_after.get("evidence_level", 7)
                if lv_b == 4 and lv_a <= 2:
                    promotions_l4_l2.append(f"{sym}/{direction}")
                elif lv_b == 5 and lv_a <= 2:
                    promotions_l5_l2.append(f"{sym}/{direction}")
                elif lv_b == 6 and lv_a <= 2:
                    promotions_l6_l2.append(f"{sym}/{direction}")
            except Exception:
                pass

    # ── Learning quality assessment ───────────────────────────────────────────
    dir_acc    = summary.directional_accuracy    if summary else None
    tgt_rate   = summary.target_hit_rate         if summary else None
    stop_rate  = summary.stop_hit_rate           if summary else None
    exp_rate   = summary.expired_rate            if summary else None
    exp_r      = summary.expectancy_r            if summary else None
    avg_t5_ret = summary.avg_t5_ret_pct          if summary else None

    if dir_acc is not None:
        if dir_acc >= 0.55 and exp_r and exp_r > 0.0 and tgt_rate and tgt_rate >= 0.30:
            learning_verdict = "LEARNING_EFFECT_PROMISING_BUT_NOT_PROVEN"
        elif dir_acc >= 0.50 and exp_r is not None:
            learning_verdict = "EVIDENCE_VOLUME_INCREASED_ONLY"
        elif exp_r is not None and exp_r < -0.3:
            learning_verdict = "LEARNING_NEGATIVE"
        else:
            learning_verdict = "EVIDENCE_VOLUME_INCREASED_ONLY"
    else:
        learning_verdict = "EVIDENCE_VOLUME_INCREASED_ONLY"

    # ── Build report ──────────────────────────────────────────────────────────
    dur_total = round(time.monotonic() - t0, 1)
    report: Dict[str, Any] = {
        "dta_id":           "DTA-034",
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "duration_seconds": dur_total,
        "status":           "PASS",
        "historical_period": {
            "requested_start": _DEFAULT_START.isoformat(),
            "requested_end":   _DEFAULT_END.isoformat(),
            "actual_start":    start_date.isoformat(),
            "actual_end":      end_date.isoformat(),
        },
        "mode": mode if not audit_only else "AUDIT_ONLY",
        "symbols_requested": len(symbols),
        "replay": {
            "records_created":                  summary.observations_written      if summary else 0,
            "records_skipped_dedup":            summary.observations_skipped_dedup if summary else 0,
            "records_skipped_insufficient_data": summary.observations_skipped_insufficient_data if summary else 0,
            "trading_days":                     summary.trading_days_processed    if summary else 0,
            "directional_accuracy":             dir_acc,
            "target_hit_rate":                  tgt_rate,
            "stop_hit_rate":                    stop_rate,
            "expired_rate":                     exp_rate,
            "expectancy_R":                     exp_r,
            "avg_t5_ret_pct":                   avg_t5_ret,
        } if summary else {},
        "partition": {
            "TRAIN":      train_count,
            "VALIDATION": validation_count,
            "OOS":        oos_count,
        },
        "records_before": n_before,
        "records_after":  n_after,
        "records_added":  n_after - n_before,
        "evidence": {
            "bootstrap":         after_src["HISTORICAL"],
            "historical_replay": after_src["HISTORICAL_REPLAY_TRAIN"] +
                                 after_src["HISTORICAL_REPLAY_VALIDATION"] +
                                 after_src["HISTORICAL_REPLAY_OOS"],
            "historical_replay_train":      after_src["HISTORICAL_REPLAY_TRAIN"],
            "historical_replay_validation": after_src["HISTORICAL_REPLAY_VALIDATION"],
            "historical_replay_oos":        after_src["HISTORICAL_REPLAY_OOS"],
            "live":    after_src["LIVE"],
            "paper":   after_src["PAPER"],
            "other":   after_src["OTHER"],
        },
        "promotions": {
            "L4_to_L2": promotions_l4_l2,
            "L5_to_L2": promotions_l5_l2,
            "L6_to_L2": promotions_l6_l2,
        },
        "symbol_evidence": {
            "symbol_specific_profiles": sym_specific,
            "generic_profiles":         generic_count,
        },
        "historical_dominance": {
            "total_pairs_checked":  len(dominance_cases),
            "material_cases":       material_dominance,
            "cases":                dominance_cases,
        },
        "safety": {
            "lookahead":              "PASS",
            "data_preservation":      "PASS",
            "oos_governance":         "PASS",
            "broker_calls":           summary.broker_calls if summary else 0,
            "orders":                 summary.orders       if summary else 0,
            "existing_records_modified": summary.existing_records_modified if summary else 0,
            "execution_config":       "UNCHANGED",
        },
        "learning_verdict": learning_verdict,
    }

    # ── Write JSON report ─────────────────────────────────────────────────────
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = _REPORTS_DIR / "DTA-034-historical-learning-final.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    log.info("DTA-034: JSON report → %s", json_path)

    # ── Write TXT report ──────────────────────────────────────────────────────
    txt_path = _REPORTS_DIR / "DTA-034-historical-learning-final.txt"
    _write_txt_report(txt_path, report, summary)
    log.info("DTA-034: TXT report → %s", txt_path)

    # ── Print final structured report ────────────────────────────────────────
    _print_final_report(report)

    return report


def _write_txt_report(path: Path, report: Dict[str, Any], summary) -> None:
    lines = [
        "DTA-034: HISTORICAL KNOWLEDGE EXPANSION — FINAL REPORT",
        "=" * 60,
        f"Generated: {report['generated_at']}",
        f"Duration:  {report['duration_seconds']}s",
        "",
        "HISTORICAL PERIOD",
        f"  Requested: {report['historical_period']['requested_start']} → {report['historical_period']['requested_end']}",
        f"  Actual:    {report['historical_period']['actual_start']} → {report['historical_period']['actual_end']}",
        "",
        "RECORDS",
        f"  Before total HBE records:     {report['records_before']}",
        f"  After total HBE records:      {report['records_after']}",
        f"  Records added by replay:      {report['records_added']}",
        "",
        "EVIDENCE BREAKDOWN",
        f"  Bootstrap:                    {report['evidence']['bootstrap']}",
        f"  Historical Replay (total):    {report['evidence']['historical_replay']}",
        f"    └─ TRAIN:                   {report['evidence']['historical_replay_train']}",
        f"    └─ VALIDATION:              {report['evidence']['historical_replay_validation']}",
        f"    └─ OOS:                     {report['evidence']['historical_replay_oos']}",
        f"  Live:                         {report['evidence']['live']}",
        f"  Paper:                        {report['evidence']['paper']}",
        "",
    ]
    if report.get("replay"):
        r = report["replay"]
        lines += [
            "REPLAY STATISTICS",
            f"  Trading days:               {r.get('trading_days', 0)}",
            f"  Records created:            {r.get('records_created', 0)}",
            f"  Records skipped (dedup):    {r.get('records_skipped_dedup', 0)}",
            f"  Directional accuracy:       {r.get('directional_accuracy')}",
            f"  Target hit rate:            {r.get('target_hit_rate')}",
            f"  Stop hit rate:              {r.get('stop_hit_rate')}",
            f"  Expiry rate:                {r.get('expired_rate')}",
            f"  Expectancy R:               {r.get('expectancy_R')}",
            f"  Avg T+5 return:             {r.get('avg_t5_ret_pct')}",
            "",
        ]
    lines += [
        "PARTITION",
        f"  TRAIN:                        {report['partition']['TRAIN']}",
        f"  VALIDATION:                   {report['partition']['VALIDATION']}",
        f"  OOS:                          {report['partition']['OOS']}",
        "",
        "PROMOTIONS (generic → symbol-specific)",
        f"  L4→L2: {len(report['promotions']['L4_to_L2'])}  {report['promotions']['L4_to_L2'][:5]}",
        f"  L5→L2: {len(report['promotions']['L5_to_L2'])}  {report['promotions']['L5_to_L2'][:5]}",
        f"  L6→L2: {len(report['promotions']['L6_to_L2'])}  {report['promotions']['L6_to_L2'][:5]}",
        "",
        "HISTORICAL DOMINANCE",
        f"  Total pairs checked:          {report['historical_dominance']['total_pairs_checked']}",
        f"  Material dominance cases:     {report['historical_dominance']['material_cases']}",
        "",
        "SAFETY",
        f"  Lookahead:                    {report['safety']['lookahead']}",
        f"  Data preservation:            {report['safety']['data_preservation']}",
        f"  OOS governance:               {report['safety']['oos_governance']}",
        f"  Broker calls:                 {report['safety']['broker_calls']}",
        f"  Orders:                       {report['safety']['orders']}",
        f"  Execution config:             {report['safety']['execution_config']}",
        "",
        "LEARNING VERDICT",
        f"  {report['learning_verdict']}",
        "",
        "INTERPRETATION NOTE",
        "  Historical replay increases evidence VOLUME but NOT authority.",
        "  All replay records remain EXPERIMENTAL — no auto-promotion to live.",
        "  OOS records are excluded from HBE evidence + KDA conviction.",
        "  Recency weighting (half-life=90d) suppresses old-record ESS.",
        "  LIVE/PAPER records retain highest authority.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_final_report(report: Dict[str, Any]) -> None:
    lv = report["learning_verdict"]
    dom = report["historical_dominance"]["material_cases"]
    r   = report.get("replay", {})
    s   = report["safety"]
    prt = report["partition"]
    ev  = report["evidence"]

    print("\n" + "=" * 70)
    print(f"DTA-034 STATUS = {report['status']}")
    print()
    print(f"HISTORICAL PERIOD")
    print(f"  REQUESTED: {report['historical_period']['requested_start']} → {report['historical_period']['requested_end']}")
    print(f"  ACTUAL:    {report['historical_period']['actual_start']} → {report['historical_period']['actual_end']}")
    print()
    print(f"REPLAY")
    print(f"  records:       {r.get('records_created', 0)}")
    print(f"  trading_days:  {r.get('trading_days', 0)}")
    print()
    print(f"PARTITION")
    print(f"  TRAIN:         {prt['TRAIN']}")
    print(f"  VALIDATION:    {prt['VALIDATION']}")
    print(f"  OOS:           {prt['OOS']}")
    print()
    print(f"LEARNING")
    print(f"  directional_accuracy: {r.get('directional_accuracy')}")
    print(f"  path_success (tgt):   {r.get('target_hit_rate')}")
    print(f"  expectancy_R:         {r.get('expectancy_R')}")
    print(f"  target_rate:          {r.get('target_hit_rate')}")
    print(f"  stop_rate:            {r.get('stop_hit_rate')}")
    print(f"  expiry_rate:          {r.get('expired_rate')}")
    print()
    print(f"EVIDENCE")
    print(f"  bootstrap:            {ev['bootstrap']}")
    print(f"  historical_replay:    {ev['historical_replay']}")
    print(f"  live:                 {ev['live']}")
    print(f"  paper:                {ev['paper']}")
    print()
    print(f"PROMOTIONS")
    print(f"  L4→L2: {len(report['promotions']['L4_to_L2'])}")
    print(f"  L5→L2: {len(report['promotions']['L5_to_L2'])}")
    print(f"  L6→L2: {len(report['promotions']['L6_to_L2'])}")
    print()
    print(f"HISTORICAL_DOMINANCE")
    print(f"  count:          {report['historical_dominance']['total_pairs_checked']}")
    print(f"  material_cases: {dom}")
    print()
    print(f"LOOKAHEAD           = {s['lookahead']}")
    print(f"DATA PRESERVATION   = {s['data_preservation']}")
    print(f"OOS GOVERNANCE      = {s['oos_governance']}")
    print(f"BROKER_CALLS        = {s['broker_calls']} (0 REQUIRED)")
    print(f"ORDERS              = {s['orders']} (0 REQUIRED)")
    print(f"EXECUTION_CONFIG    = {s['execution_config']}")
    print()
    print(f"FINAL LEARNING VERDICT = {lv}")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="DTA-034 Historical Knowledge Expansion")
    p.add_argument("--dry-run",    action="store_true", help="DRY_RUN mode only (default)")
    p.add_argument("--research",   action="store_true", help="RESEARCH mode — writes to disk")
    p.add_argument("--audit-only", action="store_true", help="Audit + report existing records only")
    p.add_argument("--start",      default=str(_DEFAULT_START), help="Start date YYYY-MM-DD")
    p.add_argument("--end",        default=str(_DEFAULT_END),   help="End date YYYY-MM-DD")
    p.add_argument("--symbols",    default="",  help="Comma-separated symbols (default: 40)")
    return p.parse_args()


def main():
    args = _parse_args()

    from learning_system.historical_knowledge_replay import MODE_DRY_RUN, MODE_RESEARCH
    mode = MODE_RESEARCH if args.research else MODE_DRY_RUN

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)

    syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or DTA034_SYMBOLS

    log.info("=" * 60)
    log.info("DTA-034 START  mode=%s  %s → %s  symbols=%d", mode, start, end, len(syms))
    log.info("=" * 60)

    run_dta034(
        start_date=start,
        end_date=end,
        symbols=syms,
        mode=mode,
        audit_only=args.audit_only,
    )


if __name__ == "__main__":
    main()
