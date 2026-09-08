"""
scripts/knowledge_system/selection_characteristic_analyzer_001.py
===================================================================
Phase 2 (Selection Intelligence Layer) — Winner / Loser / Missed-Winner /
Correct-Rejection characteristic analysis.

READ-ONLY ANALYSIS LAYER. Standalone, manually invoked. Never imported by
master_orchestrator.py or any live trading path. Does not write back to
mover_discovery_v3.py, final_c2_selector.py, StrategyLab, KDA, DecisionEngine,
Risk, or Execution. Output is a report only.

Four groups (per direction, UP/DOWN analyzed separately):
  SELECTED_WON     — selected_final_5=True,  outcome direction-correct
  SELECTED_FAILED  — selected_final_5=True,  outcome direction-wrong
  REJECTED_WON     — selected_final_5=False, outcome direction-correct AND
                      meaningful (>=2%) — a "missed winner"
  REJECTED_FAILED  — selected_final_5=False, everything else — a
                      "correct rejection"

Groups are computed directly from selected_final_5 + t1_ret_pct/direction,
NOT from the Classification enum — the enum's CORRECT_SELECT value is
overloaded (used both for "selected and won" and for "not selected and
nothing interesting happened"), which is fine for KSL-001's original
purpose but would blur these four groups if reused here.

Only analyzes EvidenceRecords where atr_pct is not None (i.e. produced by
the Phase-1-updated pipeline) — legacy pre-Phase-1 records lack the raw
V3 feature vector and cannot be used for this analysis.

Phase 2B adds a regime dimension (BULL/BEAR/RANGE — regime is computed by
_get_regime() in final_trading_architecture_shadow_001.py from real NIFTY
(^NSEI) OHLCV data; VOLATILE is not distinguished since VIX is not tracked).
Regime was backfilled retroactively on 2026-09-07 after discovering
ohlcv_daily had zero '^NSEI' rows (index data was never persisted), which
is why every prior evidence record showed regime=UNAVAILABLE. This layer
answers: 'does a feature's importance differ by market regime?' Sample
sizes per regime x direction x group are small (single-digit to low-double
digit) with ~30 days of history — treat as early/exploratory, not proof.

Phase 2C adds feature-combination analysis (see COMBINATIONS below) — a
small, pre-specified set of hypothesis-driven pairings, not a blind search
over all possible combinations, to avoid mining accidental correlations.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT / "data" / "shadow_evidence_ledger.jsonl"

GE2_THRESHOLD = 2.0
MIN_SAMPLE_FOR_STATS = 15  # below this, report but flag as low-confidence

FEATURES = [
    "atr_pct", "mom_5d", "mom_accel", "vol_ratio",
    "rs_pct_5d", "rsi_14", "hv_20", "vol_expansion",
]

GROUP_SELECTED_WON = "SELECTED_WON"
GROUP_SELECTED_FAILED = "SELECTED_FAILED"
GROUP_REJECTED_WON = "REJECTED_WON"       # missed winner
GROUP_REJECTED_FAILED = "REJECTED_FAILED"  # correct rejection


def load_records(ledger_path: Path = LEDGER_PATH) -> List[Dict[str, Any]]:
    """Load evidence records, keeping only Phase-1-complete rows (atr_pct
    present), deduplicated by (trade_date, symbol, direction) keeping the
    most recently processed record (handles force=True regeneration)."""
    latest: Dict[str, Dict[str, Any]] = {}
    if not ledger_path.exists():
        return []
    for line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("atr_pct") is None:
            continue  # legacy pre-Phase-1 record, no feature vector
        if rec.get("t1_ret_pct") is None:
            continue  # outcome not yet resolved, can't classify group
        key = f"{rec.get('trade_date')}|{rec.get('symbol')}|{rec.get('direction')}"
        existing = latest.get(key)
        if existing is None or rec.get("processed_at", "") > existing.get("processed_at", ""):
            latest[key] = rec
    return list(latest.values())


def _direction_correct(direction: str, t1: float) -> bool:
    return (direction == "UP" and t1 > 0) or (direction == "DOWN" and t1 < 0)


def assign_group(rec: Dict[str, Any]) -> Optional[str]:
    t1 = rec.get("t1_ret_pct")
    if t1 is None:
        return None
    direction = rec.get("direction", "UP")
    selected = bool(rec.get("selected_final_5", False))
    correct = _direction_correct(direction, t1)
    meaningful = correct and abs(t1) >= GE2_THRESHOLD

    if selected:
        return GROUP_SELECTED_WON if correct else GROUP_SELECTED_FAILED
    return GROUP_REJECTED_WON if meaningful else GROUP_REJECTED_FAILED


def _stats(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "stdev": None}
    return {
        "n": n,
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "stdev": round(statistics.stdev(values), 4) if n >= 2 else 0.0,
    }


def _cohens_d(a: List[float], b: List[float]) -> Optional[float]:
    """Standardized mean difference (a - b) / pooled_stdev. None if either
    group has <2 samples (stdev undefined) or pooled_stdev is 0."""
    if len(a) < 2 or len(b) < 2:
        return None
    sa, sb = statistics.stdev(a), statistics.stdev(b)
    na, nb = len(a), len(b)
    pooled = (((na - 1) * sa ** 2 + (nb - 1) * sb ** 2) / (na + nb - 2)) ** 0.5
    if pooled == 0:
        return None
    return round((statistics.mean(a) - statistics.mean(b)) / pooled, 4)


def analyze(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_direction: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "UP": defaultdict(list), "DOWN": defaultdict(list)
    }
    for rec in records:
        direction = rec.get("direction", "UP")
        if direction not in ("UP", "DOWN"):
            continue
        group = assign_group(rec)
        if group is None:
            continue
        by_direction[direction][group].append(rec)

    report: Dict[str, Any] = {"generated_from_n_records": len(records), "directions": {}}

    for direction in ("UP", "DOWN"):
        groups = by_direction[direction]
        group_counts = {g: len(groups.get(g, [])) for g in
                         (GROUP_SELECTED_WON, GROUP_SELECTED_FAILED,
                          GROUP_REJECTED_WON, GROUP_REJECTED_FAILED)}
        dir_report: Dict[str, Any] = {"group_counts": group_counts, "features": {}}

        for feat in FEATURES:
            feat_report: Dict[str, Any] = {}
            group_values: Dict[str, List[float]] = {}
            for g in (GROUP_SELECTED_WON, GROUP_SELECTED_FAILED,
                      GROUP_REJECTED_WON, GROUP_REJECTED_FAILED):
                vals = [r[feat] for r in groups.get(g, []) if r.get(feat) is not None]
                group_values[g] = vals
                feat_report[g] = _stats(vals)

            # Key comparisons the user asked for:
            feat_report["selected_won_vs_selected_failed_cohens_d"] = _cohens_d(
                group_values[GROUP_SELECTED_WON], group_values[GROUP_SELECTED_FAILED])
            feat_report["rejected_won_vs_rejected_failed_cohens_d"] = _cohens_d(
                group_values[GROUP_REJECTED_WON], group_values[GROUP_REJECTED_FAILED])
            feat_report["selected_won_vs_rejected_won_cohens_d"] = _cohens_d(
                group_values[GROUP_SELECTED_WON], group_values[GROUP_REJECTED_WON])

            dir_report["features"][feat] = feat_report

        report["directions"][direction] = dir_report

    return report


def format_summary(report: Dict[str, Any]) -> str:
    """Human-readable summary — flags |d|>=0.3 as noteworthy, always shows n."""
    lines = [
        f"Selection Characteristic Analysis — {report['generated_from_n_records']} evidence records",
        "(Cohen's d: standardized mean difference. |d|<0.2 negligible, "
        "0.2-0.5 small, 0.5-0.8 medium, >0.8 large. LOW-CONFIDENCE if any "
        f"group n < {MIN_SAMPLE_FOR_STATS}.)",
        "",
    ]
    for direction, dir_report in report["directions"].items():
        gc = dir_report["group_counts"]
        lines.append(f"=== {direction} ===  "
                      f"SELECTED_WON={gc[GROUP_SELECTED_WON]}  "
                      f"SELECTED_FAILED={gc[GROUP_SELECTED_FAILED]}  "
                      f"REJECTED_WON(missed winners)={gc[GROUP_REJECTED_WON]}  "
                      f"REJECTED_FAILED={gc[GROUP_REJECTED_FAILED]}")
        min_n = min(gc.values()) if gc else 0
        low_conf = " [LOW CONFIDENCE — small samples]" if min_n < MIN_SAMPLE_FOR_STATS else ""
        for feat, fr in dir_report["features"].items():
            d1 = fr["selected_won_vs_selected_failed_cohens_d"]
            d2 = fr["rejected_won_vs_rejected_failed_cohens_d"]
            d3 = fr["selected_won_vs_rejected_won_cohens_d"]
            lines.append(
                f"  {feat:14s} SELECTED_WON.mean={fr[GROUP_SELECTED_WON]['mean']}  "
                f"SELECTED_FAILED.mean={fr[GROUP_SELECTED_FAILED]['mean']}  "
                f"REJECTED_WON.mean={fr[GROUP_REJECTED_WON]['mean']}  "
                f"REJECTED_FAILED.mean={fr[GROUP_REJECTED_FAILED]['mean']}  "
                f"| d(won_vs_failed_selected)={d1}  d(missed_vs_correct_reject)={d2}  "
                f"d(selected_won_vs_missed_won)={d3}{low_conf}"
            )
        lines.append("")
    return "\n".join(lines)


def analyze_by_regime(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 2B: same 4-group breakdown as analyze(), further split by
    regime (BULL/BEAR/RANGE). Records with regime in (None, "UNAVAILABLE",
    "UNKNOWN") are excluded — they carry no regime information."""
    by_regime_dir: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(
        lambda: {"UP": defaultdict(list), "DOWN": defaultdict(list)}
    )
    excluded_no_regime = 0
    for rec in records:
        regime = rec.get("regime")
        if regime in (None, "UNAVAILABLE", "UNKNOWN"):
            excluded_no_regime += 1
            continue
        direction = rec.get("direction", "UP")
        if direction not in ("UP", "DOWN"):
            continue
        group = assign_group(rec)
        if group is None:
            continue
        by_regime_dir[regime][direction][group].append(rec)

    report: Dict[str, Any] = {
        "generated_from_n_records": len(records),
        "excluded_no_regime": excluded_no_regime,
        "regimes": {},
    }

    for regime, dirs in sorted(by_regime_dir.items()):
        regime_report: Dict[str, Any] = {"directions": {}}
        for direction in ("UP", "DOWN"):
            groups = dirs[direction]
            group_counts = {g: len(groups.get(g, [])) for g in
                             (GROUP_SELECTED_WON, GROUP_SELECTED_FAILED,
                              GROUP_REJECTED_WON, GROUP_REJECTED_FAILED)}
            dir_report: Dict[str, Any] = {"group_counts": group_counts, "features": {}}
            for feat in FEATURES:
                group_values: Dict[str, List[float]] = {}
                for g in (GROUP_SELECTED_WON, GROUP_SELECTED_FAILED,
                          GROUP_REJECTED_WON, GROUP_REJECTED_FAILED):
                    vals = [r[feat] for r in groups.get(g, []) if r.get(feat) is not None]
                    group_values[g] = vals
                feat_report = {g: _stats(group_values[g]) for g in group_values}
                feat_report["selected_won_vs_selected_failed_cohens_d"] = _cohens_d(
                    group_values[GROUP_SELECTED_WON], group_values[GROUP_SELECTED_FAILED])
                feat_report["rejected_won_vs_rejected_failed_cohens_d"] = _cohens_d(
                    group_values[GROUP_REJECTED_WON], group_values[GROUP_REJECTED_FAILED])
                dir_report["features"][feat] = feat_report
            regime_report["directions"][direction] = dir_report
        report["regimes"][regime] = regime_report

    return report


