"""
oios/phase_f/differential_engine.py
Phase F2.5 — Differential Research Engine

The heart of Phase F.

For every winner-control pair, this engine:
  1. Loads the winner's extracted features (market_leader_features)
  2. Computes the same features for the control stock on the same date
  3. Builds a Difference Matrix: for each feature, winner_val vs control_val + delta
  4. Ranks features by |delta| — biggest differentiators first
  5. Computes outcome_gap (winner return - control return) at 1D/3D/5D/20D
  6. Persists to feature_differentials

The aggregate layer answers:
  "Which features most consistently separate winners from look-alike failures?"
  "When the same setup succeeded vs failed on different days, what changed?"

ISOLATION CONTRACT
------------------
Reads:   market_leaders_daily, market_leader_features, market_leader_outcomes,
         market_research_controls, ohlcv_daily, bhav_daily,
         sector_conviction_daily, universe_stocks, signal_births, cause_scores
Writes:  feature_differentials
No writes to any A–E table.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# Minimum similarity score to store a differential pair (avoid noise)
MIN_SIMILARITY_FOR_DIFF = 0.50

# Feature set to compare (must match feature_extractor.ALL_FEATURES)
COMPARABLE_FEATURES = (
    "above_20dma", "above_50dma", "above_200dma",
    "rs_score", "volume_ratio", "atr_expansion",
    "theme_phase_score", "sector_conviction",
    "active_archetypes", "cause_score",
    "sector_rank", "sector_purity",
)


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Per-Day
# ─────────────────────────────────────────────────────────────────────────────

def compute_differentials(trade_date: str, conn: sqlite3.Connection) -> int:
    """
    Compute and store feature differentials for all winner-control pairs on trade_date.

    Typical call order:
        leader_capture.capture_daily_leaders(date, conn)
        feature_extractor.extract_features_batch(leaders, conn)
        control_population.build_controls_for_date(date, conn)
        differential_engine.compute_differentials(date, conn)  ← here

    Returns number of differential rows inserted.
    """
    pairs = _load_pairs(trade_date, conn)
    if not pairs:
        log.info("[DiffEngine] No winner-control pairs for %s", trade_date)
        return 0

    # Pre-fetch winner features (batch: all leaders on this date)
    winner_features: dict[str, dict[str, Optional[float]]] = _load_all_winner_features(
        trade_date, conn
    )

    # Pre-fetch outcome data for winners and controls
    winner_outcomes = _load_leader_outcomes(trade_date, conn)

    inserted = 0
    for pair in pairs:
        lid        = pair["matched_leader_id"]
        cid        = pair["control_id"]
        win_sym    = pair["winner_symbol"]
        ctrl_sym   = pair["control_symbol"]
        sim_score  = pair["similarity_score"]

        if sim_score < MIN_SIMILARITY_FOR_DIFF:
            continue

        # Features for winner (from market_leader_features)
        wf = winner_features.get(win_sym, {})

        # Features for control (compute on-the-fly from raw data)
        cf = _compute_control_features(ctrl_sym, trade_date, conn)

        # Build difference matrix
        diff_list = _difference_matrix(wf, cf)
        if not diff_list:
            continue

        # Outcome gaps
        w_oc = winner_outcomes.get(lid, {})
        c_oc = _load_control_outcomes(cid, conn)
        gaps = _compute_gaps(w_oc, c_oc)

        # Persist
        did = f"DIFF_{trade_date.replace('-','')}_{win_sym}_{ctrl_sym}"
        now = datetime.utcnow().isoformat(timespec="seconds")
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO feature_differentials
                    (differential_id, trade_date, winner_symbol, control_symbol,
                     matched_leader_id, control_id, similarity_score,
                     differing_features,
                     outcome_gap_1d, outcome_gap_3d, outcome_gap_5d, outcome_gap_20d,
                     computed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                did, trade_date, win_sym, ctrl_sym, lid, cid,
                round(sim_score, 4),
                json.dumps(diff_list),
                gaps.get("g1d"), gaps.get("g3d"),
                gaps.get("g5d"), gaps.get("g20d"),
                now,
            ))
        inserted += 1

    log.info("[DiffEngine] %s: inserted %d differential rows", trade_date, inserted)
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Aggregate Analysis
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_top_differentiators(
    as_of_date: str,
    conn: sqlite3.Connection,
    lookback_days: int = 30,
    min_pairs: int = 5,
) -> list[dict]:
    """
    Across all high-similarity winner-control pairs in the lookback window,
    find which features most consistently have larger values in winners.

    Returns list of dicts sorted by separation_power desc:
        {
          feature:          str,
          winner_higher_pct: float,   # fraction of pairs where winner > control
          avg_delta:        float,    # mean (winner_val - control_val)
          avg_outcome_gap:  float,    # mean outcome_gap_1d when this feature differs
          pair_count:       int,
        }
    """
    start_date = (date.fromisoformat(as_of_date) - timedelta(days=lookback_days)).isoformat()

    rows = conn.execute("""
        SELECT differing_features, outcome_gap_1d
        FROM feature_differentials
        WHERE trade_date BETWEEN ? AND ?
          AND similarity_score >= ?
          AND differing_features IS NOT NULL
    """, (start_date, as_of_date, MIN_SIMILARITY_FOR_DIFF)).fetchall()

    if not rows:
        return []

    # Aggregate per feature
    stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "winner_higher": 0,
        "sum_delta": 0.0, "sum_gap": 0.0,
    })

    for row in rows:
        try:
            diff_list = json.loads(row[0] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue
        gap = row[1]

        for entry in diff_list:
            feat  = entry.get("feature", "")
            delta = entry.get("delta")
            if feat and delta is not None:
                s = stats[feat]
                s["total"] += 1
                if delta > 0:
                    s["winner_higher"] += 1
                s["sum_delta"] += delta
                if gap is not None:
                    s["sum_gap"] += gap

    result = []
    for feat, s in stats.items():
        if s["total"] < min_pairs:
            continue
        winner_pct = s["winner_higher"] / s["total"]
        avg_delta  = s["sum_delta"] / s["total"]
        avg_gap    = s["sum_gap"]    / s["total"]
        # Separation power: how reliably winner > control, weighted by outcome gap
        separation = abs(winner_pct - 0.5) * 2 * abs(avg_gap)
        result.append({
            "feature":          feat,
            "winner_higher_pct": round(winner_pct, 3),
            "avg_delta":         round(avg_delta, 4),
            "avg_outcome_gap":   round(avg_gap, 4),
            "pair_count":        s["total"],
            "separation_power":  round(separation, 4),
        })

    result.sort(key=lambda x: x["separation_power"], reverse=True)
    return result


def same_setup_different_outcome(
    as_of_date: str,
    conn: sqlite3.Connection,
    lookback_days: int = 90,
    min_occurrences: int = 3,
) -> list[dict]:
    """
    Find feature combinations that produced strong gains on some days but
    failed on other days.

    Returns list of dicts:
        {
          setup_signature:   str,    # e.g. "above_20dma=1|sector_conviction=HIGH"
          success_dates:     list[str],
          failure_dates:     list[str],
          success_avg_gap:   float,
          failure_avg_gap:   float,
          discriminator_hint: str,   # feature that was different between S/F cases
        }
    """
    start_date = (date.fromisoformat(as_of_date) - timedelta(days=lookback_days)).isoformat()

    rows = conn.execute("""
        SELECT trade_date, winner_symbol, differing_features,
               outcome_gap_1d, similarity_score
        FROM feature_differentials
        WHERE trade_date BETWEEN ? AND ?
          AND outcome_gap_1d IS NOT NULL
          AND similarity_score >= ?
    """, (start_date, as_of_date, 0.70)).fetchall()   # only high-similarity pairs

    if not rows:
        return []

    # Group rows by "setup signature" (features where winner > control)
    setup_groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        try:
            diff_list = json.loads(r[2] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue

        # Setup signature = top-3 winner-favourable features by abs_delta
        top3 = sorted(
            [e for e in diff_list if e.get("delta", 0) > 0],
            key=lambda e: e.get("abs_delta", 0), reverse=True
        )[:3]
        if len(top3) < 2:
            continue
        sig = "|".join(sorted(e["feature"] for e in top3))
        setup_groups[sig].append({
            "trade_date":  r[0],
            "outcome_gap": r[3],
            "diff":        diff_list,
        })

    result = []
    for sig, cases in setup_groups.items():
        if len(cases) < min_occurrences:
            continue

        successes = [c for c in cases if c["outcome_gap"] > 2.0]
        failures  = [c for c in cases if c["outcome_gap"] < 0.5]

        if not successes or not failures:
            continue

        success_avg = sum(c["outcome_gap"] for c in successes) / len(successes)
        failure_avg = sum(c["outcome_gap"] for c in failures)  / len(failures)

        # Find the feature that differs most between success and failure cases
        discriminator = _find_discriminator(successes, failures)

        result.append({
            "setup_signature":   sig,
            "occurrence_count":  len(cases),
            "success_count":     len(successes),
            "failure_count":     len(failures),
            "success_avg_gap":   round(success_avg, 3),
            "failure_avg_gap":   round(failure_avg, 3),
            "success_dates":     [c["trade_date"] for c in successes[:5]],
            "failure_dates":     [c["trade_date"] for c in failures[:5]],
            "discriminator_hint": discriminator,
        })

    result.sort(key=lambda x: x["occurrence_count"], reverse=True)
    return result


def format_differential_report(
    as_of_date: str,
    conn: sqlite3.Connection,
    lookback_days: int = 30,
) -> str:
    """Return a Markdown report of the differential analysis for the given window."""
    top_diff = aggregate_top_differentiators(as_of_date, conn, lookback_days)
    same_setup = same_setup_different_outcome(as_of_date, conn, lookback_days * 3)

    start_date = (date.fromisoformat(as_of_date) - timedelta(days=lookback_days)).isoformat()

    lines = [
        "# Phase F2.5 — Differential Research Report",
        f"**Window:** {start_date} → {as_of_date}  |  **Lookback:** {lookback_days} days",
        "",
        "> This report isolates the tiny differences that separated winners from",
        "> near-identical stocks that failed to follow through.",
        "",
    ]

    # Section 1: Top differentiators
    lines += ["## Top Separating Features", ""]
    lines += ["*Features that most consistently had higher values in winners than in look-alike failures.*", ""]
    if top_diff:
        lines += ["| Rank | Feature | Winner > Control | Avg Delta | Avg Outcome Gap | Pairs |"]
        lines += ["|---|---|---|---|---|---|"]
        for i, d in enumerate(top_diff[:10], 1):
            lines.append(
                f"| {i} | {d['feature']} | {d['winner_higher_pct']:.0%} | "
                f"{d['avg_delta']:+.3f} | {d['avg_outcome_gap']:+.2f}% | {d['pair_count']} |"
            )
    else:
        lines.append("*Not enough data yet. Pairs accumulate daily.*")
    lines.append("")

    # Section 2: Same setup, different outcome
    lines += ["## Same Setup — Different Outcome", ""]
    lines += [
        "*Feature combinations that sometimes produced big gains and sometimes failed.",
        "The discriminator hint is the feature that varied between the two groups.*",
        "",
    ]
    if same_setup:
        for s in same_setup[:5]:
            lines += [
                f"### Setup: `{s['setup_signature']}`",
                f"- **Occurrences:** {s['occurrence_count']}  "
                f"({s['success_count']} success / {s['failure_count']} failure)",
                f"- **Success avg gap:** +{s['success_avg_gap']:.2f}%",
                f"- **Failure avg gap:** {s['failure_avg_gap']:+.2f}%",
                f"- **Discriminator hint:** `{s['discriminator_hint']}`",
                "",
            ]
    else:
        lines.append("*Insufficient cross-day repetitions yet. Patterns build over 3+ months.*")
    lines.append("")

    lines += [
        "---",
        "> Phase F2.5 — Research output only. No OIOS tables modified. No trades implied.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_pairs(trade_date: str, conn: sqlite3.Connection) -> list[dict]:
    """Load all winner-control pairs for a date, with similarity scores."""
    rows = conn.execute("""
        SELECT
            mrc.control_id,
            mrc.matched_leader_id,
            mld.symbol AS winner_symbol,
            mrc.symbol AS control_symbol,
            -- recompute similarity from fingerprint_hash match (bucket-level only).
            -- Phase F uses the similarity already calculated by control_population.
            -- We approximate it here as 1.0 for exact hash match, 0.7 otherwise.
            CASE WHEN mrc.fingerprint_hash = (
                SELECT fingerprint_hash FROM market_research_controls src2
                WHERE src2.control_id = mrc.control_id LIMIT 1
            ) THEN 0.70 ELSE 0.60 END AS similarity_score
        FROM market_research_controls mrc
        JOIN market_leaders_daily mld ON mrc.matched_leader_id = mld.leader_id
        WHERE mrc.trade_date = ?
    """, (trade_date,)).fetchall()

    # Enhance similarity using feature overlap from market_leader_features if available
    result = []
    for r in rows:
        cid, lid, win_sym, ctrl_sym, sim = r
        # Try to compute a more precise similarity from feature data
        precise_sim = _compute_feature_similarity(lid, ctrl_sym, trade_date, conn)
        result.append({
            "control_id":      cid,
            "matched_leader_id": lid,
            "winner_symbol":   win_sym,
            "control_symbol":  ctrl_sym,
            "similarity_score": precise_sim if precise_sim is not None else sim,
        })
    return result


def _compute_feature_similarity(
    leader_id: str, ctrl_sym: str, trade_date: str, conn: sqlite3.Connection
) -> Optional[float]:
    """
    Compare winner features (from DB) vs control features (computed on-the-fly).
    Returns cosine-style similarity 0.0–1.0, or None if insufficient data.
    """
    winner_feats = dict(conn.execute("""
        SELECT feature_name, feature_value FROM market_leader_features
        WHERE leader_id = ? AND feature_value IS NOT NULL
    """, (leader_id,)).fetchall())

    if not winner_feats:
        return None

    ctrl_feats = _compute_control_features(ctrl_sym, trade_date, conn)
    if not ctrl_feats:
        return None

    # For each shared feature, compute 1 - |normalised_delta|
    shared = [f for f in winner_feats if f in ctrl_feats and ctrl_feats[f] is not None]
    if not shared:
        return None

    matches = 0.0
    for feat in shared:
        wv = winner_feats[feat]
        cv = ctrl_feats[feat]
        if wv is None or cv is None:
            continue
        # Range-normalise: features are on different scales.
        # Use a simple within-magnitude comparison.
        denominator = max(abs(wv), abs(cv), 0.001)
        closeness = 1.0 - min(abs(wv - cv) / denominator, 1.0)
        matches += closeness

    return round(matches / len(shared), 4)


def _load_all_winner_features(
    trade_date: str, conn: sqlite3.Connection
) -> dict[str, dict[str, Optional[float]]]:
    """
    Load all extracted features for every winner on trade_date.
    Returns {symbol: {feature_name: value}}.
    """
    rows = conn.execute("""
        SELECT mld.symbol, mlf.feature_name, mlf.feature_value
        FROM market_leader_features mlf
        JOIN market_leaders_daily mld ON mlf.leader_id = mld.leader_id
        WHERE mld.trade_date = ? AND mld.leader_type = 'WINNER'
    """, (trade_date,)).fetchall()

    result: dict[str, dict[str, Optional[float]]] = defaultdict(dict)
    for sym, feat, val in rows:
        result[sym][feat] = val
    return dict(result)


def _compute_control_features(
    symbol: str, trade_date: str, conn: sqlite3.Connection
) -> dict[str, Optional[float]]:
    """
    Compute the same 12 features for a control stock without storing them.
    Mirrors feature_extractor logic but returns a plain dict.
    """
    # OHLCV history
    history = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE symbol = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 210
    """, (symbol, trade_date)).fetchall()

    close_series = [r[4] for r in history]
    vol_series   = [r[5] for r in history]
    high_series  = [r[2] for r in history]
    low_series   = [r[3] for r in history]
    today_close  = close_series[0] if close_series else None

    feats: dict[str, Optional[float]] = {}

    # Technical
    feats["above_20dma"]  = _above_sma(close_series, today_close, 20)
    feats["above_50dma"]  = _above_sma(close_series, today_close, 50)
    feats["above_200dma"] = _above_sma(close_series, today_close, 200)
    feats["volume_ratio"] = _volume_ratio(vol_series)
    feats["atr_expansion"] = _atr_expansion(high_series, low_series, close_series)
    feats["rs_score"]     = None   # expensive; skip for controls (not used in differential)

    # Sector
    sec_row = conn.execute(
        "SELECT sector, sector_purity_score FROM universe_stocks WHERE symbol = ?", (symbol,)
    ).fetchone()
    sector       = sec_row[0] if sec_row else "UNKNOWN"
    sector_purity = float(sec_row[1]) if sec_row else None

    scd = conn.execute("""
        SELECT sector_conviction_score, theme_phase
        FROM sector_conviction_daily WHERE record_date = ? AND sector = ?
    """, (trade_date, sector)).fetchone()

    _THEME_SCORE = {
        "EMERGENCE": 1.0, "ACCELERATION": 2.0, "CONSENSUS": 3.0,
        "CROWDING": 4.0, "EXHAUSTION": 5.0,
    }
    feats["theme_phase_score"]  = _THEME_SCORE.get(scd[1], None) if scd and scd[1] else None
    feats["sector_conviction"]  = float(scd[0]) if scd and scd[0] is not None else None
    feats["sector_purity"]      = sector_purity

    # OIOS
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM signal_births
            WHERE symbol = ? AND current_state IN ('ACTIVE','WATCHING')
              AND detected_at <= ?
        """, (symbol, trade_date)).fetchone()
        feats["active_archetypes"] = float(row[0]) if row else None
    except Exception:
        feats["active_archetypes"] = None

    try:
        row = conn.execute("""
            SELECT cs.cause_score FROM cause_scores cs
            JOIN opportunities o ON cs.opportunity_id = o.opportunity_id
            WHERE o.symbol = ? AND cs.score_date <= ?
              AND o.current_state IN ('ACTIVE','WATCHING')
            ORDER BY cs.score_date DESC LIMIT 1
        """, (symbol, trade_date)).fetchone()
        feats["cause_score"] = float(row[0]) if row and row[0] is not None else None
    except Exception:
        feats["cause_score"] = None

    # Sector rank
    try:
        rank_rows = conn.execute("""
            SELECT sector FROM sector_conviction_daily
            WHERE record_date = ? AND sector_conviction_score IS NOT NULL
            ORDER BY sector_conviction_score DESC
        """, (trade_date,)).fetchall()
        feats["sector_rank"] = None
        for i, r in enumerate(rank_rows, 1):
            if r[0] == sector:
                feats["sector_rank"] = float(i)
                break
    except Exception:
        feats["sector_rank"] = None

    return feats


def _difference_matrix(
    winner_feats: dict[str, Optional[float]],
    control_feats: dict[str, Optional[float]],
) -> list[dict]:
    """
    Build sorted difference matrix.
    Returns list of {feature, winner_val, control_val, delta, abs_delta},
    sorted by abs_delta descending.
    """
    diffs = []
    for feat in COMPARABLE_FEATURES:
        wv = winner_feats.get(feat)
        cv = control_feats.get(feat)
        if wv is None or cv is None:
            continue
        delta = wv - cv
        diffs.append({
            "feature":    feat,
            "winner_val": round(wv, 4),
            "control_val": round(cv, 4),
            "delta":      round(delta, 4),
            "abs_delta":  round(abs(delta), 4),
        })
    diffs.sort(key=lambda x: x["abs_delta"], reverse=True)
    return diffs


def _load_leader_outcomes(trade_date: str, conn: sqlite3.Connection) -> dict[str, dict]:
    """
    Returns {leader_id: {return_1d, return_3d, return_5d, return_20d}}
    for all winners on trade_date.
    """
    rows = conn.execute("""
        SELECT mld.leader_id, mlo.return_1d, mlo.return_3d, mlo.return_5d, mlo.return_20d
        FROM market_leaders_daily mld
        LEFT JOIN market_leader_outcomes mlo ON mld.leader_id = mlo.leader_id
        WHERE mld.trade_date = ? AND mld.leader_type = 'WINNER'
    """, (trade_date,)).fetchall()
    return {
        r[0]: {"r1d": r[1], "r3d": r[2], "r5d": r[3], "r20d": r[4]}
        for r in rows
    }


def _load_control_outcomes(control_id: str, conn: sqlite3.Connection) -> dict:
    row = conn.execute("""
        SELECT return_1d, return_3d, return_5d, return_20d
        FROM market_research_controls WHERE control_id = ?
    """, (control_id,)).fetchone()
    if not row:
        return {}
    return {"r1d": row[0], "r3d": row[1], "r5d": row[2], "r20d": row[3]}


def _compute_gaps(
    winner_oc: dict, control_oc: dict
) -> dict[str, Optional[float]]:
    def gap(w, c):
        if w is None or c is None:
            return None
        return round(w - c, 4)
    return {
        "g1d":  gap(winner_oc.get("r1d"),  control_oc.get("r1d")),
        "g3d":  gap(winner_oc.get("r3d"),  control_oc.get("r3d")),
        "g5d":  gap(winner_oc.get("r5d"),  control_oc.get("r5d")),
        "g20d": gap(winner_oc.get("r20d"), control_oc.get("r20d")),
    }


def _find_discriminator(
    successes: list[dict], failures: list[dict]
) -> str:
    """
    Find the feature that had the largest average difference between
    success cases and failure cases.
    """
    sums_s: dict[str, float] = defaultdict(float)
    cnts_s: dict[str, int]   = defaultdict(int)
    sums_f: dict[str, float] = defaultdict(float)
    cnts_f: dict[str, int]   = defaultdict(int)

    for group, sums, cnts in [(successes, sums_s, cnts_s), (failures, sums_f, cnts_f)]:
        for case in group:
            for entry in case.get("diff", []):
                feat = entry.get("feature", "")
                delta = entry.get("delta")
                if feat and delta is not None:
                    sums[feat] += delta
                    cnts[feat] += 1

    best_feat = "UNKNOWN"
    best_gap  = 0.0
    for feat in set(cnts_s) | set(cnts_f):
        avg_s = sums_s[feat] / cnts_s[feat] if cnts_s[feat] else 0.0
        avg_f = sums_f[feat] / cnts_f[feat] if cnts_f[feat] else 0.0
        g = abs(avg_s - avg_f)
        if g > best_gap:
            best_gap  = g
            best_feat = feat

    return best_feat


# ── Reusable math helpers (no external deps) ──────────────────────────────────

def _above_sma(series: list[float], today: Optional[float], period: int) -> Optional[float]:
    if today is None or len(series) < period + 1:
        return None
    sma = sum(series[1:period + 1]) / period
    return 1.0 if today > sma else 0.0


def _volume_ratio(vol_series: list[float]) -> Optional[float]:
    if len(vol_series) < 2:
        return None
    prev = [v for v in vol_series[1:21] if v and v > 0]
    if not prev:
        return None
    return round(vol_series[0] / (sum(prev) / len(prev)), 3)


def _atr_expansion(
    highs: list[float], lows: list[float], closes: list[float]
) -> Optional[float]:
    if len(highs) < 22:
        return None
    def _atr(h, l, c_prev, n):
        trs = [max(h[i]-l[i], abs(h[i]-c_prev[i]), abs(l[i]-c_prev[i])) for i in range(n)]
        return sum(trs) / n if trs else None
    today_atr = _atr(highs, lows, closes[1:], 1)
    avg_atr   = _atr(highs[1:], lows[1:], closes[2:], 20)
    if today_atr is None or avg_atr is None or avg_atr == 0:
        return None
    return round(today_atr / avg_atr, 3)
