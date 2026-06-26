"""
Market Scanner — Phase D
========================
Post-market deep scan across Nifty 500 + liquid midcaps.
Runs at 16:45 IST on weekdays, triggered by master_orchestrator.py.

Responsibilities:
  Stage 1 — Fetch 35-day OHLCV for all symbols from Yahoo Finance
  Stage 2 — Compute fresh technical context: RSI(14), ATR(14), support, resistance,
             volume_ratio, adv_crore, trend clarity, breakout proximity
  Stage 3 — Apply structural quality gates and sector diversification caps
  Stage 4 — Apply concentration penalties (symbols repeated over consecutive days)
  Stage 5 — Write prepared candidates to CandidateStore

Governance constraints (NEVER changes these):
  - Does NOT interact with Layers 5-17
  - Does NOT modify _identify_setup(), debate logic, or governance thresholds
  - Prepared candidates are INPUTS to the pipeline, not pre-approved trades
  - Every candidate still passes full debate + MC + risk governance before execution
  - Safe mode: if scanner fails, CandidateStore is not updated → static fallback activates

Shadow mode (SCANNER_SHADOW_MODE = True in config):
  - Runs and logs everything but does NOT write to CandidateStore
  - Allows 5-10 session validation before live activation
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from opportunity_engine.candidate_store import CandidateStore
from opportunity_engine.filter_funnel_audit import get_filter_funnel_audit
from utils import get_logger
from utils.safe_scalar import safe_scalar
from utils.scalar_audit import get_scalar_audit

log = get_logger(__name__)

# ── Resource bounds (from config, with safe defaults) ───────────────────────
try:
    from config import (
        SCANNER_MAX_SYMBOLS,
        SCANNER_MAX_CANDIDATES,
        SCANNER_MAX_RUNTIME_MINUTES,
        SCANNER_SHADOW_MODE,
        PREPARED_UNIVERSE_MIN_COVERAGE_PCT,
        MIN_ADV_CRORE,
        MIN_PREPARED_SCORE,
        MAX_PREPARED_CANDIDATES,
    )
except ImportError:
    SCANNER_MAX_SYMBOLS               = 600
    SCANNER_MAX_CANDIDATES            = 120
    SCANNER_MAX_RUNTIME_MINUTES       = 20
    SCANNER_SHADOW_MODE               = False
    PREPARED_UNIVERSE_MIN_COVERAGE_PCT = 60.0
    MIN_ADV_CRORE                     = 50.0
    MIN_PREPARED_SCORE                = 0.55
    MAX_PREPARED_CANDIDATES           = 120

# ── Sector diversification cap ────────────────────────────────────────────────
# No more than this fraction of final candidates from any single sector.
SECTOR_MAX_FRACTION = 0.20   # 20%

# ── ATR proxy divergence tolerance ───────────────────────────────────────────
# If (|proxy_ATR - real_ATR| / real_ATR) > this → use ATR-anchored levels.
ATR_DIVERGENCE_THRESHOLD = 0.40

# ── Minimum data quality gates ────────────────────────────────────────────────
MIN_HISTORY_DAYS  = 15     # skip symbol if fewer than this many trading days available
MIN_ATR_PCT       = 0.3    # skip if ATR% < 0.3% of LTP (too illiquid / stale data)
MAX_ATR_PCT_GATE  = 8.0    # skip if ATR% > 8% (too volatile for reliable setups)
MIN_VOLUME_RATIO  = 0.2    # skip if 3-day avg vol < 20% of 20-day avg (liquidity concern)

# ── Concentration penalty ─────────────────────────────────────────────────────
# Symbol appearing in prepared list for N consecutive days gets score penalty.
CONCENTRATION_PENALTY_START_DAYS = 3    # no penalty for first 3 days
CONCENTRATION_PENALTY_PER_DAY    = 0.05 # 5% score reduction per day beyond start

# ── Bucket classification thresholds ─────────────────────────────────────────
BREAKOUT_PROXIMITY_PCT  = 0.02   # LTP within 2% below resistance = breakout candidate
PULLBACK_PROXIMITY_PCT  = 0.04   # LTP within 4% above support in bull regime = pullback
OVERSOLD_RSI_MAX        = 40.0   # RSI ≤ 40 = mean-reversion bounce candidate
OVERBOUGHT_RSI_MIN      = 65.0   # RSI ≥ 65 = potential short / avoid long candidate
VOLUME_EXPANSION_MIN    = 1.8    # volume_ratio ≥ 1.8 = volume expansion bucket


def run_scan(universe_path: Optional[str] = None) -> bool:
    """
    Main entry point. Called by master_orchestrator at 16:45 IST.

    Args:
        universe_path: path to nifty500_universe.json. Defaults to data/nifty500_universe.json.

    Returns True if scan completed and store was updated (or shadow mode ran).
    Returns False on critical failure.
    """
    scan_start = time.monotonic()
    log.info("[ScannerRun] Starting post-market scan. shadow_mode=%s", SCANNER_SHADOW_MODE)

    # ── Load symbol universe ─────────────────────────────────────────────────
    universe = _load_universe(universe_path)
    if not universe:
        log.error("[ScannerRun] Failed to load symbol universe — aborting.")
        return False

    symbols = [s["symbol"] for s in universe[:SCANNER_MAX_SYMBOLS]]
    sector_map = {s["symbol"]: s.get("sector", "UNKNOWN") for s in universe}
    index_map  = {s["symbol"]: s.get("index", "")         for s in universe}
    log.info("[ScannerRun] Universe loaded: %d symbols (capped at %d).",
             len(universe), SCANNER_MAX_SYMBOLS)

    # ── Fetch historical data ────────────────────────────────────────────────
    raw_data = _batch_fetch(symbols, scan_start)
    if raw_data is None:
        log.error("[ScannerRun] Batch fetch failed — aborting.")
        return False

    # ── Compute technical context per symbol ─────────────────────────────────
    processed: List[Dict[str, Any]] = []
    failed_symbols: List[str] = []
    failed_count = 0

    for sym in symbols:
        # Runtime guard — abort if scanner exceeds max allowed time
        elapsed_min = (time.monotonic() - scan_start) / 60.0
        if elapsed_min > SCANNER_MAX_RUNTIME_MINUTES:
            log.warning("[ScannerRun] Runtime limit reached (%.1f min) — stopping at %d/%d symbols.",
                        elapsed_min, len(processed) + failed_count, len(symbols))
            break

        result = _process_symbol(sym, raw_data)
        if result is None:
            failed_count += 1
            failed_symbols.append(sym)
            continue
        processed.append(result)

    # Log which specific symbols failed — helps diagnose coverage gaps
    if failed_symbols:
        log.debug(
            "[ScannerCoverage] Failed symbols (%d): %s",
            len(failed_symbols),
            ", ".join(failed_symbols[:40]) + ("..." if len(failed_symbols) > 40 else ""),
        )

    attempted  = len(processed) + failed_count
    coverage   = (len(processed) / attempted * 100.0) if attempted > 0 else 0.0

    log.info(
        "[CandidateCoverage] symbols_attempted=%d symbols_successful=%d"
        " symbols_failed=%d coverage_pct=%.1f%%",
        attempted, len(processed), failed_count, coverage,
    )

    if coverage < PREPARED_UNIVERSE_MIN_COVERAGE_PCT:
        log.warning(
            "[ScannerRun] Coverage %.1f%% below minimum %.1f%% — candidate file NOT written.",
            coverage, PREPARED_UNIVERSE_MIN_COVERAGE_PCT,
        )
        return False

    # ── Apply concentration penalties ────────────────────────────────────────
    streak_counts = CandidateStore.get_consecutive_selection_counts()
    for r in processed:
        sym = r["symbol"]
        streak = streak_counts.get(sym, 0)
        if streak >= CONCENTRATION_PENALTY_START_DAYS:
            excess   = streak - CONCENTRATION_PENALTY_START_DAYS
            penalty  = min(excess * CONCENTRATION_PENALTY_PER_DAY, 0.30)  # cap at 30%
            r["score"] = round(r["score"] * (1.0 - penalty), 4)
            if penalty > 0:
                log.debug("[ConcentrationPenalty] %s streak=%d penalty=%.0f%% new_score=%.3f",
                          sym, streak, penalty * 100, r["score"])

    # ── Sort and apply sector diversification cap ─────────────────────────────
    processed.sort(key=lambda x: x["score"], reverse=True)
    candidates = _apply_sector_cap(processed, sector_map, SCANNER_MAX_CANDIDATES)

    # Patch 3 — emit [PreparedUniverseCap] when truncation actually occurred
    if len(processed) > len(candidates):
        log.info(
            "[PreparedUniverseCap] before=%d after=%d cap=%d"
            " (higher-ranked candidates retained)",
            len(processed), len(candidates), SCANNER_MAX_CANDIDATES,
        )

    # Patch 4 — minimum quality floor: drop candidates below MIN_PREPARED_SCORE
    _before_floor = len(candidates)
    _score_passed: List[Dict[str, Any]] = []
    for _sc in candidates:
        if _sc.get("score", 0.0) >= MIN_PREPARED_SCORE:
            _score_passed.append(_sc)
        else:
            # [Audit 1] per-symbol rejection forensic for score_floor stage
            log.info("[FilterStageReject] stage=score_floor symbol=%s score=%.3f"
                     " threshold=%.2f buckets=%s",
                     _sc.get("symbol", "?"), _sc.get("score", 0.0),
                     MIN_PREPARED_SCORE, _sc.get("buckets", []))
    candidates = _score_passed
    _removed_by_floor = _before_floor - len(candidates)
    if _removed_by_floor > 0:
        log.info(
            "[PreparedScoreFloor] removed=%d threshold=%.2f remaining=%d"
            " (choppy/weak setups excluded)",
            _removed_by_floor, MIN_PREPARED_SCORE, len(candidates),
        )

    # Final absolute cap after all filters (Patch 3 / MAX_PREPARED_CANDIDATES)
    if len(candidates) > MAX_PREPARED_CANDIDATES:
        log.info("[PreparedUniverseCap] final_trim=%d (max=%d)",
                 len(candidates), MAX_PREPARED_CANDIDATES)
        candidates = candidates[:MAX_PREPARED_CANDIDATES]

    log.info(
        "[PreparedUniverseStats] total_processed=%d after_sector_cap=%d"
        " after_score_floor=%d sector_cap_fraction=%.0f%% max_candidates=%d",
        len(processed), _before_floor, len(candidates),
        SECTOR_MAX_FRACTION * 100, SCANNER_MAX_CANDIDATES,
    )

    # ── Enrich with index / sector metadata ──────────────────────────────────
    for c in candidates:
        c["sector"] = sector_map.get(c["symbol"], "UNKNOWN")
        c["index"]  = index_map.get(c["symbol"], "")

    # ── Build context block ──────────────────────────────────────────────────
    regime = _detect_simple_regime(candidates)
    context = {
        "regime":             regime,
        "vix":                None,   # populated by overnight overlay (Phase F)
        "scanner_feed_state": "YAHOO_FALLBACK",
        "regime_confidence":  None,   # populated by overnight overlay (Phase F)
    }

    scanner_stats = {
        "symbols_attempted":  attempted,
        "symbols_successful": len(processed),
        "symbols_failed":     failed_count,
        "coverage_pct":       round(coverage, 1),
        "scan_duration_min":  round((time.monotonic() - scan_start) / 60.0, 2),
        "candidates_before_sector_cap": len(processed),
        "candidates_after_sector_cap":  len(candidates),
    }

    # ── Record concentration memory ───────────────────────────────────────────
    selected_symbols = [c["symbol"] for c in candidates]
    CandidateStore.record_selected_symbols(selected_symbols)

    # ── Write to store (or shadow-log only) ──────────────────────────────────
    if SCANNER_SHADOW_MODE:
        log.info(
            "[ScannerRun] SHADOW MODE — candidates generated but NOT written to store. "
            "candidates=%d coverage=%.1f%%  Review [PreparedUniverseStats] logs to validate "
            "before setting SCANNER_SHADOW_MODE=False.",
            len(candidates), coverage,
        )
        # Log top-10 for shadow validation
        for i, c in enumerate(candidates[:10], 1):
            log.info(
                "[ShadowCandidate] rank=%d symbol=%s score=%.3f buckets=%s"
                " rsi=%.1f vol=%.1fx sector=%s",
                i, c["symbol"], c["score"], c.get("buckets", []),
                c.get("rsi", 0), c.get("volume_ratio", 0), c.get("sector", "?"),
            )
        return True

    success = CandidateStore.write(
        candidates=candidates,
        context=context,
        scanner_stats=scanner_stats,
    )
    _total_sec = time.monotonic() - scan_start
    if success:
        log.info(
            "[ScannerRun] Complete. candidates=%d coverage=%.1f%% duration=%.1fmin",
            len(candidates), coverage, _total_sec / 60.0,
        )
    # Patch 6 — performance telemetry (always emitted, even on shadow / failure)
    log.info(
        "[ScannerPerformance] scan_runtime_sec=%.1f symbols_scanned=%d"
        " symbols_per_sec=%.2f candidates=%d",
        _total_sec,
        len(symbols),
        len(symbols) / _total_sec if _total_sec > 0 else 0.0,
        len(candidates),
    )
    # ── [Audit 1] Feed scanner-level funnel counts into FilterFunnelAudit ──────────
    try:
        get_filter_funnel_audit().record_scanner_stage(
            symbols_attempted = attempted,
            data_ok           = len(processed),
            after_sector_cap  = _before_floor,       # len(candidates) before score floor
            after_score_floor = len(candidates),     # len(candidates) after score floor
        )
    except Exception as _ffa_e:
        log.debug("[FilterFunnelAudit] scanner_stage record failed: %s", _ffa_e)

    # ── [Audit 3] Freshness validation: audit freshness_age_minutes accuracy ───────
    try:
        _emit_freshness_validation(candidates)
    except Exception as _fv_e:
        log.debug("[FreshnessValidation] emit failed: %s", _fv_e)

    # ── ScalarNormalizationAudit: emit per-scan coverage summary ─────────────
    try:
        get_scalar_audit().emit_coverage_audit()
    except Exception:
        pass
    return success


# ── [Audit 3] Freshness validation helper ─────────────────────────────────────

def _emit_freshness_validation(candidates: List[Dict[str, Any]]) -> None:
    """
    [Audit 3] Observational only — emits [FreshnessValidation] to quantify
    how stale prepared candidates are at the point of writing.

    The candidate store sets freshness_age_minutes=0 (hardcoded) and
    last_refresh_time=valid_until_utc (expiry, NOT refresh time).
    This audit computes the actual age from prepared_at and records the
    discrepancy WITHOUT modifying any stored value.
    """
    from datetime import datetime, timezone as _tz
    _now = datetime.now(_tz.utc)

    total = len(candidates)
    if total == 0:
        return

    always_zero      = 0   # records where freshness_age_minutes == 0 (hardcoded)
    has_prepared_at  = 0   # records that have prepared_at field
    ages             = []  # true ages in minutes (computed from prepared_at)
    expiry_used      = 0   # records where last_refresh_time == valid_until_utc (semantic mismatch)
    missing_key      = 0   # records missing prepared_at field

    for c in candidates:
        # Count hardcoded-zero records
        if c.get("freshness_age_minutes", -1) == 0:
            always_zero += 1

        # Check last_refresh_time vs valid_until_utc (semantic mismatch detection)
        _lrt = c.get("last_refresh_time", "")
        _vuu = c.get("valid_until_utc", "")
        if _lrt and _vuu and _lrt == _vuu:
            expiry_used += 1

        # Compute true age from prepared_at
        _pa_str = c.get("prepared_at", "")
        if not _pa_str:
            missing_key += 1
            continue
        has_prepared_at += 1
        try:
            _pa = datetime.fromisoformat(_pa_str.replace("Z", "+00:00"))
            _true_age_min = int((_now - _pa).total_seconds() / 60)
            ages.append(_true_age_min)
        except Exception:
            pass

    avg_age = sum(ages) / len(ages) if ages else 0.0
    max_age = max(ages) if ages else 0
    min_age = min(ages) if ages else 0

    log.info(
        "[FreshnessValidation]"
        " candidates=%d always_zero_pct=%.1f%%"
        " has_prepared_at=%d missing_prepared_at=%d"
        " true_age_min_avg=%.1f true_age_min_max=%d true_age_min_min=%d"
        " expiry_used_as_refresh=%d"
        " note=freshness_age_minutes_is_hardcoded_0_in_store_see_candidate_store.py",
        total,
        (always_zero / total * 100.0) if total > 0 else 0.0,
        has_prepared_at, missing_key,
        avg_age, max_age, min_age,
        expiry_used,
    )


# ── Symbol universe loader ─────────────────────────────────────────────────

def _load_universe(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load nifty500_universe.json. Returns [] on failure."""
    universe_path = Path(path) if path else (
        Path(__file__).parent.parent / "data" / "nifty500_universe.json"
    )
    if not universe_path.exists():
        log.warning("[ScannerRun] Universe file not found: %s — using built-in base symbols.", universe_path)
        return _builtin_universe()

    try:
        import json
        data = json.loads(universe_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            log.error("[ScannerRun] Invalid universe format — expected list.")
            return _builtin_universe()
        log.info("[ScannerRun] Loaded universe: %d symbols from %s", len(data), universe_path)
        return data
    except Exception as exc:
        log.error("[ScannerRun] Failed to load universe file: %s — using built-in.", exc)
        return _builtin_universe()


def _builtin_universe() -> List[Dict[str, Any]]:
    """
    Full 230-symbol NSE universe seed (NIFTY50 → NIFTY500 tiers) with sector tags.
    Used when nifty500_universe.json is absent and as the source for
    _write_universe_json() during the weekly Monday rebuild.
    """
    return [
        {"symbol": "RELIANCE",      "yahoo_ticker": "RELIANCE.NS",      "sector": "ENERGY",       "index": "NIFTY50"},
        {"symbol": "HDFCBANK",      "yahoo_ticker": "HDFCBANK.NS",      "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "ICICIBANK",     "yahoo_ticker": "ICICIBANK.NS",     "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "INFY",          "yahoo_ticker": "INFY.NS",          "sector": "IT",           "index": "NIFTY50"},
        {"symbol": "TCS",           "yahoo_ticker": "TCS.NS",           "sector": "IT",           "index": "NIFTY50"},
        {"symbol": "HCLTECH",       "yahoo_ticker": "HCLTECH.NS",       "sector": "IT",           "index": "NIFTY50"},
        {"symbol": "WIPRO",         "yahoo_ticker": "WIPRO.NS",         "sector": "IT",           "index": "NIFTY50"},
        {"symbol": "TECHM",         "yahoo_ticker": "TECHM.NS",         "sector": "IT",           "index": "NIFTY50"},
        {"symbol": "LT",            "yahoo_ticker": "LT.NS",            "sector": "INFRA",        "index": "NIFTY50"},
        {"symbol": "AXISBANK",      "yahoo_ticker": "AXISBANK.NS",      "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "KOTAKBANK",     "yahoo_ticker": "KOTAKBANK.NS",     "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "SBIN",          "yahoo_ticker": "SBIN.NS",          "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "BHARTIARTL",    "yahoo_ticker": "BHARTIARTL.NS",    "sector": "TELECOM",      "index": "NIFTY50"},
        {"symbol": "TATASTEEL",     "yahoo_ticker": "TATASTEEL.NS",     "sector": "METALS",       "index": "NIFTY50"},
        {"symbol": "HINDALCO",      "yahoo_ticker": "HINDALCO.NS",      "sector": "METALS",       "index": "NIFTY50"},
        {"symbol": "JSWSTEEL",      "yahoo_ticker": "JSWSTEEL.NS",      "sector": "METALS",       "index": "NIFTY50"},
        {"symbol": "ONGC",          "yahoo_ticker": "ONGC.NS",          "sector": "ENERGY",       "index": "NIFTY50"},
        {"symbol": "COALINDIA",     "yahoo_ticker": "COALINDIA.NS",     "sector": "ENERGY",       "index": "NIFTY50"},
        {"symbol": "NTPC",          "yahoo_ticker": "NTPC.NS",          "sector": "POWER",        "index": "NIFTY50"},
        {"symbol": "POWERGRID",     "yahoo_ticker": "POWERGRID.NS",     "sector": "POWER",        "index": "NIFTY50"},
        {"symbol": "ITC",           "yahoo_ticker": "ITC.NS",           "sector": "FMCG",         "index": "NIFTY50"},
        {"symbol": "HINDUNILVR",    "yahoo_ticker": "HINDUNILVR.NS",    "sector": "FMCG",         "index": "NIFTY50"},
        {"symbol": "NESTLEIND",     "yahoo_ticker": "NESTLEIND.NS",     "sector": "FMCG",         "index": "NIFTY50"},
        {"symbol": "BAJFINANCE",    "yahoo_ticker": "BAJFINANCE.NS",    "sector": "FINANCIAL",    "index": "NIFTY50"},
        {"symbol": "BAJAJFINSV",    "yahoo_ticker": "BAJAJFINSV.NS",    "sector": "FINANCIAL",    "index": "NIFTY50"},
        {"symbol": "HDFCLIFE",      "yahoo_ticker": "HDFCLIFE.NS",      "sector": "FINANCIAL",    "index": "NIFTY50"},
        {"symbol": "SBILIFE",       "yahoo_ticker": "SBILIFE.NS",       "sector": "FINANCIAL",    "index": "NIFTY50"},
        {"symbol": "MARUTI",        "yahoo_ticker": "MARUTI.NS",        "sector": "AUTO",         "index": "NIFTY50"},
        {"symbol": "TATAMOTORS",    "yahoo_ticker": "TATAMOTORS.NS",    "sector": "AUTO",         "index": "NIFTY50"},
        {"symbol": "M&M",           "yahoo_ticker": "M&M.NS",           "sector": "AUTO",         "index": "NIFTY50"},
        {"symbol": "EICHERMOT",     "yahoo_ticker": "EICHERMOT.NS",     "sector": "AUTO",         "index": "NIFTY50"},
        {"symbol": "HEROMOTOCO",    "yahoo_ticker": "HEROMOTOCO.NS",    "sector": "AUTO",         "index": "NIFTY50"},
        {"symbol": "SUNPHARMA",     "yahoo_ticker": "SUNPHARMA.NS",     "sector": "PHARMA",       "index": "NIFTY50"},
        {"symbol": "DRREDDY",       "yahoo_ticker": "DRREDDY.NS",       "sector": "PHARMA",       "index": "NIFTY50"},
        {"symbol": "DIVISLAB",      "yahoo_ticker": "DIVISLAB.NS",      "sector": "PHARMA",       "index": "NIFTY50"},
        {"symbol": "CIPLA",         "yahoo_ticker": "CIPLA.NS",         "sector": "PHARMA",       "index": "NIFTY50"},
        {"symbol": "ASIANPAINT",    "yahoo_ticker": "ASIANPAINT.NS",    "sector": "PAINTS",       "index": "NIFTY50"},
        {"symbol": "TITAN",         "yahoo_ticker": "TITAN.NS",         "sector": "CONSUMER",     "index": "NIFTY50"},
        {"symbol": "GRASIM",        "yahoo_ticker": "GRASIM.NS",        "sector": "CEMENT",       "index": "NIFTY50"},
        {"symbol": "ULTRACEMCO",    "yahoo_ticker": "ULTRACEMCO.NS",    "sector": "CEMENT",       "index": "NIFTY50"},
        {"symbol": "ADANIENT",      "yahoo_ticker": "ADANIENT.NS",      "sector": "CONGLOMERATE", "index": "NIFTY50"},
        {"symbol": "ADANIPORTS",    "yahoo_ticker": "ADANIPORTS.NS",    "sector": "INFRA",        "index": "NIFTY50"},
        {"symbol": "TATACONSUM",    "yahoo_ticker": "TATACONSUM.NS",    "sector": "FMCG",         "index": "NIFTY50"},
        {"symbol": "INDUSINDBK",    "yahoo_ticker": "INDUSINDBK.NS",    "sector": "BANKING",      "index": "NIFTY50"},
        {"symbol": "BRITANNIA",     "yahoo_ticker": "BRITANNIA.NS",     "sector": "FMCG",         "index": "NIFTY50"},
        {"symbol": "BPCL",          "yahoo_ticker": "BPCL.NS",          "sector": "ENERGY",       "index": "NIFTY50"},
        {"symbol": "TRENT",         "yahoo_ticker": "TRENT.NS",         "sector": "RETAIL",       "index": "NIFTY50"},
        {"symbol": "BEL",           "yahoo_ticker": "BEL.NS",           "sector": "DEFENCE",      "index": "NIFTY50"},
        {"symbol": "APOLLOHOSP",    "yahoo_ticker": "APOLLOHOSP.NS",    "sector": "HEALTHCARE",   "index": "NIFTY50"},
        {"symbol": "SHRIRAMFIN",    "yahoo_ticker": "SHRIRAMFIN.NS",    "sector": "FINANCIAL",    "index": "NIFTY50"},
        {"symbol": "BANKBARODA",    "yahoo_ticker": "BANKBARODA.NS",    "sector": "BANKING",      "index": "NIFTYNEXT50"},
        {"symbol": "CANBK",         "yahoo_ticker": "CANBK.NS",         "sector": "BANKING",      "index": "NIFTYNEXT50"},
        {"symbol": "PNB",           "yahoo_ticker": "PNB.NS",           "sector": "BANKING",      "index": "NIFTYNEXT50"},
        {"symbol": "IDFCFIRSTB",    "yahoo_ticker": "IDFCFIRSTB.NS",    "sector": "BANKING",      "index": "NIFTYNEXT50"},
        {"symbol": "FEDERALBNK",    "yahoo_ticker": "FEDERALBNK.NS",    "sector": "BANKING",      "index": "NIFTYNEXT50"},
        {"symbol": "BAJAJ-AUTO",    "yahoo_ticker": "BAJAJ-AUTO.NS",    "sector": "AUTO",         "index": "NIFTYNEXT50"},
        {"symbol": "TVSMOTORS",     "yahoo_ticker": "TVSMOTORS.NS",     "sector": "AUTO",         "index": "NIFTYNEXT50"},
        {"symbol": "BOSCHLTD",      "yahoo_ticker": "BOSCHLTD.NS",      "sector": "AUTO",         "index": "NIFTYNEXT50"},
        {"symbol": "MOTHERSON",     "yahoo_ticker": "MOTHERSON.NS",     "sector": "AUTO",         "index": "NIFTYNEXT50"},
        {"symbol": "ZOMATO",        "yahoo_ticker": "ZOMATO.NS",        "sector": "CONSUMER",     "index": "NIFTYNEXT50"},
        {"symbol": "NYKAA",         "yahoo_ticker": "NYKAA.NS",         "sector": "CONSUMER",     "index": "NIFTYNEXT50"},
        {"symbol": "PAYTM",         "yahoo_ticker": "PAYTM.NS",         "sector": "FINTECH",      "index": "NIFTYNEXT50"},
        {"symbol": "POLICYBZR",     "yahoo_ticker": "POLICYBZR.NS",     "sector": "FINTECH",      "index": "NIFTYNEXT50"},
        {"symbol": "DMART",         "yahoo_ticker": "DMART.NS",         "sector": "RETAIL",       "index": "NIFTYNEXT50"},
        {"symbol": "VEDL",          "yahoo_ticker": "VEDL.NS",          "sector": "METALS",       "index": "NIFTYNEXT50"},
        {"symbol": "NMDC",          "yahoo_ticker": "NMDC.NS",          "sector": "METALS",       "index": "NIFTYNEXT50"},
        {"symbol": "SAIL",          "yahoo_ticker": "SAIL.NS",          "sector": "METALS",       "index": "NIFTYNEXT50"},
        {"symbol": "HINDZINC",      "yahoo_ticker": "HINDZINC.NS",      "sector": "METALS",       "index": "NIFTYNEXT50"},
        {"symbol": "NAUKRI",        "yahoo_ticker": "NAUKRI.NS",        "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "MPHASIS",       "yahoo_ticker": "MPHASIS.NS",       "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "LTIM",          "yahoo_ticker": "LTIM.NS",          "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "PERSISTENT",    "yahoo_ticker": "PERSISTENT.NS",    "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "COFORGE",       "yahoo_ticker": "COFORGE.NS",       "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "HAVELLS",       "yahoo_ticker": "HAVELLS.NS",       "sector": "CONSUMER",     "index": "NIFTYNEXT50"},
        {"symbol": "VOLTAS",        "yahoo_ticker": "VOLTAS.NS",        "sector": "CONSUMER",     "index": "NIFTYNEXT50"},
        {"symbol": "CROMPTON",      "yahoo_ticker": "CROMPTON.NS",      "sector": "CONSUMER",     "index": "NIFTYNEXT50"},
        {"symbol": "GODREJCP",      "yahoo_ticker": "GODREJCP.NS",      "sector": "FMCG",         "index": "NIFTYNEXT50"},
        {"symbol": "DABUR",         "yahoo_ticker": "DABUR.NS",         "sector": "FMCG",         "index": "NIFTYNEXT50"},
        {"symbol": "MARICO",        "yahoo_ticker": "MARICO.NS",        "sector": "FMCG",         "index": "NIFTYNEXT50"},
        {"symbol": "COLPAL",        "yahoo_ticker": "COLPAL.NS",        "sector": "FMCG",         "index": "NIFTYNEXT50"},
        {"symbol": "EMAMILTD",      "yahoo_ticker": "EMAMILTD.NS",      "sector": "FMCG",         "index": "NIFTYNEXT50"},
        {"symbol": "PIDILITIND",    "yahoo_ticker": "PIDILITIND.NS",    "sector": "CHEMICALS",    "index": "NIFTYNEXT50"},
        {"symbol": "SRF",           "yahoo_ticker": "SRF.NS",           "sector": "CHEMICALS",    "index": "NIFTYNEXT50"},
        {"symbol": "AAVAS",         "yahoo_ticker": "AAVAS.NS",         "sector": "FINANCIAL",    "index": "NIFTYNEXT50"},
        {"symbol": "MUTHOOTFIN",    "yahoo_ticker": "MUTHOOTFIN.NS",    "sector": "FINANCIAL",    "index": "NIFTYNEXT50"},
        {"symbol": "CHOLAFIN",      "yahoo_ticker": "CHOLAFIN.NS",      "sector": "FINANCIAL",    "index": "NIFTYNEXT50"},
        {"symbol": "MAXHEALTH",     "yahoo_ticker": "MAXHEALTH.NS",     "sector": "HEALTHCARE",   "index": "NIFTYNEXT50"},
        {"symbol": "FORTIS",        "yahoo_ticker": "FORTIS.NS",        "sector": "HEALTHCARE",   "index": "NIFTYNEXT50"},
        {"symbol": "LALPATHLAB",    "yahoo_ticker": "LALPATHLAB.NS",    "sector": "HEALTHCARE",   "index": "NIFTYNEXT50"},
        {"symbol": "METROPOLIS",    "yahoo_ticker": "METROPOLIS.NS",    "sector": "HEALTHCARE",   "index": "NIFTYNEXT50"},
        {"symbol": "TORNTPHARM",    "yahoo_ticker": "TORNTPHARM.NS",    "sector": "PHARMA",       "index": "NIFTYNEXT50"},
        {"symbol": "AUROPHARMA",    "yahoo_ticker": "AUROPHARMA.NS",    "sector": "PHARMA",       "index": "NIFTYNEXT50"},
        {"symbol": "BIOCON",        "yahoo_ticker": "BIOCON.NS",        "sector": "PHARMA",       "index": "NIFTYNEXT50"},
        {"symbol": "LUPIN",         "yahoo_ticker": "LUPIN.NS",         "sector": "PHARMA",       "index": "NIFTYNEXT50"},
        {"symbol": "GLAND",         "yahoo_ticker": "GLAND.NS",         "sector": "PHARMA",       "index": "NIFTYNEXT50"},
        {"symbol": "LTTS",          "yahoo_ticker": "LTTS.NS",          "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "KPITTECH",      "yahoo_ticker": "KPITTECH.NS",      "sector": "IT",           "index": "NIFTYNEXT50"},
        {"symbol": "TATACOMM",      "yahoo_ticker": "TATACOMM.NS",      "sector": "TELECOM",      "index": "NIFTYNEXT50"},
        {"symbol": "DLF",           "yahoo_ticker": "DLF.NS",           "sector": "REALESTATE",   "index": "NIFTYNEXT50"},
        {"symbol": "GODREJPROP",    "yahoo_ticker": "GODREJPROP.NS",    "sector": "REALESTATE",   "index": "NIFTYNEXT50"},
        {"symbol": "OBEROIRLTY",    "yahoo_ticker": "OBEROIRLTY.NS",    "sector": "REALESTATE",   "index": "NIFTYNEXT50"},
        {"symbol": "SIEMENS",       "yahoo_ticker": "SIEMENS.NS",       "sector": "INFRA",        "index": "NIFTY100"},
        {"symbol": "ABB",           "yahoo_ticker": "ABB.NS",           "sector": "INFRA",        "index": "NIFTY100"},
        {"symbol": "CUMMINSIND",    "yahoo_ticker": "CUMMINSIND.NS",    "sector": "INFRA",        "index": "NIFTY100"},
        {"symbol": "THERMAX",       "yahoo_ticker": "THERMAX.NS",       "sector": "INFRA",        "index": "NIFTY100"},
        {"symbol": "HAL",           "yahoo_ticker": "HAL.NS",           "sector": "DEFENCE",      "index": "NIFTY100"},
        {"symbol": "COCHINSHIP",    "yahoo_ticker": "COCHINSHIP.NS",    "sector": "DEFENCE",      "index": "NIFTY100"},
        {"symbol": "NHPC",          "yahoo_ticker": "NHPC.NS",          "sector": "POWER",        "index": "NIFTY100"},
        {"symbol": "TORNTPOWER",    "yahoo_ticker": "TORNTPOWER.NS",    "sector": "POWER",        "index": "NIFTY100"},
        {"symbol": "CESC",          "yahoo_ticker": "CESC.NS",          "sector": "POWER",        "index": "NIFTY100"},
        {"symbol": "ADANIGREEN",    "yahoo_ticker": "ADANIGREEN.NS",    "sector": "POWER",        "index": "NIFTY100"},
        {"symbol": "TATAPOWER",     "yahoo_ticker": "TATAPOWER.NS",     "sector": "POWER",        "index": "NIFTY100"},
        {"symbol": "ASHOKLEY",      "yahoo_ticker": "ASHOKLEY.NS",      "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "BHARATFORG",    "yahoo_ticker": "BHARATFORG.NS",    "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "EXIDEIND",      "yahoo_ticker": "EXIDEIND.NS",      "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "TIINDIA",       "yahoo_ticker": "TIINDIA.NS",       "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "BALKRISIND",    "yahoo_ticker": "BALKRISIND.NS",    "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "MRF",           "yahoo_ticker": "MRF.NS",           "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "APOLLOTYRE",    "yahoo_ticker": "APOLLOTYRE.NS",    "sector": "AUTO",         "index": "NIFTY100"},
        {"symbol": "ZYDUSLIFE",     "yahoo_ticker": "ZYDUSLIFE.NS",     "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "ALKEM",         "yahoo_ticker": "ALKEM.NS",         "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "IPCA",          "yahoo_ticker": "IPCA.NS",          "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "ABBOTINDIA",    "yahoo_ticker": "ABBOTINDIA.NS",    "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "SANOFI",        "yahoo_ticker": "SANOFI.NS",        "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "IPCALAB",       "yahoo_ticker": "IPCALAB.NS",       "sector": "PHARMA",       "index": "NIFTY100"},
        {"symbol": "INDIANB",       "yahoo_ticker": "INDIANB.NS",       "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "BANKINDIA",     "yahoo_ticker": "BANKINDIA.NS",     "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "UCOBANK",       "yahoo_ticker": "UCOBANK.NS",       "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "J&KBANK",       "yahoo_ticker": "J&KBANK.NS",       "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "KARURVYSYA",    "yahoo_ticker": "KARURVYSYA.NS",    "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "DCBBANK",       "yahoo_ticker": "DCBBANK.NS",       "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "RBLBANK",       "yahoo_ticker": "RBLBANK.NS",       "sector": "BANKING",      "index": "NIFTY100"},
        {"symbol": "HDFCAMC",       "yahoo_ticker": "HDFCAMC.NS",       "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "MIRAE",         "yahoo_ticker": "MIRAE.NS",         "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "ICICIGI",       "yahoo_ticker": "ICICIGI.NS",       "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "ICICIPRULI",    "yahoo_ticker": "ICICIPRULI.NS",    "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "NIACL",         "yahoo_ticker": "NIACL.NS",         "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "STAR",          "yahoo_ticker": "STAR.NS",          "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "PNBHOUSING",    "yahoo_ticker": "PNBHOUSING.NS",    "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "LICHSGFIN",     "yahoo_ticker": "LICHSGFIN.NS",     "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "CANFINHOME",    "yahoo_ticker": "CANFINHOME.NS",    "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "HOMEFIRST",     "yahoo_ticker": "HOMEFIRST.NS",     "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "IRFC",          "yahoo_ticker": "IRFC.NS",          "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "PFC",           "yahoo_ticker": "PFC.NS",           "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "REC",           "yahoo_ticker": "REC.NS",           "sector": "FINANCIAL",    "index": "NIFTY100"},
        {"symbol": "SOLARINDS",     "yahoo_ticker": "SOLARINDS.NS",     "sector": "DEFENCE",      "index": "NIFTY200"},
        {"symbol": "MAZDOCK",       "yahoo_ticker": "MAZDOCK.NS",       "sector": "DEFENCE",      "index": "NIFTY200"},
        {"symbol": "BHEL",          "yahoo_ticker": "BHEL.NS",          "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "IRCTC",         "yahoo_ticker": "IRCTC.NS",         "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "CONCOR",        "yahoo_ticker": "CONCOR.NS",        "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "APLAPOLLO",     "yahoo_ticker": "APLAPOLLO.NS",     "sector": "METALS",       "index": "NIFTY200"},
        {"symbol": "JINDALSTEL",    "yahoo_ticker": "JINDALSTEL.NS",    "sector": "METALS",       "index": "NIFTY200"},
        {"symbol": "TATACHEM",      "yahoo_ticker": "TATACHEM.NS",      "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "DEEPAKNTR",     "yahoo_ticker": "DEEPAKNTR.NS",     "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "PIIND",         "yahoo_ticker": "PIIND.NS",         "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "UPL",           "yahoo_ticker": "UPL.NS",           "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "ATUL",          "yahoo_ticker": "ATUL.NS",          "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "NAVINFLUOR",    "yahoo_ticker": "NAVINFLUOR.NS",    "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "CLEAN",         "yahoo_ticker": "CLEAN.NS",         "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "VINATI",        "yahoo_ticker": "VINATI.NS",        "sector": "CHEMICALS",    "index": "NIFTY200"},
        {"symbol": "FINPIPE",       "yahoo_ticker": "FINPIPE.NS",       "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "ASTRAL",        "yahoo_ticker": "ASTRAL.NS",        "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "SUPREMEIND",    "yahoo_ticker": "SUPREMEIND.NS",    "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "KAYNES",        "yahoo_ticker": "KAYNES.NS",        "sector": "ELECTRONICS",  "index": "NIFTY200"},
        {"symbol": "DIXON",         "yahoo_ticker": "DIXON.NS",         "sector": "ELECTRONICS",  "index": "NIFTY200"},
        {"symbol": "AMBER",         "yahoo_ticker": "AMBER.NS",         "sector": "ELECTRONICS",  "index": "NIFTY200"},
        {"symbol": "VGUARD",        "yahoo_ticker": "VGUARD.NS",        "sector": "CONSUMER",     "index": "NIFTY200"},
        {"symbol": "WHIRLPOOL",     "yahoo_ticker": "WHIRLPOOL.NS",     "sector": "CONSUMER",     "index": "NIFTY200"},
        {"symbol": "BLUESTAR",      "yahoo_ticker": "BLUESTAR.NS",      "sector": "CONSUMER",     "index": "NIFTY200"},
        {"symbol": "SYMPHONY",      "yahoo_ticker": "SYMPHONY.NS",      "sector": "CONSUMER",     "index": "NIFTY200"},
        {"symbol": "KANSAINER",     "yahoo_ticker": "KANSAINER.NS",     "sector": "PAINTS",       "index": "NIFTY200"},
        {"symbol": "INDIGO",        "yahoo_ticker": "INDIGO.NS",        "sector": "AVIATION",     "index": "NIFTY200"},
        {"symbol": "SPICEJET",      "yahoo_ticker": "SPICEJET.NS",      "sector": "AVIATION",     "index": "NIFTY200"},
        {"symbol": "GMRAIRPORT",    "yahoo_ticker": "GMRAIRPORT.NS",    "sector": "INFRA",        "index": "NIFTY200"},
        {"symbol": "ZEEL",          "yahoo_ticker": "ZEEL.NS",          "sector": "MEDIA",        "index": "NIFTY200"},
        {"symbol": "SUNTV",         "yahoo_ticker": "SUNTV.NS",         "sector": "MEDIA",        "index": "NIFTY200"},
        {"symbol": "PVR",           "yahoo_ticker": "PVR.NS",           "sector": "MEDIA",        "index": "NIFTY200"},
        {"symbol": "INOXWIND",      "yahoo_ticker": "INOXWIND.NS",      "sector": "POWER",        "index": "NIFTY500"},
        {"symbol": "SUZLON",        "yahoo_ticker": "SUZLON.NS",        "sector": "POWER",        "index": "NIFTY500"},
        {"symbol": "CRISIL",        "yahoo_ticker": "CRISIL.NS",        "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "BSE",           "yahoo_ticker": "BSE.NS",           "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "MCX",           "yahoo_ticker": "MCX.NS",           "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "CDSL",          "yahoo_ticker": "CDSL.NS",          "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "ANGELONE",      "yahoo_ticker": "ANGELONE.NS",      "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "MOTILALOFS",    "yahoo_ticker": "MOTILALOFS.NS",    "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "LICI",          "yahoo_ticker": "LICI.NS",          "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "POLYCAB",       "yahoo_ticker": "POLYCAB.NS",       "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "FINOLEX",       "yahoo_ticker": "FINOLEX.NS",       "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "KEI",           "yahoo_ticker": "KEI.NS",           "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "GMMPFAUDLR",    "yahoo_ticker": "GMMPFAUDLR.NS",    "sector": "INFRA",        "index": "NIFTY500"},
        {"symbol": "KALYANKJIL",    "yahoo_ticker": "KALYANKJIL.NS",    "sector": "RETAIL",       "index": "NIFTY500"},
        {"symbol": "VEDANT",        "yahoo_ticker": "VEDANT.NS",        "sector": "RETAIL",       "index": "NIFTY500"},
        {"symbol": "SHOPPERSSTOP",  "yahoo_ticker": "SHOPPERSSTOP.NS",  "sector": "RETAIL",       "index": "NIFTY500"},
        {"symbol": "PCJEWELLER",    "yahoo_ticker": "PCJEWELLER.NS",    "sector": "RETAIL",       "index": "NIFTY500"},
        {"symbol": "SENCO",         "yahoo_ticker": "SENCO.NS",         "sector": "RETAIL",       "index": "NIFTY500"},
        {"symbol": "JUBLFOOD",      "yahoo_ticker": "JUBLFOOD.NS",      "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "DEVYANI",       "yahoo_ticker": "DEVYANI.NS",       "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "WESTLIFE",      "yahoo_ticker": "WESTLIFE.NS",      "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "EASEMYTRIP",    "yahoo_ticker": "EASEMYTRIP.NS",    "sector": "CONSUMER",     "index": "NIFTY500"},
        {"symbol": "MAHINDCIE",     "yahoo_ticker": "MAHINDCIE.NS",     "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "WABCO",         "yahoo_ticker": "WABCO.NS",         "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "SUPRAJIT",      "yahoo_ticker": "SUPRAJIT.NS",      "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "ENDURANCE",     "yahoo_ticker": "ENDURANCE.NS",     "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "MINDA",         "yahoo_ticker": "MINDA.NS",         "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "GABRIEL",       "yahoo_ticker": "GABRIEL.NS",       "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "ESCORTS",       "yahoo_ticker": "ESCORTS.NS",       "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "FORCEMOT",      "yahoo_ticker": "FORCEMOT.NS",      "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "SUNDRMFAST",    "yahoo_ticker": "SUNDRMFAST.NS",    "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "VSTIND",        "yahoo_ticker": "VSTIND.NS",        "sector": "AUTO",         "index": "NIFTY500"},
        {"symbol": "ELGIEQUIP",     "yahoo_ticker": "ELGIEQUIP.NS",     "sector": "INFRA",        "index": "NIFTY500"},
        {"symbol": "KSBBLTD",       "yahoo_ticker": "KSBBLTD.NS",       "sector": "INFRA",        "index": "NIFTY500"},
        {"symbol": "GRINDWELL",     "yahoo_ticker": "GRINDWELL.NS",     "sector": "INFRA",        "index": "NIFTY500"},
        {"symbol": "CRAFTSMAN",     "yahoo_ticker": "CRAFTSMAN.NS",     "sector": "INFRA",        "index": "NIFTY500"},
        {"symbol": "HUDCO",         "yahoo_ticker": "HUDCO.NS",         "sector": "FINANCIAL",    "index": "NIFTY500"},
        {"symbol": "INDIAGRID",     "yahoo_ticker": "INDIAGRID.NS",     "sector": "POWER",        "index": "NIFTY500"},
        {"symbol": "KPRMILL",       "yahoo_ticker": "KPRMILL.NS",       "sector": "TEXTILES",     "index": "NIFTY500"},
        {"symbol": "WELSPUNIND",    "yahoo_ticker": "WELSPUNIND.NS",    "sector": "TEXTILES",     "index": "NIFTY500"},
        {"symbol": "VARDHACRLC",    "yahoo_ticker": "VARDHACRLC.NS",    "sector": "TEXTILES",     "index": "NIFTY500"},
        {"symbol": "PAGEIND",       "yahoo_ticker": "PAGEIND.NS",       "sector": "TEXTILES",     "index": "NIFTY500"},
        {"symbol": "RAYMOND",       "yahoo_ticker": "RAYMOND.NS",       "sector": "TEXTILES",     "index": "NIFTY500"},
        {"symbol": "KKALPATAARU",   "yahoo_ticker": "KKALPATAARU.NS",   "sector": "REALESTATE",   "index": "NIFTY500"},
        {"symbol": "PRESTIGE",      "yahoo_ticker": "PRESTIGE.NS",      "sector": "REALESTATE",   "index": "NIFTY500"},
        {"symbol": "BRIGADE",       "yahoo_ticker": "BRIGADE.NS",       "sector": "REALESTATE",   "index": "NIFTY500"},
        {"symbol": "MACROTECH",     "yahoo_ticker": "MACROTECH.NS",     "sector": "REALESTATE",   "index": "NIFTY500"},
        {"symbol": "SUNTECKRLTY",   "yahoo_ticker": "SUNTECKRLTY.NS",   "sector": "REALESTATE",   "index": "NIFTY500"},
        {"symbol": "NUVOCO",        "yahoo_ticker": "NUVOCO.NS",        "sector": "CEMENT",       "index": "NIFTY500"},
        {"symbol": "AMBUJACEM",     "yahoo_ticker": "AMBUJACEM.NS",     "sector": "CEMENT",       "index": "NIFTY500"},
        {"symbol": "ACCLTD",        "yahoo_ticker": "ACCLTD.NS",        "sector": "CEMENT",       "index": "NIFTY500"},
        {"symbol": "JKCEMENT",      "yahoo_ticker": "JKCEMENT.NS",      "sector": "CEMENT",       "index": "NIFTY500"},
        {"symbol": "RAMCOCEM",      "yahoo_ticker": "RAMCOCEM.NS",      "sector": "CEMENT",       "index": "NIFTY500"},
    ]


def _write_universe_json() -> bool:
    """
    Atomically write the 230-symbol universe seed to data/nifty500_universe.json.
    Called by _run_weekly_universe_rebuild() every Monday at 08:30 IST.
    Returns True on success.
    """
    import json as _json_wu
    import os as _os_wu
    universe_path = Path(__file__).parent.parent / "data" / "nifty500_universe.json"
    try:
        universe_path.parent.mkdir(parents=True, exist_ok=True)
        _tmp = str(universe_path) + ".tmp"
        with open(_tmp, "w", encoding="utf-8") as _f:
            _json_wu.dump(_builtin_universe(), _f, indent=2, ensure_ascii=False)
        _os_wu.replace(_tmp, str(universe_path))
        log.info("[UniverseWriter] Wrote %d symbols to %s", len(_builtin_universe()), universe_path)
        return True
    except Exception as exc:
        log.error("[UniverseWriter] Failed to write universe JSON: %s", exc)
        return False


# ── Batch data fetch ──────────────────────────────────────────────────────────

def _batch_fetch(symbols: List[str], scan_start: float) -> Optional[pd.DataFrame]:
    """
    Download 35-day OHLCV for all symbols in chunks of 50.
    Returns a multi-level DataFrame (yfinance format) or None on total failure.
    Rate-limiting: 2-second sleep between chunks.
    """
    try:
        import yfinance as yf
    except ImportError:
        log.error("[ScannerRun] yfinance not installed — cannot run scanner.")
        return None

    tickers = [s + ".NS" for s in symbols]
    chunk_size = 50
    all_chunks: List[pd.DataFrame] = []

    for i in range(0, len(tickers), chunk_size):
        elapsed_min = (time.monotonic() - scan_start) / 60.0
        if elapsed_min > SCANNER_MAX_RUNTIME_MINUTES * 0.8:
            log.warning("[ScannerRun] Approaching runtime limit during fetch — stopping at chunk %d.", i // chunk_size)
            break

        chunk = tickers[i: i + chunk_size]
        try:
            df = yf.download(
                chunk, period="35d", interval="1d",
                progress=False, auto_adjust=True, group_by="column",
            )
            if df is not None and not df.empty:
                all_chunks.append(df)
        except Exception as exc:
            log.warning("[ScannerRun] Chunk %d fetch error: %s", i // chunk_size, exc)

        if i + chunk_size < len(tickers):
            time.sleep(2)  # rate-limit guard

    if not all_chunks:
        return None

    # Concatenate if multiple chunks
    if len(all_chunks) == 1:
        return all_chunks[0]

    try:
        return pd.concat(all_chunks, axis=1)
    except Exception as exc:
        log.error("[ScannerRun] Failed to concatenate chunk data: %s", exc)
        return all_chunks[0]  # return first chunk as partial fallback


# ── Per-symbol technical computation ─────────────────────────────────────────

def _process_symbol(symbol: str, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Extract technical context for one symbol.
    Returns None if data is insufficient or quality gates fail.
    """
    ns = symbol + ".NS"
    try:
        # Extract OHLCV for this symbol
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"][ns].dropna()
            high  = data["High"][ns].dropna()
            low   = data["Low"][ns].dropna()
            vol   = data["Volume"][ns].dropna()
        else:
            # Single-ticker download
            close = data["Close"].dropna()
            high  = data["High"].dropna()
            low   = data["Low"].dropna()
            vol   = data["Volume"].dropna()

        if len(close) < MIN_HISTORY_DAYS:
            return None

        ltp   = safe_scalar(close.iloc[-1], 0.0, f"{symbol}.close")
        if ltp <= 0:
            return None

        # RSI(14)
        rsi = round(safe_scalar(_compute_rsi(close).iloc[-1], 50.0, f"{symbol}.rsi"), 1)
        if np.isnan(rsi):
            rsi = 50.0

        # ATR(14) — real
        atr14 = safe_scalar(_compute_atr(high, low, close).iloc[-1], 0.0, f"{symbol}.atr14")
        if atr14 <= 0 or np.isnan(atr14):
            return None

        atr_pct = atr14 / ltp * 100.0

        # Volatility quality gates
        if atr_pct < MIN_ATR_PCT or atr_pct > MAX_ATR_PCT_GATE:
            return None

        # 20-day support / resistance
        w20        = close.iloc[-20:]
        support    = round(safe_scalar(w20.min(), 0.0, f"{symbol}.support"), 2)
        resistance = round(safe_scalar(w20.max(), 0.0, f"{symbol}.resistance"), 2)

        # ATR proxy divergence check — rebuild levels if needed
        proxy_atr  = (resistance - support) * 0.40
        divergence = abs(proxy_atr - atr14) / atr14 if atr14 > 0 else 0.0
        atr_anchored = False
        if divergence > ATR_DIVERGENCE_THRESHOLD:
            support      = round(ltp - atr14 * 2.5, 2)
            resistance   = round(ltp + atr14 * 2.5, 2)
            atr_anchored = True
            log.debug(
                "[LevelAdjustment] symbol=%s real_atr=%.2f proxy_atr=%.2f"
                " divergence_pct=%.1f action=ATR_ANCHORED new_support=%.2f new_resistance=%.2f",
                symbol, atr14, proxy_atr, divergence * 100, support, resistance,
            )

        # Volume ratio (3-day avg / 20-day avg)
        avg_vol    = safe_scalar(vol.iloc[-20:].mean(), 0.0, f"{symbol}.avg_vol")
        recent_vol = (
            safe_scalar(vol.iloc[-3:].mean(), 0.0, f"{symbol}.recent_vol")
            if len(vol) >= 3
            else safe_scalar(vol.iloc[-1], 0.0, f"{symbol}.recent_vol")
        )
        vol_ratio  = round(
            min(max(recent_vol / avg_vol if avg_vol > 0 else 1.0, 0.1), 8.0), 1
        )

        if vol_ratio < MIN_VOLUME_RATIO:
            return None   # severely below-average liquidity

        # ADV in crore: avg(close * volume) / 10_000_000 (Indian crore = 10M)
        adv_crore = int(round(
            safe_scalar((close.iloc[-20:] * vol.iloc[-20:]).mean(), 0.0, f"{symbol}.adv") / 1e7, 0
        ))
        adv_crore = max(adv_crore, 1)

        if adv_crore < int(MIN_ADV_CRORE):
            return None   # below minimum liquidity threshold

        # Bucket classification
        buckets = _classify_buckets(ltp, resistance, support, rsi, vol_ratio, atr14)

        # Base score: quality + momentum + setup proximity
        score = _compute_base_score(ltp, resistance, support, rsi, vol_ratio, atr14, atr_pct)

        # Conviction decay (used by premarket refiner)
        conviction_decay = 0.30 if "breakout" in buckets else 0.15

        return {
            "symbol":           symbol,
            "yahoo_ticker":     ns,
            "base_ltp":         ltp,
            "resistance":       resistance,
            "support":          support,
            "rsi":              rsi,
            "volume_ratio":     vol_ratio,
            "adv_crore":        adv_crore,
            "atr14":            round(atr14, 2),
            "atr_pct":          round(atr_pct, 2),
            "atr_anchored":     atr_anchored,
            "buckets":          buckets,
            "score":            score,
            "conviction_decay": conviction_decay,
            "overnight_adjustment": 1.0,     # Phase F will populate this
            "valid_until_utc":  None,         # Phase G will populate this
        }

    except Exception as exc:
        log.debug("[ScannerRun] Error processing %s: %s", symbol, exc)
        return None


# ── Scoring ────────────────────────────────────────────────────────────────────

def _compute_base_score(
    ltp: float, resistance: float, support: float,
    rsi: float, vol_ratio: float, atr14: float, atr_pct: float,
) -> float:
    """
    Deterministic base score [0.0, 1.0].
    Higher = more interesting setup. NEVER adaptive to recent performance.

    Components:
      - Setup proximity (0.40 weight): how close to a trade trigger
      - Volatility quality (0.25 weight): ATR in the sweet spot
      - Volume quality (0.20 weight): above-average volume
      - RSI positioning (0.15 weight): away from extremes = more setup potential
    """
    range_size = max(resistance - support, 1.0)

    # Proximity score: LTP near resistance (breakout) or near support (bounce)
    dist_from_res = max(resistance - ltp, 0.0) / range_size
    dist_from_sup = max(ltp - support, 0.0) / range_size
    proximity = 1.0 - min(min(dist_from_res, dist_from_sup) * 2.5, 1.0)

    # Volatility quality: prefer ATR% in 1.0-3.5% range
    if 1.0 <= atr_pct <= 3.5:
        vol_qual = 1.0
    elif atr_pct < 1.0:
        vol_qual = atr_pct / 1.0
    else:
        vol_qual = max(0.0, 1.0 - (atr_pct - 3.5) / 4.5)

    # Volume quality: prefer vol_ratio 1.2-3.0
    if vol_ratio < 1.0:
        vol_score = vol_ratio / 1.0 * 0.5
    elif vol_ratio <= 3.0:
        vol_score = 0.5 + (vol_ratio - 1.0) / 4.0
    else:
        vol_score = 1.0

    # RSI quality: 35-65 is the sweet spot (away from extremes, more potential)
    if 35.0 <= rsi <= 65.0:
        rsi_score = 1.0
    elif rsi < 35.0:
        rsi_score = 0.7 + (35.0 - rsi) / 35.0 * 0.3  # oversold bonus for bounce
    else:
        rsi_score = max(0.0, 1.0 - (rsi - 65.0) / 35.0)

    score = (
        proximity  * 0.40 +
        vol_qual   * 0.25 +
        vol_score  * 0.20 +
        rsi_score  * 0.15
    )
    return round(min(max(score, 0.0), 1.0), 4)


def _classify_buckets(
    ltp: float, resistance: float, support: float,
    rsi: float, vol_ratio: float, atr14: float,
) -> List[str]:
    """Assign semantic setup bucket tags. A candidate can belong to multiple buckets."""
    buckets: List[str] = []
    range_size = max(resistance - support, 1.0)

    # Breakout proximity: LTP within 2% below resistance
    if resistance > 0 and (resistance - ltp) / resistance <= BREAKOUT_PROXIMITY_PCT:
        buckets.append("breakout")

    # Trend pullback: LTP near support (within 4% above support)
    if support > 0 and (ltp - support) / support <= PULLBACK_PROXIMITY_PCT:
        buckets.append("trend_pullback")

    # Mean reversion bounce: oversold RSI + near support
    if rsi <= OVERSOLD_RSI_MAX and ltp <= support * 1.05:
        buckets.append("mean_reversion")

    # Volume expansion: above-average volume
    if vol_ratio >= VOLUME_EXPANSION_MIN:
        buckets.append("volume_expansion")

    # Squeeze: very tight range (low ATR relative to price level)
    if (resistance - support) / max(ltp, 1) < 0.04:
        buckets.append("squeeze")

    # Relative strength: high RSI + near resistance (momentum continuation)
    if rsi >= 60.0 and (resistance - ltp) / max(resistance, 1) < 0.03:
        buckets.append("relative_strength")

    # High RSI potential short: overbought
    if rsi >= OVERBOUGHT_RSI_MIN:
        buckets.append("overbought_short_watch")

    return buckets if buckets else ["neutral"]


# ── Sector diversification cap ─────────────────────────────────────────────────

def _apply_sector_cap(
    candidates: List[Dict[str, Any]],
    sector_map: Dict[str, str],
    max_total: int,
) -> List[Dict[str, Any]]:
    """
    Select top-scored candidates while enforcing SECTOR_MAX_FRACTION cap.
    Candidates are already sorted by score descending.
    """
    max_per_sector = max(1, int(max_total * SECTOR_MAX_FRACTION))
    sector_counts: Dict[str, int] = {}
    selected: List[Dict[str, Any]] = []

    for c in candidates:
        if len(selected) >= max_total:
            break
        sector = sector_map.get(c["symbol"], "UNKNOWN")
        count  = sector_counts.get(sector, 0)
        if count >= max_per_sector:
            log.debug("[SectorCapApplied] symbol=%s sector=%s count=%d/%d — skipped.",
                      c["symbol"], sector, count + 1, max_per_sector)
            # [Audit 1] per-symbol rejection forensic
            log.info("[FilterStageReject] stage=sector_cap symbol=%s sector=%s"
                     " sector_count=%d max_per_sector=%d score=%.3f",
                     c["symbol"], sector, count + 1, max_per_sector, c.get("score", 0.0))
            continue
        sector_counts[sector] = count + 1
        selected.append(c)

    return selected


# ── Simple regime detection (no external dependency) ─────────────────────────

def _detect_simple_regime(candidates: List[Dict[str, Any]]) -> str:
    """
    Infer broad market regime from the candidate pool RSI distribution.
    This is a rough heuristic — Phase F will overlay the real regime from GlobalDataAI.
    """
    if not candidates:
        return "UNKNOWN"
    rsi_values = [c.get("rsi", 50.0) for c in candidates]
    avg_rsi = sum(rsi_values) / len(rsi_values)
    if avg_rsi >= 60:
        return "BULL_TREND"
    elif avg_rsi <= 40:
        return "BEAR_MARKET"
    else:
        return "RANGE_MARKET"


# ── Technical indicators ─────────────────────────────────────────────────────

def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()