def format_regime_summary(report: Dict[str, Any]) -> str:
    lines = [
        f"Regime-Split Characteristic Analysis (Phase 2B) — "
        f"{report['generated_from_n_records']} records, "
        f"{report['excluded_no_regime']} excluded (no regime)",
        f"(LOW-CONFIDENCE if any group n < {MIN_SAMPLE_FOR_STATS}; "
        f"with ~30 days of history most regime x group cells will be small "
        f"— treat as exploratory, not proof.)",
        "",
    ]
    for regime, regime_report in report["regimes"].items():
        for direction, dir_report in regime_report["directions"].items():
            gc = dir_report["group_counts"]
            min_n = min(gc.values()) if gc else 0
            low_conf = " [LOW CONFIDENCE]" if min_n < MIN_SAMPLE_FOR_STATS else ""
            lines.append(
                f"=== regime={regime} direction={direction} ===  "
                f"SELECTED_WON={gc[GROUP_SELECTED_WON]}  "
                f"SELECTED_FAILED={gc[GROUP_SELECTED_FAILED]}  "
                f"REJECTED_WON={gc[GROUP_REJECTED_WON]}  "
                f"REJECTED_FAILED={gc[GROUP_REJECTED_FAILED]}{low_conf}"
            )
            for feat, fr in dir_report["features"].items():
                d1 = fr["selected_won_vs_selected_failed_cohens_d"]
                d2 = fr["rejected_won_vs_rejected_failed_cohens_d"]
                lines.append(
                    f"  {feat:14s} SELECTED_WON.mean={fr[GROUP_SELECTED_WON]['mean']}  "
                    f"SELECTED_FAILED.mean={fr[GROUP_SELECTED_FAILED]['mean']}  "
                    f"REJECTED_WON.mean={fr[GROUP_REJECTED_WON]['mean']}  "
                    f"REJECTED_FAILED.mean={fr[GROUP_REJECTED_FAILED]['mean']}  "
                    f"| d(won_vs_failed_selected)={d1}  d(missed_vs_correct_reject)={d2}"
                )
            lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2C — feature-combination analysis
