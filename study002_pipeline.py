"""
Study 002 — One-Year Historical Market Learning Pipeline
=========================================================
Transforms Study 002 replay evidence (data/study002_replay.db) into
accumulated market knowledge using all enabled pipeline stages.

Stages:
  0  Session Record Generation  — per-day: regime, signals, opps, sectors
  1  Regime Analysis            — classify sessions; per-regime statistics
  2  Signal & Opportunity Analysis
  3  Sector Analysis
  4  Feature Database Enrichment — OHLCV → labelled feature vectors
  5  Edge Discovery Pipeline (EDE) — PatternMiner → EdgeRankingEngine
  6  MetaModel Status
  7  Knowledge Store Verification

Does NOT modify any trading algorithm, AI model, or production parameter.
Does NOT create new commits.
Does NOT push to any branch.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from utils import get_logger
log = get_logger("study002")

# ── Paths ────────────────────────────────────────────────────────────────────
STUDY_DB   = os.path.join(ROOT, "data", "study002_replay.db")
RESULTS    = os.path.join(ROOT, "data", "study002_results.json")
FEAT_DB    = os.path.join(ROOT, "data", "ede_feature_db.json")
EDGES_DB   = os.path.join(ROOT, "data", "discovered_edges.json")
STRATS_DB  = os.path.join(ROOT, "data", "evolved_strategies.json")
PERF_DB    = os.path.join(ROOT, "data", "strategy_performance.json")
ML_DS      = os.path.join(ROOT, "data", "ml_performance_dataset.json")
NIFTY_SYM  = "^NSEI"

# Regime detection constants (must match historical_replay.py)
REGIME_TREND_THRESHOLD_PCT = 2.0
REGIME_SMA_BAND            = 0.02

# Positive label threshold (next-day return ≥ 0.8% = positive)
POSITIVE_RETURN_THRESHOLD = 0.008

# Feature source tag
SOURCE_TAG = "S002_OHLCV"

# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _banner(msg: str) -> None:
    log.info("═" * 68)
    log.info("  %s", msg)
    log.info("═" * 68)


def _open_study_db() -> sqlite3.Connection:
    if not Path(STUDY_DB).exists():
        raise FileNotFoundError(
            f"Study 002 replay DB not found: {STUDY_DB}\n"
            "Run historical_replay.py first:\n"
            "  python historical_replay.py --start 2025-08-01 --end 2026-07-31 "
            "--db data/study002_replay.db"
        )
    conn = sqlite3.connect(STUDY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot_knowledge_stores() -> dict:
    snap: dict = {}

    with open(FEAT_DB) as f:
        feat = json.load(f)
    snap["feat_total"]   = len(feat)
    snap["feat_labeled"] = sum(1 for r in feat if r.get("forward_return", 0.0) != 0.0)
    snap["feat_symbols"] = len(set(r.get("symbol", "") for r in feat))

    with open(EDGES_DB) as f:
        edges = json.load(f)
    snap["edges_total"] = len(edges)
    by_st: dict[str, int] = {}
    for v in edges.values():
        st = v.get("status", "?")
        by_st[st] = by_st.get(st, 0) + 1
    snap["edges_by_status"] = by_st

    with open(STRATS_DB) as f:
        snap["strats_total"] = len(json.load(f))

    with open(PERF_DB) as f:
        snap["perf_tracked"] = len(json.load(f))

    snap["ml_records"] = 0
    if os.path.exists(ML_DS):
        with open(ML_DS) as f:
            snap["ml_records"] = len(json.load(f))

    return snap


# ═══════════════════════════════════════════════════════════════════════════
# REGIME DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _build_regime_map(conn: sqlite3.Connection) -> dict[str, str]:
    """
    Compute regime for every trading day using NIFTY50 OHLCV.
    Returns {date_str: regime_str} using the same algorithm as
    historical_replay._detect_regime().

    Regimes: TRENDING_UP | TRENDING_DOWN | SIDEWAYS
    """
    rows = conn.execute("""
        SELECT trade_date, close FROM ohlcv_daily
        WHERE symbol = ?
        ORDER BY trade_date ASC
    """, (NIFTY_SYM,)).fetchall()

    if not rows:
        log.warning("[Regime] No NIFTY50 data found — defaulting all to SIDEWAYS")
        # Fall back: assign SIDEWAYS to all trading calendar dates
        cal_rows = conn.execute("""
            SELECT calendar_date FROM trading_calendar
            WHERE is_trading_day = 1 ORDER BY calendar_date
        """).fetchall()
        return {r[0]: "SIDEWAYS" for r in cal_rows}

    closes = [(r["trade_date"], r["close"]) for r in rows]
    regime_map: dict[str, str] = {}

    for i, (date_str, close) in enumerate(closes):
        if i < 25:
            regime_map[date_str] = "SIDEWAYS"
            continue

        window = min(200, i + 1)
        sma = sum(c for _, c in closes[max(0, i - window + 1):i + 1]) / window

        change_20d = 0.0
        if i >= 20:
            change_20d = (close / closes[i - 20][1] - 1.0) * 100.0

        above_sma = close > sma * (1 + REGIME_SMA_BAND)
        below_sma = close < sma * (1 - REGIME_SMA_BAND)

        if above_sma and change_20d > REGIME_TREND_THRESHOLD_PCT:
            regime_map[date_str] = "TRENDING_UP"
        elif below_sma and change_20d < -REGIME_TREND_THRESHOLD_PCT:
            regime_map[date_str] = "TRENDING_DOWN"
        else:
            regime_map[date_str] = "SIDEWAYS"

    return regime_map


def _regime_features(regime: str) -> dict:
    if regime == "TRENDING_UP":
        return {"regime_score": 0.8, "regime_bull": 1.0, "regime_range": 0.0,
                "regime_bear": 0.0, "regime_volatile": 0.0,
                "vix": 0.25, "vix_low": 1.0, "vix_high": 0.0}
    if regime == "TRENDING_DOWN":
        return {"regime_score": 0.2, "regime_bull": 0.0, "regime_range": 0.0,
                "regime_bear": 1.0, "regime_volatile": 0.0,
                "vix": 0.65, "vix_low": 0.0, "vix_high": 1.0}
    if regime == "VOLATILE":
        return {"regime_score": 0.5, "regime_bull": 0.0, "regime_range": 0.0,
                "regime_bear": 0.0, "regime_volatile": 1.0,
                "vix": 0.75, "vix_low": 0.0, "vix_high": 1.0}
    # SIDEWAYS / default
    return {"regime_score": 0.5, "regime_bull": 0.0, "regime_range": 1.0,
            "regime_bear": 0.0, "regime_volatile": 0.0,
            "vix": 0.375, "vix_low": 1.0, "vix_high": 0.0}


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 0 — SESSION RECORDS
# ═══════════════════════════════════════════════════════════════════════════

def stage0_session_records(conn: sqlite3.Connection, regime_map: dict[str, str]) -> list[dict]:
    """
    Build one record per trading session covering all required metrics.
    """
    _banner("STAGE 0 — Session Record Generation")

    trading_days = [
        r[0] for r in conn.execute("""
            SELECT calendar_date FROM trading_calendar
            WHERE is_trading_day = 1
            ORDER BY calendar_date
        """).fetchall()
    ]
    log.info("[Stage0] %d trading sessions to process", len(trading_days))

    # Pre-load signals and opportunities per day
    sig_by_day: dict[str, list] = defaultdict(list)
    for r in conn.execute("SELECT detected_at, archetype_id, regime_at_birth FROM signal_births").fetchall():
        sig_by_day[r["detected_at"]].append(dict(r))

    # Opportunities: use DATE(created_at) as birth date proxy
    opp_by_day: dict[str, list] = defaultdict(list)
    for r in conn.execute(
        "SELECT DATE(created_at) AS birth_date, current_state, direction, conviction_score FROM opportunities"
    ).fetchall():
        if r["birth_date"]:
            opp_by_day[r["birth_date"]].append(dict(r))

    # Sector conviction per day
    sc_by_day: dict[str, list] = defaultdict(list)
    for r in conn.execute("""
        SELECT record_date, sector, sector_conviction_score, data_quality
        FROM sector_conviction_daily
    """).fetchall():
        sc_by_day[r["record_date"]].append(dict(r))

    # NIFTY50 price per day
    nifty_by_day: dict[str, float] = {}
    for r in conn.execute(
        "SELECT trade_date, close FROM ohlcv_daily WHERE symbol = ? ORDER BY trade_date",
        (NIFTY_SYM,)
    ).fetchall():
        nifty_by_day[r["trade_date"]] = r["close"]

    records = []
    for day in trading_days:
        regime = regime_map.get(day, "SIDEWAYS")
        signals = sig_by_day.get(day, [])
        opps    = opp_by_day.get(day, [])
        scs     = sc_by_day.get(day, [])
        nifty   = nifty_by_day.get(day)

        # Sector leadership: top conviction sector on this day
        full_scs = [s for s in scs if s.get("data_quality") == "FULL"]
        top_sector = ""
        top_conviction = 0.0
        if full_scs:
            top = max(full_scs, key=lambda s: s.get("sector_conviction_score") or 0.0)
            top_sector    = top["sector"]
            top_conviction = top.get("sector_conviction_score") or 0.0

        avg_breadth = (
            sum(s.get("sector_conviction_score") or 0.0 for s in full_scs) / len(full_scs)
            if full_scs else 0.0
        )

        arch_counts: dict[str, int] = {}
        for sig in signals:
            arch_id = sig.get("archetype_id", "UNKNOWN")
            arch_counts[arch_id] = arch_counts.get(arch_id, 0) + 1

        rec = {
            "date":           day,
            "regime":         regime,
            "nifty_close":    round(nifty, 2) if nifty else None,
            "signals":        len(signals),
            "signal_by_arch": arch_counts,
            "new_opps":       len(opps),
            "opp_states":     {st: sum(1 for o in opps if o["current_state"] == st)
                               for st in ["DISCOVERED", "ACTIVE", "WATCHING", "INVALID"]},
            "top_sector":     top_sector,
            "top_conviction": round(top_conviction, 4),
            "avg_breadth":    round(avg_breadth, 4),
            "sectors_full":   len(full_scs),
        }
        records.append(rec)

    log.info("[Stage0] Session records built: %d", len(records))
    return records


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1 — REGIME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def stage1_regime_analysis(session_records: list[dict]) -> dict:
    """
    Group sessions by regime; compute per-regime statistics.
    Do NOT merge regime statistics.
    """
    _banner("STAGE 1 — Regime Analysis")

    regimes = ["TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS", "VOLATILE"]
    analysis: dict[str, dict] = {r: {
        "sessions": 0, "signals": 0, "new_opps": 0,
        "avg_breadth": 0.0, "signal_days": 0, "top_sector_counts": {},
    } for r in regimes}

    for rec in session_records:
        regime = rec["regime"]
        if regime not in analysis:
            analysis[regime] = {
                "sessions": 0, "signals": 0, "new_opps": 0,
                "avg_breadth": 0.0, "signal_days": 0, "top_sector_counts": {},
            }
        a = analysis[regime]
        a["sessions"]  += 1
        a["signals"]   += rec["signals"]
        a["new_opps"]  += rec["new_opps"]
        a["avg_breadth"] = (
            (a["avg_breadth"] * (a["sessions"] - 1) + rec["avg_breadth"]) / a["sessions"]
        )
        if rec["signals"] > 0:
            a["signal_days"] += 1
        if rec["top_sector"]:
            sec = rec["top_sector"]
            a["top_sector_counts"][sec] = a["top_sector_counts"].get(sec, 0) + 1

    for regime, a in analysis.items():
        if a["sessions"] > 0:
            a["signal_rate"] = round(a["signal_days"] / a["sessions"], 4)
            a["signals_per_session"] = round(a["signals"] / a["sessions"], 4)
            a["avg_breadth"] = round(a["avg_breadth"], 4)
        else:
            a["signal_rate"] = 0.0
            a["signals_per_session"] = 0.0
        # Find dominant sector per regime
        tsc = a["top_sector_counts"]
        a["dominant_sector"] = max(tsc, key=tsc.get) if tsc else "—"

    log.info("[Stage1] Regime breakdown:")
    for regime, a in analysis.items():
        if a["sessions"] > 0:
            log.info("  %-15s  sessions=%3d  signals=%4d  signal_rate=%.2f  dominant=%s",
                     regime, a["sessions"], a["signals"],
                     a.get("signal_rate", 0.0), a.get("dominant_sector", "—"))

    return analysis


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2 — SIGNAL AND OPPORTUNITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def stage2_signal_opportunity_analysis(conn: sqlite3.Connection,
                                        regime_map: dict[str, str]) -> dict:
    """
    Full signal and opportunity breakdown by archetype, direction, regime,
    and opportunity lifecycle state.
    """
    _banner("STAGE 2 — Signal and Opportunity Analysis")

    # Signals
    sig_rows = conn.execute("""
        SELECT detected_at, archetype_id, regime_at_birth
        FROM signal_births
    """).fetchall()
    total_signals = len(sig_rows)

    by_arch: dict[str, int] = {}
    by_regime_sig: dict[str, int] = {}
    for r in sig_rows:
        arch = r["archetype_id"] or "UNKNOWN"
        by_arch[arch] = by_arch.get(arch, 0) + 1
        reg  = r["regime_at_birth"] or regime_map.get(r["detected_at"], "SIDEWAYS")
        by_regime_sig[reg] = by_regime_sig.get(reg, 0) + 1

    # Opportunities
    opp_rows = conn.execute("""
        SELECT DATE(created_at) AS birth_date, current_state, direction,
               conviction_score, invalidation_reason, regime_at_birth
        FROM opportunities
    """).fetchall()
    total_opps = len(opp_rows)

    by_state: dict[str, int] = {}
    by_dir:   dict[str, int] = {}
    by_regime_opp: dict[str, int] = {}
    closed_opps = 0

    for r in opp_rows:
        st = r["current_state"] or "UNKNOWN"
        by_state[st] = by_state.get(st, 0) + 1
        dr = r["direction"] or "UNKNOWN"
        by_dir[dr] = by_dir.get(dr, 0) + 1
        # Prefer regime_at_birth from DB over regime_map lookup
        reg = r["regime_at_birth"] or regime_map.get(r["birth_date"] or "", "SIDEWAYS")
        by_regime_opp[reg] = by_regime_opp.get(reg, 0) + 1
        if st in ("COMPLETED", "INVALIDATED"):
            closed_opps += 1

    log.info("[Stage2] signals=%d  opportunities=%d  closed=%d",
             total_signals, total_opps, closed_opps)

    return {
        "total_signals":          total_signals,
        "by_archetype":           dict(sorted(by_arch.items(), key=lambda x: -x[1])),
        "by_regime_signals":      by_regime_sig,
        "total_opportunities":    total_opps,
        "by_state":               by_state,
        "by_direction":           by_dir,
        "by_regime_opportunities": by_regime_opp,
        "closed_opportunities":   closed_opps,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3 — SECTOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def stage3_sector_analysis(conn: sqlite3.Connection) -> dict:
    """
    Sector conviction statistics: peak conviction, most consistent sectors,
    sector signal contribution.
    """
    _banner("STAGE 3 — Sector Analysis")

    sc_rows = conn.execute("""
        SELECT sector, record_date, sector_conviction_score, data_quality
        FROM sector_conviction_daily
        WHERE data_quality = 'FULL'
        ORDER BY sector, record_date
    """).fetchall()

    # Per-sector: count, avg, max conviction
    by_sector: dict[str, dict] = {}
    peak_conviction = {"score": 0.0, "sector": "", "date": ""}

    for r in sc_rows:
        sec   = r["sector"]
        score = r["sector_conviction_score"] or 0.0
        date  = r["record_date"]

        if sec not in by_sector:
            by_sector[sec] = {"count": 0, "total": 0.0, "max": 0.0, "max_date": ""}
        by_sector[sec]["count"]  += 1
        by_sector[sec]["total"]  += score
        if score > by_sector[sec]["max"]:
            by_sector[sec]["max"]      = round(score, 4)
            by_sector[sec]["max_date"] = date
        if score > peak_conviction["score"]:
            peak_conviction = {"score": round(score, 4), "sector": sec, "date": date}

    summary: dict[str, dict] = {}
    for sec, s in by_sector.items():
        n = s["count"]
        summary[sec] = {
            "full_rows":      n,
            "avg_conviction": round(s["total"] / n, 4) if n > 0 else 0.0,
            "peak_conviction": s["max"],
            "peak_date":       s["max_date"],
        }

    # Sector → signal count
    sig_sector_rows = conn.execute("""
        SELECT sb.archetype_id, u.sector, COUNT(*) AS n
        FROM signal_births sb
        JOIN universe_stocks u ON sb.symbol = u.symbol
        GROUP BY u.sector
        ORDER BY n DESC
    """).fetchall()
    sig_by_sector: dict[str, int] = {r["sector"]: r["n"] for r in sig_sector_rows}

    # Total FULL rows (coverage check)
    total_full = len(sc_rows)
    log.info("[Stage3] Sectors tracked: %d  |  peak conviction: %.3f (%s on %s)  |  total FULL rows: %d",
             len(by_sector), peak_conviction["score"],
             peak_conviction["sector"], peak_conviction["date"], total_full)

    return {
        "total_full_conviction_rows": total_full,
        "peak_conviction":            peak_conviction,
        "by_sector":                  summary,
        "signals_by_sector":          sig_by_sector,
        "most_active_signal_sector":  max(sig_by_sector, key=sig_by_sector.get)
                                       if sig_by_sector else "—",
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4 — FEATURE DATABASE ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════

def stage4_enrich_feature_db(conn: sqlite3.Connection,
                              regime_map: dict[str, str]) -> dict:
    """
    Extract real OHLCV feature vectors from study002_replay.db with proper
    per-date regime encoding, compute forward_return labels, append to
    ede_feature_db.json.

    Regime encoding replaces the hardcoded SIDEWAYS from RE001A.
    """
    _banner("STAGE 4 — Feature Database Enrichment")

    # Idempotency guard: skip if S002 features already present
    with open(FEAT_DB) as f:
        existing_check = json.load(f)
    already_enriched = sum(1 for r in existing_check if r.get("source") == SOURCE_TAG)
    if already_enriched > 0:
        log.info("[Stage4] SKIP — %d S002 feature rows already present in DB",
                 already_enriched)
        before = len(existing_check)
        labeled_before = sum(1 for r in existing_check if r.get("forward_return", 0.0) != 0.0)
        pos = sum(1 for r in existing_check
                  if r.get("source") == SOURCE_TAG
                  and r.get("forward_return", 0.0) >= POSITIVE_RETURN_THRESHOLD)
        syms = len(set(r.get("symbol", "") for r in existing_check
                       if r.get("source") == SOURCE_TAG))
        dates = len(set(r.get("ts", "") for r in existing_check
                        if r.get("source") == SOURCE_TAG))
        reg_dist: dict[str, int] = {}
        for r in existing_check:
            if r.get("source") == SOURCE_TAG:
                reg = r.get("regime", "SIDEWAYS")
                reg_dist[reg] = reg_dist.get(reg, 0) + 1
        return {
            "feat_before":      before - already_enriched,
            "feat_after":       before,
            "feat_added":       already_enriched,
            "labeled_before":   labeled_before - already_enriched,
            "labeled_after":    labeled_before,
            "positive_labels":  pos,
            "negative_labels":  already_enriched - pos,
            "positive_rate":    round(pos / already_enriched, 4) if already_enriched else 0,
            "symbols_enriched": syms,
            "dates_covered":    dates,
            "regime_distribution": reg_dist,
            "skipped_reason":   "already_enriched",
        }

    # Load all OHLCV
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, trade_date, open, high, low, close, volume "
        "FROM ohlcv_daily ORDER BY symbol, trade_date"
    )
    rows = cur.fetchall()
    log.info("[Stage4] Loaded %d OHLCV rows", len(rows))

    # Build per-symbol candle series
    sym_data: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["symbol"] == NIFTY_SYM:
            continue  # skip index — not a tradeable stock
        sym_data[r["symbol"]].append({
            "d": r["trade_date"], "o": r["open"],   "h": r["high"],
            "l": r["low"],        "c": r["close"],   "v": r["volume"],
        })

    # Sector conviction map: date → sector → (score, part5d)
    sc_map: dict[str, dict[str, tuple]] = defaultdict(dict)
    for r in cur.execute("""
        SELECT record_date, sector, sector_conviction_score, participation_rate_5d
        FROM sector_conviction_daily WHERE data_quality='FULL'
    """).fetchall():
        sc_map[r["record_date"]][r["sector"]] = (
            r["sector_conviction_score"] or 0.0,
            r["participation_rate_5d"] or 0.0,
        )

    # Symbol → sector
    sym_sector: dict[str, str] = {
        r["symbol"]: r["primary_sector"]
        for r in cur.execute(
            "SELECT symbol, primary_sector FROM stock_sector_map"
        ).fetchall()
    }

    new_rows: list[dict] = []
    skipped_no_next    = 0
    skipped_no_history = 0
    regime_counts: dict[str, int] = {}

    for symbol, candles in sym_data.items():
        if len(candles) < 6:
            skipped_no_history += 1
            continue
        sector = sym_sector.get(symbol, "UNKNOWN")

        for i in range(5, len(candles)):
            today = candles[i]
            prev1 = candles[i - 1]
            prev5 = candles[i - 5]

            if i + 1 >= len(candles):
                skipped_no_next += 1
                continue

            nxt = candles[i + 1]
            if today["c"] <= 0 or nxt["c"] <= 0:
                continue

            # ── Price features ─────────────────────────────────────────────
            mom_1d = (today["c"] - prev1["c"]) / prev1["c"] if prev1["c"] > 0 else 0.0
            mom_5d = (today["c"] - prev5["c"]) / prev5["c"] if prev5["c"] > 0 else 0.0

            intra_range = (today["h"] - today["l"]) / today["c"] if today["c"] > 0 else 0.0
            close_pos   = ((today["c"] - today["l"]) / (today["h"] - today["l"])
                           if (today["h"] - today["l"]) > 0 else 0.5)

            vols_5  = [candles[i - k]["v"] for k in range(1, 6) if candles[i - k]["v"]]
            avg_vol  = sum(vols_5) / len(vols_5) if vols_5 else 1.0
            vol_ratio = min(today["v"] / avg_vol, 5.0) if avg_vol > 0 else 1.0

            cons_up = 0
            for k in range(1, 5):
                if candles[i - k]["c"] < candles[i - k - 1]["c"]:
                    break
                cons_up += 1

            # ── Sector conviction features ──────────────────────────────────
            sc = sc_map.get(today["d"], {}).get(sector, (0.0, 0.0))
            sect_conviction = sc[0]
            sect_part5d     = sc[1]

            day_sc = sc_map.get(today["d"], {})
            avg_conviction = (sum(v[0] for v in day_sc.values()) / len(day_sc)
                              if day_sc else 0.0)

            # ── Regime features (real per-date, not hardcoded) ──────────────
            regime = regime_map.get(today["d"], "SIDEWAYS")
            rfeat  = _regime_features(regime)
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

            # ── PCR proxy: use avg_conviction as a breadth signal ───────────
            pcr_neutral = 1.0 if 0.4 <= avg_conviction <= 0.7 else 0.0
            pcr_bullish = 1.0 if avg_conviction > 0.7 else 0.0
            pcr_bearish = 1.0 if avg_conviction < 0.4 else 0.0

            # ── Forward return label ────────────────────────────────────────
            forward_return = (nxt["c"] - today["c"]) / today["c"]

            feat_vec = {
                "mom_1d":             round(mom_1d, 6),
                "mom_5d":             round(mom_5d, 6),
                "intra_range":        round(intra_range, 6),
                "close_pos":          round(close_pos, 4),
                "vol_ratio":          round(vol_ratio, 4),
                "cons_up_days":       float(cons_up),
                "sect_conviction":    round(sect_conviction, 4),
                "sect_part5d":        round(sect_part5d, 4),
                "avg_conviction":     round(avg_conviction, 4),
                "regime_score":       rfeat["regime_score"],
                "regime_bull":        rfeat["regime_bull"],
                "regime_range":       rfeat["regime_range"],
                "regime_bear":        rfeat["regime_bear"],
                "regime_volatile":    rfeat["regime_volatile"],
                "vix":                rfeat["vix"],
                "vix_low":            rfeat["vix_low"],
                "vix_high":           rfeat["vix_high"],
                "breadth":            round(avg_conviction, 4),
                "breadth_strong":     1.0 if avg_conviction > 0.6 else 0.0,
                "breadth_weak":       1.0 if avg_conviction < 0.4 else 0.0,
                "pcr":                round(avg_conviction, 4),
                "pcr_bullish":        pcr_bullish,
                "pcr_bearish":        pcr_bearish,
                "pcr_neutral":        pcr_neutral,
                "global_bias":        rfeat["regime_bull"] * 0.7 + rfeat["regime_score"] * 0.3,
                "sector_flow_count":  1.2,
                "event_count":        0.0,
            }

            new_rows.append({
                "features":       feat_vec,
                "forward_return": round(forward_return, 6),
                "symbol":         symbol,
                "ts":             today["d"],
                "source":         SOURCE_TAG,
                "sector":         sector,
                "regime":         regime,
            })

    log.info("[Stage4] Computed %d feature rows "
             "(skip no_next=%d, no_history=%d)",
             len(new_rows), skipped_no_next, skipped_no_history)
    log.info("[Stage4] Regime distribution in features: %s", regime_counts)

    # Load existing and append
    with open(FEAT_DB) as f:
        existing = json.load(f)
    before = len(existing)
    labeled_before = sum(1 for r in existing if r.get("forward_return", 0.0) != 0.0)

    enriched = existing + new_rows
    with open(FEAT_DB, "w") as f:
        json.dump(enriched, f)
    after = len(enriched)

    labeled_after = sum(1 for r in enriched if r.get("forward_return", 0.0) != 0.0)
    pos_labels = sum(1 for r in new_rows if r["forward_return"] >= POSITIVE_RETURN_THRESHOLD)
    neg_labels = len(new_rows) - pos_labels

    result = {
        "feat_before":      before,
        "feat_after":       after,
        "feat_added":       after - before,
        "labeled_before":   labeled_before,
        "labeled_after":    labeled_after,
        "positive_labels":  pos_labels,
        "negative_labels":  neg_labels,
        "positive_rate":    round(pos_labels / len(new_rows), 4) if new_rows else 0,
        "symbols_enriched": len(set(r["symbol"] for r in new_rows)),
        "dates_covered":    len(set(r["ts"] for r in new_rows)),
        "regime_distribution": regime_counts,
    }
    log.info("[Stage4] Feature DB: %d → %d (+%d)  positive_rate=%.1f%%",
             before, after, after - before, 100 * result["positive_rate"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5 — EDGE DISCOVERY PIPELINE (EDE)
# ═══════════════════════════════════════════════════════════════════════════

def _build_final_snapshot(conn: sqlite3.Connection,
                           regime_map: dict[str, str]) -> object:
    """
    Build a MarketSnapshot reflecting the terminal state of Study 002.
    Uses the last available trading session data.
    """
    from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel, SectorFlow

    # Last trading day
    last_day_row = conn.execute("""
        SELECT calendar_date FROM trading_calendar
        WHERE is_trading_day = 1 ORDER BY calendar_date DESC LIMIT 1
    """).fetchone()
    last_day = last_day_row[0] if last_day_row else "2026-07-31"
    final_regime = regime_map.get(last_day, "SIDEWAYS")

    # Sector conviction on last day (or nearest prior)
    sc_rows = conn.execute("""
        SELECT sector, sector_conviction_score
        FROM sector_conviction_daily
        WHERE record_date = (
            SELECT MAX(record_date) FROM sector_conviction_daily
            WHERE data_quality = 'FULL'
        )
        ORDER BY sector_conviction_score DESC
    """).fetchall()

    sector_flows = []
    for rank, r in enumerate(sc_rows, 1):
        score = r["sector_conviction_score"] or 0.0
        sector_flows.append(SectorFlow(r["sector"], score, rank, []))

    if not sector_flows:
        sector_flows = [SectorFlow("IT", 0.5, 1, [])]

    # Map replay regime strings to RegimeLabel enum
    regime_label_map = {
        "TRENDING_UP":   RegimeLabel.BULL_TREND,
        "TRENDING_DOWN": RegimeLabel.BEAR_MARKET,
        "SIDEWAYS":      RegimeLabel.RANGE_MARKET,
        "VOLATILE":      RegimeLabel.VOLATILE,
    }
    regime_label = regime_label_map.get(final_regime, RegimeLabel.RANGE_MARKET)

    avg_conviction = (
        sum(sf.flow_score for sf in sector_flows) / len(sector_flows)
        if sector_flows else 0.5
    )

    vol_level = VolatilityLevel.HIGH if final_regime == "VOLATILE" else VolatilityLevel.LOW

    return MarketSnapshot(
        timestamp             = datetime.fromisoformat(last_day + "T15:30:00"),
        indices               = {},
        regime                = regime_label,
        volatility            = vol_level,
        vix                   = 20.0 if final_regime in ("VOLATILE", "TRENDING_DOWN") else 14.0,
        fii_dii               = None,
        sector_flows          = sector_flows,
        sector_leaders        = [sf.sector_name for sf in sector_flows[:4]],
        events_today          = [],
        market_breadth        = round(avg_conviction, 4),
        pcr                   = 0.90,
        global_bias           = "bullish" if final_regime == "TRENDING_UP" else "neutral",
        global_sentiment_score = 0.2 if final_regime == "TRENDING_UP" else 0.0,
    ), last_day, final_regime


def stage5_ede(conn: sqlite3.Connection, regime_map: dict[str, str]) -> dict:
    """
    Run EdgeDiscoveryEngine cycle using a MarketSnapshot reflecting
    the final state of Study 002.
    """
    _banner("STAGE 5 — Edge Discovery Pipeline")

    from edge_discovery.edge_discovery_engine import EdgeDiscoveryEngine
    from edge_discovery.pattern_miner import load_feature_db

    snapshot, last_day, final_regime = _build_final_snapshot(conn, regime_map)
    log.info("[Stage5] Using snapshot: date=%s  regime=%s", last_day, final_regime)
    log.info("[Stage5] MarketSnapshot: %s", snapshot.summary())

    with open(EDGES_DB) as f:
        edges_before = json.load(f)
    with open(STRATS_DB) as f:
        strats_before = json.load(f)

    ede = EdgeDiscoveryEngine()
    db  = load_feature_db()
    log.info("[Stage5] Feature DB: %d rows loaded for EDE", len(db))

    report = ede.run_discovery_cycle(snapshot, publish_event=False)
    log.info("[Stage5] EDE report:\n%s", report)

    with open(EDGES_DB) as f:
        edges_after = json.load(f)
    with open(STRATS_DB) as f:
        strats_after = json.load(f)

    new_edges     = [k for k in edges_after if k not in edges_before]
    updated_edges = [k for k in edges_after if k in edges_before
                     and edges_after[k].get("status") != edges_before[k].get("status")]
    removed_edges = [k for k in edges_before if k not in edges_after]
    new_strats    = [k for k in strats_after  if k not in strats_before]

    status_after = {
        st: sum(1 for v in edges_after.values() if v.get("status") == st)
        for st in ["ACTIVE", "CANDIDATE", "DECAYING", "DEPRECATED"]
    }

    log.info("[Stage5] Edges: %d → %d  (+%d new  %d updated  %d removed)",
             len(edges_before), len(edges_after),
             len(new_edges), len(updated_edges), len(removed_edges))
    log.info("[Stage5] Status after: %s", status_after)
    log.info("[Stage5] New strategies: %d", len(new_strats))

    return {
        "snapshot_date":       last_day,
        "final_regime":        final_regime,
        "edges_before":        len(edges_before),
        "edges_after":         len(edges_after),
        "new_edges":           new_edges,
        "updated_edges":       updated_edges,
        "removed_edges":       removed_edges,
        "strats_before":       len(strats_before),
        "strats_after":        len(strats_after),
        "new_strats":          new_strats,
        "edges_by_status_after": status_after,
        "ede_report":          report,
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6 — METAMODEL STATUS
# ═══════════════════════════════════════════════════════════════════════════

def stage6_metamodel(closed_opps: int) -> dict:
    """
    Check MetaModel training readiness.
    Training is only attempted if closed_opps ≥ 10 (evidence threshold).
    """
    _banner("STAGE 6 — MetaModel Status")

    from meta_learning.meta_model import MetaModel
    from meta_learning.performance_dataset import PerformanceDataset

    dataset   = PerformanceDataset()
    records   = dataset.get_all()
    n_records = len(records)

    log.info("[Stage6] PerformanceDataset records: %d  closed_opps_in_study: %d",
             n_records, closed_opps)

    trained = False
    observations_used = 0
    reason = None

    if n_records >= 10:
        from meta_learning.meta_model import Observation
        from meta_learning.feature_extractor import FeatureExtractor
        ext = FeatureExtractor()
        observations = []
        for rec in records:
            fv  = ext.extract_from_dict(rec.feature_dict())
            obs = Observation(
                features   = fv.to_list(),
                strategy   = rec.strategy,
                r_multiple = rec.r_multiple,
            )
            observations.append(obs)
        model = MetaModel()
        model.fit(observations)
        trained = model.is_trained()
        observations_used = len(observations)
        if trained:
            log.info("[Stage6] MetaModel TRAINED with %d observations", observations_used)
        else:
            reason = "Model.fit() returned is_trained()=False"
    elif closed_opps == 0:
        reason = ("Study 002 produced 0 closed trade outcomes — all opportunities "
                  "remained open at window end. ml_performance_dataset.json "
                  "cannot be populated without completed/invalidated opportunities.")
    else:
        reason = (f"Only {n_records} records in PerformanceDataset — "
                  "minimum 10 required for training.")

    result = {
        "ml_dataset_exists":   os.path.exists(ML_DS),
        "ml_records":          n_records,
        "closed_opps_in_study": closed_opps,
        "model_trained":       trained,
        "observations_used":   observations_used,
        "min_required":        10,
        "reason_not_trained":  reason,
    }
    log.info("[Stage6] MetaModel trained: %s  records: %d", trained, n_records)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7 — KNOWLEDGE STORE VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def stage7_verify(baseline: dict) -> dict:
    """Final knowledge store counts and deltas vs baseline."""
    _banner("STAGE 7 — Knowledge Store Final Verification")

    final = _snapshot_knowledge_stores()

    result = {
        "baseline":                 baseline,
        "final":                    final,
        "feat_delta":               final["feat_total"] - baseline["feat_total"],
        "feat_labeled_delta":       final["feat_labeled"] - baseline["feat_labeled"],
        "edges_delta":              final["edges_total"] - baseline["edges_total"],
        "strats_delta":             final["strats_total"] - baseline["strats_total"],
        "ml_records_delta":         final["ml_records"] - baseline["ml_records"],
    }

    log.info("[Stage7] Feature DB:      %d → %d  (Δ%+d)",
             baseline["feat_total"], final["feat_total"], result["feat_delta"])
    log.info("[Stage7] Labeled records: %d → %d  (Δ%+d)",
             baseline["feat_labeled"], final["feat_labeled"], result["feat_labeled_delta"])
    log.info("[Stage7] Edges:           %d → %d  (Δ%+d)",
             baseline["edges_total"], final["edges_total"], result["edges_delta"])
    log.info("[Stage7] Strategies:      %d → %d  (Δ%+d)",
             baseline["strats_total"], final["strats_total"], result["strats_delta"])
    log.info("[Stage7] ML records:      %d → %d  (Δ%+d)",
             baseline["ml_records"], final["ml_records"], result["ml_records_delta"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    t0 = time.time()
    _banner("STUDY 002 — ONE-YEAR HISTORICAL MARKET LEARNING PIPELINE")
    log.info("Study DB:  %s", STUDY_DB)
    log.info("Started:   %s", datetime.now().isoformat(timespec="seconds"))

    conn = _open_study_db()

    # Verify DB has data
    n_ohlcv = conn.execute("SELECT COUNT(*) FROM ohlcv_daily").fetchone()[0]
    n_signals = conn.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
    log.info("[Main] DB check: ohlcv=%d  signals=%d", n_ohlcv, n_signals)

    if n_ohlcv == 0:
        log.error("[Main] No OHLCV data in study DB. Abort.")
        sys.exit(1)

    # Baseline knowledge store snapshot
    baseline = _snapshot_knowledge_stores()
    log.info("[Main] Baseline — feat:%d  edges:%d  strats:%d  ml:%d",
             baseline["feat_total"], baseline["edges_total"],
             baseline["strats_total"], baseline["ml_records"])

    # OHLCV coverage statistics
    ohlcv_stats = conn.execute("""
        SELECT COUNT(DISTINCT trade_date) AS dates,
               COUNT(DISTINCT symbol)     AS symbols,
               COUNT(*)                   AS total_rows
        FROM ohlcv_daily
        WHERE symbol != ?
    """, (NIFTY_SYM,)).fetchone()

    # Build regime map
    log.info("[Main] Building regime map…")
    regime_map = _build_regime_map(conn)
    regime_counts: dict[str, int] = {}
    for regime in regime_map.values():
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
    log.info("[Main] Regime map built: %s", regime_counts)

    # Run all stages
    session_records  = stage0_session_records(conn, regime_map)
    regime_analysis  = stage1_regime_analysis(session_records)
    sig_opp_analysis = stage2_signal_opportunity_analysis(conn, regime_map)
    sector_analysis  = stage3_sector_analysis(conn)
    feat_result      = stage4_enrich_feature_db(conn, regime_map)
    ede_result       = stage5_ede(conn, regime_map)
    meta_result      = stage6_metamodel(sig_opp_analysis["closed_opportunities"])
    verify_result    = stage7_verify(baseline)

    conn.close()

    elapsed = round(time.time() - t0, 1)
    _banner(f"STUDY 002 PIPELINE COMPLETE — {elapsed}s")

    # Compile full results
    results = {
        "study":           "Study 002 — One-Year Historical Market Learning",
        "date_range":      {"start": "2025-08-01", "end": "2026-07-31"},
        "executed_at":     datetime.now().isoformat(timespec="seconds"),
        "elapsed_s":       elapsed,
        "ohlcv_coverage":  {
            "trading_dates":   ohlcv_stats["dates"],
            "symbols":         ohlcv_stats["symbols"],
            "total_rows":      ohlcv_stats["total_rows"],
        },
        "regime_map_summary": regime_counts,
        "stage0_sessions":    session_records,
        "stage1_regime":      regime_analysis,
        "stage2_signals_opps": sig_opp_analysis,
        "stage3_sectors":     sector_analysis,
        "stage4_features":    feat_result,
        "stage5_ede":         ede_result,
        "stage6_metamodel":   meta_result,
        "stage7_verify":      verify_result,
    }

    with open(RESULTS, "w") as f:
        json.dump(results, f, indent=2, default=str)

    log.info("[Main] Results saved to %s", RESULTS)

    # Quick summary
    log.info("")
    log.info("══ STUDY 002 SUMMARY ════════════════════════════════")
    log.info("  Trading sessions: %d", len(session_records))
    log.info("  OHLCV rows:       %d  (%d symbols, %d dates)",
             ohlcv_stats["total_rows"], ohlcv_stats["symbols"], ohlcv_stats["dates"])
    log.info("  Regime breakdown: %s", regime_counts)
    log.info("  Total signals:    %d", sig_opp_analysis["total_signals"])
    log.info("  Total opps:       %d  (closed: %d)",
             sig_opp_analysis["total_opportunities"],
             sig_opp_analysis["closed_opportunities"])
    log.info("  Features:         %d → %d (+%d)",
             baseline["feat_total"], verify_result["final"]["feat_total"],
             verify_result["feat_delta"])
    log.info("  Edges:            %s", ede_result["edges_by_status_after"])
    log.info("  MetaModel:        trained=%s  records=%d",
             meta_result["model_trained"], meta_result["ml_records"])
    log.info("  Elapsed:          %.1fs", elapsed)
    log.info("══════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
