"""
analysis/live_observation_collector.py
=============================================
LIVE_OBSERVATION_FRAMEWORK_001 — Trade enrichment engine.

Reads paper_trades.csv and enriches each trade with:
    - Quality tier (derived from confidence + strategy pattern)
    - SFT class (from phase_d_sft.db via symbol lookup)
    - Regime context (from real VIX + price via yfinance or cached data)
    - Outcome (WIN/LOSS/OPEN based on pnl field)

This module runs in BATCH mode (process all CSV rows not yet in DB)
or can be called per-trade at execution time for real-time ingestion.

The quality scoring here is a SIMPLIFIED model because paper_trades.csv
only carries `confidence` and `rr` — not the full 5-component score.
Once the quality tracker has real data, this mapping can be improved.

SIMPLIFIED QUALITY SCORING
---------------------------
score = confidence × 0.60 + rr_score × 0.40

Where rr_score = min(rr / 3.0, 1.0) × 10

Tier thresholds remain identical to trade_quality_scoring.py:
    PREMIUM ≥ 8.0  |  HIGH ≥ 7.0  |  MEDIUM ≥ 6.0  |  LOW < 6.0
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

PAPER_TRADES_CSV = os.path.join(_ROOT, "data", "paper_trades.csv")
SFT_DB           = os.path.join(_ROOT, "data", "phase_d_sft.db")
REAL_OPTIONS_DB  = os.path.join(_ROOT, "data", "real_options_audit.db")

from analysis.live_observation_tracker import LiveObservationTracker, get_live_tracker


# ── Quality tier derivation ───────────────────────────────────────────────────

def _derive_quality(confidence: float, rr: float) -> tuple:
    """
    Returns (quality_score, quality_tier, is_high_conviction).

    Simplified model — real model requires 5 sub-scores.
    confidence : 0–10 (decision engine confidence)
    rr         : planned risk:reward ratio
    """
    rr_score    = min(rr / 3.0, 1.0) * 10.0   # 0–10
    score       = confidence * 0.60 + rr_score * 0.40
    score       = round(min(score, 10.0), 2)

    if score >= 8.0:
        tier = "PREMIUM"
    elif score >= 7.0:
        tier = "HIGH"
    elif score >= 6.0:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    is_high_conviction = score >= 7.5 and rr >= 2.0
    return score, tier, is_high_conviction


# ── SFT class lookup ──────────────────────────────────────────────────────────

def _sft_for_symbol(symbol: str) -> tuple:
    """
    Look up latest SFT classification for a symbol from phase_d_sft.db.
    Returns (sft_class, sft_score). Falls back to ('UNKNOWN', 0.0).
    """
    if not os.path.exists(SFT_DB):
        return "UNKNOWN", 0.0
    try:
        with sqlite3.connect(SFT_DB) as conn:
            row = conn.execute(
                "SELECT sft_class, sft_score FROM sft_records WHERE symbol=? ORDER BY recorded_at DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return "UNKNOWN", 0.0


# ── Regime context from real options cache ────────────────────────────────────

def _regime_for_date(trade_date: str) -> tuple:
    """
    Look up regime / VIX for a given date from the real options backtest cache.
    Returns (regime, vix, vix_bucket).
    Falls back to ('RANGING', 15.0, 'MEDIUM') if not found.
    """
    default = ("RANGING", 15.0, "MEDIUM")
    if not os.path.exists(REAL_OPTIONS_DB):
        return default
    try:
        with sqlite3.connect(REAL_OPTIONS_DB) as conn:
            row = conn.execute(
                """SELECT regime, vix, vix_bucket
                   FROM real_options_backtest
                   WHERE date=?
                   LIMIT 1""",
                (trade_date,),
            ).fetchone()
        if row:
            return row[0], row[1], row[2]
    except Exception:
        pass
    return default


# ── Live regime via yfinance (for today's trades) ─────────────────────────────

_regime_cache: Dict[str, tuple] = {}


def _current_regime_with_transition() -> tuple:
    """
    Fetch current VIX + regime + transition probability.
    Returns (regime, vix, vix_bucket, transition_prob, transition_alert).
    """
    key = datetime.now().strftime("%Y-%m-%d")
    if key in _regime_cache:
        return _regime_cache[key]

    try:
        from analysis.regime_transition_engine import analyse_regime_transition
        r = analyse_regime_transition("NIFTY", period="3mo", use_cache=True)
        result = (r.current_regime, r.current_vix,
                  ("HIGH" if r.current_vix > 22 else "MEDIUM" if r.current_vix > 14 else "LOW"),
                  r.transition_probability, r.alert_level)
        _regime_cache[key] = result
        return result
    except Exception:
        pass

    return ("RANGING", 15.0, "MEDIUM", 0.0, "STABLE")


def _current_regime() -> tuple:
    """Returns (regime, vix, vix_bucket) only — backward-compatible wrapper."""
    r = _current_regime_with_transition()
    return r[0], r[1], r[2]


# ── Outcome derivation ────────────────────────────────────────────────────────

def _derive_outcome(pnl: Optional[float], exit_price: Optional[float]) -> str:
    if exit_price is None or exit_price == 0:
        return "OPEN"
    if pnl is None:
        return "OPEN"
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "OPEN"


# ── CSV row enrichment ────────────────────────────────────────────────────────

def enrich_csv_row(row: dict) -> dict:
    """
    Given a raw row from paper_trades.csv, return an enriched dict
    ready for LiveObservationTracker.ingest().
    """
    timestamp   = row.get("timestamp", "")
    trade_date  = timestamp[:10] if timestamp else datetime.now().strftime("%Y-%m-%d")

    try:
        confidence = float(row.get("confidence") or 0)
    except (ValueError, TypeError):
        confidence = 0.0

    try:
        rr = float(row.get("rr") or 1.5)
    except (ValueError, TypeError):
        rr = 1.5

    try:
        entry_price = float(row.get("entry_price") or 0)
    except (ValueError, TypeError):
        entry_price = 0.0

    try:
        stop_loss = float(row.get("stop_loss") or 0)
    except (ValueError, TypeError):
        stop_loss = 0.0

    try:
        target = float(row.get("target") or 0)
    except (ValueError, TypeError):
        target = 0.0

    try:
        exit_price = float(row.get("exit_price") or 0) or None
    except (ValueError, TypeError):
        exit_price = None

    try:
        pnl = float(row.get("pnl") or 0) or None
    except (ValueError, TypeError):
        pnl = None

    quality_score, quality_tier, is_hc = _derive_quality(confidence, rr)
    sft_class, sft_score               = _sft_for_symbol(row.get("symbol", ""))
    if trade_date < datetime.now().strftime("%Y-%m-%d"):
        regime, vix, vix_bucket = _regime_for_date(trade_date)
        transition_prob, transition_alert = 0.0, "STABLE"
    else:
        regime, vix, vix_bucket, transition_prob, transition_alert = _current_regime_with_transition()
    outcome                            = _derive_outcome(pnl, exit_price)

    return {
        "order_id":           row.get("order_id", ""),
        "symbol":             row.get("symbol", "UNKNOWN"),
        "strategy":           row.get("strategy", "UNKNOWN"),
        "direction":          row.get("direction", ""),
        "trade_date":         trade_date,
        "entry_price":        entry_price,
        "stop_loss":          stop_loss,
        "target":             target,
        "confidence":         confidence,
        "rr":                 rr,
        "quality_score":      quality_score,
        "quality_tier":       quality_tier,
        "is_high_conviction": is_hc,
        "sft_class":          sft_class,
        "sft_score":          sft_score,
        "market_regime":      regime,
        "vix":                vix,
        "vix_bucket":         vix_bucket,
        "news_type":          "NONE",
        "news_sentiment":     "NEUTRAL",
        "transition_probability": transition_prob,
        "transition_alert":   transition_alert,
        "data_source":        "PAPER",
        "exit_price":         exit_price,
        "pnl":                pnl,
        "outcome":            outcome,
        "close_reason":       row.get("reason", ""),
    }


# ── Batch ingestor ────────────────────────────────────────────────────────────

def ingest_from_csv(
    csv_path: str = PAPER_TRADES_CSV,
    tracker:  Optional[LiveObservationTracker] = None,
) -> dict:
    """
    Read paper_trades.csv and ingest all rows not yet in live_observations.db.
    Returns summary dict with counts.
    """
    tracker = tracker or get_live_tracker()

    if not os.path.exists(csv_path):
        return {"processed": 0, "new": 0, "skipped": 0, "errors": 0, "error_details": []}

    new     = 0
    skipped = 0
    errors  = 0
    error_details = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows   = list(reader)

    for row in rows:
        if not row.get("order_id"):
            skipped += 1
            continue
        try:
            enriched = enrich_csv_row(row)
            row_id   = tracker.ingest(
                order_id           = enriched["order_id"],
                symbol             = enriched["symbol"],
                strategy           = enriched["strategy"],
                direction          = enriched["direction"],
                trade_date         = enriched["trade_date"],
                entry_price        = enriched["entry_price"],
                stop_loss          = enriched["stop_loss"],
                target             = enriched["target"],
                confidence         = enriched["confidence"],
                rr                 = enriched["rr"],
                quality_score      = enriched["quality_score"],
                quality_tier       = enriched["quality_tier"],
                is_high_conviction = enriched["is_high_conviction"],
                sft_class          = enriched["sft_class"],
                sft_score          = enriched["sft_score"],
                market_regime      = enriched["market_regime"],
                vix                = enriched["vix"],
                vix_bucket         = enriched["vix_bucket"],
                news_type          = enriched["news_type"],
                news_sentiment     = enriched["news_sentiment"],
                transition_probability = enriched["transition_probability"],
                transition_alert   = enriched["transition_alert"],
                data_source        = enriched["data_source"],
                notes              = "",
            )
            # Mark outcome if trade is closed
            if enriched["outcome"] != "OPEN" and enriched["exit_price"]:
                tracker.mark_outcome(
                    order_id    = enriched["order_id"],
                    outcome     = enriched["outcome"],
                    exit_price  = enriched["exit_price"] or 0,
                    pnl         = enriched["pnl"] or 0,
                    close_reason= enriched["close_reason"],
                )
            if row_id is not None:
                new += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            error_details.append(f"order_id={row.get('order_id','?')}: {e}")

    return {
        "processed": len(rows),
        "new":       new,
        "skipped":   skipped,
        "errors":    errors,
        "error_details": error_details,
    }