# ─────────────────────────────────────────────────────────────────────────────
# Deliberately NOT a brute-force search over all feature pairs/triples (the
# user explicitly asked us to avoid "blindly testing thousands of
# combinations and finding accidental correlations"). Instead this tests a
# small, pre-specified set of hypothesis-driven combinations, each directly
# derived from either the Phase 2A single-feature findings or a plain
# domain-reasoning rationale from the user's own list. No combination is
# added or removed based on how the results turn out.
#
# mom_5d, mom_accel and rs_pct_5d are direction-signed (UP candidates run
# positive, DOWN candidates run negative/low) so "favorable" is direction-
# relative: high raw value for UP, low raw value for DOWN. rsi_14, atr_pct,
# hv_20 and vol_expansion are treated as direction-neutral; their band
# edges (tertiles) are computed separately within each direction's own
# population so they reflect that direction's own distribution.

DIRECTIONAL_FEATURES = {"mom_5d", "mom_accel", "rs_pct_5d"}

COMBINATIONS = [
    {
        "name": "high_momentum_and_high_rs",
        "label": "high momentum (mom_5d) + high relative strength (rs_pct_5d)",
        "conditions": [("mom_5d", "high"), ("rs_pct_5d", "high")],
        "rule": lambda bands: bands["mom_5d"] == "high" and bands["rs_pct_5d"] == "high",
    },
    {
        "name": "high_mom_accel_and_moderate_rsi",
        "label": "high momentum acceleration (mom_accel) + moderate RSI",
        "conditions": [("mom_accel", "high"), ("rsi_14", "moderate")],
        "rule": lambda bands: bands["mom_accel"] == "high" and bands["rsi_14"] == "moderate",
    },
    {
        "name": "strong_rs_and_increasing_volume",
        "label": "strong relative strength (rs_pct_5d) + volume expansion",
        "conditions": [("rs_pct_5d", "high"), ("vol_expansion", "high")],
        "rule": lambda bands: bands["rs_pct_5d"] == "high" and bands["vol_expansion"] == "high",
    },
    {
        "name": "low_rsi_and_high_mom_accel",
        "label": "low RSI + high momentum acceleration",
        "conditions": [("rsi_14", "low"), ("mom_accel", "high")],
        "rule": lambda bands: bands["rsi_14"] == "low" and bands["mom_accel"] == "high",
    },
    {
        "name": "high_volatility_and_strong_momentum",
        "label": "high volatility (hv_20) + strong momentum (mom_5d)",
        "conditions": [("hv_20", "high"), ("mom_5d", "high")],
        "rule": lambda bands: bands["hv_20"] == "high" and bands["mom_5d"] == "high",
    },
]


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def _build_band_thresholds(records: List[Dict[str, Any]], direction: str) -> Dict[str, Dict[str, float]]:
    """Per-feature tertile cut points (p33, p66), computed from the pooled
    population (all 4 groups) within a single direction. For direction-
    signed features, 'favorable' orientation flips for DOWN (see module
    note above) — thresholds are computed on the raw value either way;
    the flip is applied when the band is read (_band_of)."""
    thresholds: Dict[str, Dict[str, float]] = {}
    for feat in FEATURES:
        vals = sorted(r[feat] for r in records if r.get("direction") == direction and r.get(feat) is not None)
        thresholds[feat] = {"p33": _percentile(vals, 0.33), "p66": _percentile(vals, 0.66)}
    return thresholds


def _band_of(feat: str, value: float, direction: str, thresholds: Dict[str, Dict[str, float]]) -> str:
    """Returns 'high' / 'moderate' / 'low'. For direction-signed features,
    orientation is flipped for DOWN so 'high' always means 'more favorable
    for this direction's move' (e.g. more negative mom_5d for DOWN)."""
    p33, p66 = thresholds[feat]["p33"], thresholds[feat]["p66"]
    if feat in DIRECTIONAL_FEATURES and direction == "DOWN":
        # favorable = lower raw value for DOWN (stronger down-conviction)
        if value <= p33:
            return "high"
        if value >= p66:
            return "low"
        return "moderate"
    if value >= p66:
        return "high"
    if value <= p33:
        return "low"
    return "moderate"


def _mover_rate(records: List[Dict[str, Any]]) -> Optional[float]:
    """Fraction of records where the move was direction-correct AND
    meaningful (>=GE2_THRESHOLD). None if the list is empty."""
    if not records:
        return None
    hits = sum(
        1 for r in records
        if _direction_correct(r.get("direction", "UP"), r["t1_ret_pct"])
        and abs(r["t1_ret_pct"]) >= GE2_THRESHOLD
    )
    return round(hits / len(records), 4)


def analyze_combinations(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 2C: for each pre-specified combination, per direction, report:
      - overall lift: mover-rate among ALL candidates satisfying the combo
        vs not (the "would this sharpen the 20-stock pool" question)
      - rejected lift: same, restricted to REJECTED candidates only (the
        "would this catch more missed winners" question)
      - selected lift: same, restricted to SELECTED candidates only (the
        "would this have filtered our own failures" question)
    """
    report: Dict[str, Any] = {"generated_from_n_records": len(records), "directions": {}}

    for direction in ("UP", "DOWN"):
        dir_records = [r for r in records if r.get("direction") == direction]
        thresholds = _build_band_thresholds(dir_records, direction)

        # pre-compute each record's band membership once
        bands_by_id = []
        for r in dir_records:
            bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                     for feat in FEATURES if r.get(feat) is not None}
            bands_by_id.append((r, bands))

        combo_results = []
        for combo in COMBINATIONS:
            true_all, false_all = [], []
            true_rej, false_rej = [], []
            true_sel, false_sel = [], []
            for r, bands in bands_by_id:
                try:
                    matches = combo["rule"](bands)
                except KeyError:
                    continue  # a needed feature/band missing for this record
                selected = bool(r.get("selected_final_5", False))
                (true_all if matches else false_all).append(r)
                if selected:
                    (true_sel if matches else false_sel).append(r)
                else:
                    (true_rej if matches else false_rej).append(r)

            combo_results.append({
                "name": combo["name"],
                "label": combo["label"],
                "overall": {"n_true": len(true_all), "n_false": len(false_all),
                            "rate_true": _mover_rate(true_all), "rate_false": _mover_rate(false_all)},
                "rejected_only": {"n_true": len(true_rej), "n_false": len(false_rej),
                                  "rate_true": _mover_rate(true_rej), "rate_false": _mover_rate(false_rej)},
                "selected_only": {"n_true": len(true_sel), "n_false": len(false_sel),
                                  "rate_true": _mover_rate(true_sel), "rate_false": _mover_rate(false_sel)},
            })

        report["directions"][direction] = {"combinations": combo_results}

    return report


def format_combination_summary(report: Dict[str, Any]) -> str:
    lines = [
        f"Feature-Combination Analysis (Phase 2C) — {report['generated_from_n_records']} records",
        "Pre-specified, hypothesis-driven combinations only (no blind search).",
        f"'rate' = fraction of candidates in that bucket whose move was direction-correct "
        f"AND >= {GE2_THRESHOLD}% (a 'mover'). LOW-CONFIDENCE if n < {MIN_SAMPLE_FOR_STATS}.",
        "",
    ]
    for direction, dir_report in report["directions"].items():
        lines.append(f"=== {direction} ===")
        for c in dir_report["combinations"]:
            lines.append(f"  [{c['label']}]")
            for scope_name, scope_key in (
                ("all candidates (20-pool question)", "overall"),
                ("rejected only (missed-winner question)", "rejected_only"),
                ("selected only (would-it-filter-our-failures question)", "selected_only"),
            ):
                s = c[scope_key]
                low_conf = ""
                if (s["n_true"] and s["n_true"] < MIN_SAMPLE_FOR_STATS) or \
                   (s["n_false"] and s["n_false"] < MIN_SAMPLE_FOR_STATS):
                    low_conf = " [LOW CONFIDENCE]"
                lift = (round(s["rate_true"] - s["rate_false"], 4)
                        if s["rate_true"] is not None and s["rate_false"] is not None else None)
                lines.append(
                    f"    {scope_name}: combo_true(n={s['n_true']}, mover_rate={s['rate_true']})  "
                    f"combo_false(n={s['n_false']}, mover_rate={s['rate_false']})  "
                    f"lift={lift}{low_conf}"
                )
            lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2D — winner / missed-winner fingerprint decomposition
# ─────────────────────────────────────────────────────────────────────────────
# Takes the single strongest Phase 2C finding (UP: low RSI + high momentum
# acceleration) and asks two questions the raw combination lift can't answer
# on its own:
#   1. Is the fingerprint CONCENTRATED in winners/missed-winners, or is it
#      just as common among failed picks and correct rejections? (group
#      concentration — % of each of the 4 groups that exhibits it)
#   2. Is the COMBINED condition meaningfully stronger than either of its
#      two components alone? (component decomposition)
# This is intentionally scoped to the one candidate Phase 2C flagged, not a
# general fingerprint-mining tool — expanding to new candidate fingerprints
# should happen only after new ones clear the same Phase 2C bar.

FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL = {
    "name": "UP_low_rsi_high_accel",
    "label": "UP: low RSI + high momentum acceleration",
    "direction": "UP",
    "components": {
        "low_rsi_alone": lambda bands: bands["rsi_14"] == "low",
        "high_accel_alone": lambda bands: bands["mom_accel"] == "high",
        "combined": lambda bands: bands["rsi_14"] == "low" and bands["mom_accel"] == "high",
    },
}


def analyze_fingerprint(records: List[Dict[str, Any]], fingerprint: Dict[str, Any]) -> Dict[str, Any]:
    direction = fingerprint["direction"]
    dir_records = [r for r in records if r.get("direction") == direction]
    thresholds = _build_band_thresholds(dir_records, direction)

    entries = []
    for r in dir_records:
        bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                  for feat in FEATURES if r.get(feat) is not None}
        entries.append((r, bands, assign_group(r)))

    groups = (GROUP_SELECTED_WON, GROUP_SELECTED_FAILED, GROUP_REJECTED_WON, GROUP_REJECTED_FAILED)
    component_reports = {}
    for name, rule in fingerprint["components"].items():
        true_all, false_all = [], []
        group_true = {g: 0 for g in groups}
        group_total = {g: 0 for g in groups}
        for r, bands, group in entries:
            try:
                matches = rule(bands)
            except KeyError:
                continue
            (true_all if matches else false_all).append(r)
            if group in group_total:
                group_total[group] += 1
                if matches:
                    group_true[group] += 1
        concentration = {
            g: (round(group_true[g] / group_total[g], 4) if group_total[g] else None)
            for g in groups
        }
        component_reports[name] = {
            "n_true": len(true_all), "n_false": len(false_all),
            "mover_rate_true": _mover_rate(true_all), "mover_rate_false": _mover_rate(false_all),
            "group_concentration": concentration,
            "group_counts_true": group_true, "group_counts_total": group_total,
        }

    return {
        "name": fingerprint["name"], "label": fingerprint["label"], "direction": direction,
        "n_records": len(dir_records), "components": component_reports,
    }


def format_fingerprint_summary(report: Dict[str, Any]) -> str:
    lines = [
        f"Winner / Missed-Winner Fingerprint Decomposition (Phase 2D) — "
        f"[{report['label']}] — {report['n_records']} {report['direction']} records",
        "Group concentration = fraction of that group's members exhibiting the "
        "condition (higher in SELECTED_WON / REJECTED_WON than in the FAILED/ "
        "REJECTED_FAILED groups would mean the fingerprint is winner-specific, "
        "not just generically common).",
        "",
    ]
    for name, c in report["components"].items():
        lift = (round(c["mover_rate_true"] - c["mover_rate_false"], 4)
                if c["mover_rate_true"] is not None and c["mover_rate_false"] is not None else None)
        lines.append(f"  [{name}]  n_true={c['n_true']} n_false={c['n_false']}  "
                      f"mover_rate_true={c['mover_rate_true']}  mover_rate_false={c['mover_rate_false']}  "
                      f"lift={lift}")
        gc = c["group_concentration"]
        gt, gtot = c["group_counts_true"], c["group_counts_total"]
        lines.append(
            f"    concentration: SELECTED_WON={gc[GROUP_SELECTED_WON]}({gt[GROUP_SELECTED_WON]}/{gtot[GROUP_SELECTED_WON]})  "
            f"SELECTED_FAILED={gc[GROUP_SELECTED_FAILED]}({gt[GROUP_SELECTED_FAILED]}/{gtot[GROUP_SELECTED_FAILED]})  "
            f"REJECTED_WON={gc[GROUP_REJECTED_WON]}({gt[GROUP_REJECTED_WON]}/{gtot[GROUP_REJECTED_WON]})  "
            f"REJECTED_FAILED={gc[GROUP_REJECTED_FAILED]}({gt[GROUP_REJECTED_FAILED]}/{gtot[GROUP_REJECTED_FAILED]})"
        )
        lines.append("")
    return "\n".join(lines)


def analyze_fingerprint_stability(records: List[Dict[str, Any]], direction: str,
                                   rule) -> Dict[str, Any]:
    """PRELIMINARY time-split check only — splits the existing ~30 days of
    history into an earlier and later half and compares lift in each half
    independently (thresholds recomputed per half, no leakage). This is NOT
    a substitute for Phase 2E's true repeatability test, which requires
    genuinely new incoming trading days accumulated going forward."""
    dir_records = [r for r in records if r.get("direction") == direction]
    dates = sorted({r["trade_date"] for r in dir_records if r.get("trade_date")})
    if len(dates) < 4:
        return {"direction": direction, "error": "insufficient distinct trade_dates for a split"}
    mid = len(dates) // 2
    early_dates, late_dates = set(dates[:mid]), set(dates[mid:])

    def _half_report(date_set):
        half_records = [r for r in dir_records if r.get("trade_date") in date_set]
        thresholds = _build_band_thresholds(half_records, direction)
        true_recs, false_recs = [], []
        for r in half_records:
            bands = {feat: _band_of(feat, r[feat], direction, thresholds)
                      for feat in FEATURES if r.get(feat) is not None}
            try:
                matches = rule(bands)
            except KeyError:
                continue
            (true_recs if matches else false_recs).append(r)
        return {
            "date_range": [min(date_set), max(date_set)] if date_set else None,
            "n_true": len(true_recs), "n_false": len(false_recs),
            "mover_rate_true": _mover_rate(true_recs), "mover_rate_false": _mover_rate(false_recs),
        }

    return {"direction": direction, "early": _half_report(early_dates), "late": _half_report(late_dates)}


def format_stability_summary(report: Dict[str, Any]) -> str:
    if "error" in report:
        return f"Preliminary Stability Check — {report['error']}"
    lines = [
        "Preliminary Time-Split Stability Check (NOT Phase 2E — that requires "
        "genuinely new incoming days, this only splits existing history in half)",
    ]
    for half_name in ("early", "late"):
        h = report[half_name]
        lift = (round(h["mover_rate_true"] - h["mover_rate_false"], 4)
                if h["mover_rate_true"] is not None and h["mover_rate_false"] is not None else None)
        lines.append(
            f"  {half_name:5s} [{h['date_range']}]: n_true={h['n_true']} "
            f"mover_rate_true={h['mover_rate_true']}  n_false={h['n_false']} "
            f"mover_rate_false={h['mover_rate_false']}  lift={lift}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    recs = load_records()
    rep = analyze(recs)
    print(format_summary(rep))
    print()
    regime_rep = analyze_by_regime(recs)
    print(format_regime_summary(regime_rep))
    print()
    combo_rep = analyze_combinations(recs)
    print(format_combination_summary(combo_rep))
    print()
    fp_rep = analyze_fingerprint(recs, FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL)
    print(format_fingerprint_summary(fp_rep))
    print()
    stab_rep = analyze_fingerprint_stability(
        recs, "UP", FINGERPRINT_UP_LOW_RSI_HIGH_ACCEL["components"]["combined"])
    print(format_stability_summary(stab_rep))
