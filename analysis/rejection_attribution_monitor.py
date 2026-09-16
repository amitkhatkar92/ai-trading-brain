"""
analysis/rejection_attribution_monitor.py
=============================================
Self-Learning Ecosystem — Phase 4: persistent rejection-attribution monitor.

Turns the existing, live-wired-but-never-completed RejectionTracker
ACQUISITION step into a standing agent, closing the same kind of "computed
but functionally a no-op" gap found in Phase 3 (PGA Category C).

Since DTA-ATTRIBUTION-TRAIL-001, every real rejection at 4 wiring points
(CapitalRiskEngine x2, StrategyLab, RiskControl PositionAllocator/StressTest)
already calls RejectionTracker.ingest_rejection() and persists to
data/rejection_audit.db. But RejectionTracker.update_price_follow() -- the
step that resolves a PENDING row into CORRECT_REJECTION/FALSE_REJECTION by
fetching real follow-through prices -- was never called from anywhere in
production. Every real rejection therefore sat PENDING forever, and
accuracy_by_reason()/missed_winner_analysis() only ever had zero classified
real rows to work with.

KBL stages:
  ACQUISITION  (already exists, no change): ingest_rejection() at the 4 live
               wiring points.
  VALIDATION   (NEW): resolve PENDING rows >= MATURITY_DAYS old using real
               yfinance OHLCV close prices (T+1/T+3/T+5), via
               update_price_follow() (already existed, never called).
  SYNTHESIS    (NEW): accuracy_by_reason() on real classified rows, gated on
               MIN_SAMPLES_FOR_RELIABILITY per reason before being considered
               "reliable" (reuses this repo's MIN_SAMPLE=10 convention from
               learning_system/strategy_performance_tracker.py).
  PROPAGATION  (NEW): get_reason_reliability() read-only accessor + an
               append-only daily JSONL summary.
  GOVERNANCE   : advisory-only. NOT wired into any live risk/decision gate in
               this phase. Pure observability -- this repo's own earlier,
               explicitly-flagged finding (MAX_POSITIONS_CAP's 48% "accuracy"
               claim was SYNTHETIC-data-only, never verified against real
               outcomes) is exactly why a real per-reason reliability figure
               needs its own dedicated evidence before any future phase lets
               anything downstream act on it.

Root-cause fix applied (2026-09-14): analysis/rejection_audit.py's
seed_synthetic_data() previously passed is_backfill=False for its
SYNTHETIC seed rows, which would have made that column unable to
distinguish synthetic from real data if that CLI tool were ever run
against the production db path. Fixed at the source to is_backfill=True
(matching the established convention in trade_quality_tracker.py's
backfill_from_paper_trades()). This monitor now filters out
is_backfill=1 rows from both the reliability summary and
get_reason_reliability() so synthetic/backfilled evidence can never
contaminate a real per-reason reliability figure.

Safety contract: read-only w.r.t. price data (yfinance). Writes only to the
existing data/rejection_audit.db schema (no changes) and a new, append-only
data/rejection_attribution/daily_summary.jsonl. Zero imports from
execution_engine, order_manager, broker APIs, or any live decision path.
Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from analysis.rejection_classifier import accuracy_by_reason, compute_accuracy_stats
from analysis.rejection_tracker import RejectionTracker, get_rejection_tracker
from utils import get_logger

log = get_logger(__name__)

# ── Tuning ──────────────────────────────────────────────────────────────────
MATURITY_DAYS               = 7     # calendar days after trade_date before resolving
MIN_SAMPLES_FOR_RELIABILITY = 10    # mirrors StrategyPerformanceTracker.MIN_SAMPLE

_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_DIR   = os.path.join(_ROOT, "data", "rejection_attribution")
SUMMARY_FILE  = os.path.join(SUMMARY_DIR, "daily_summary.jsonl")


def _fetch_ohlcv_closes(symbol: str, trade_date: str, horizon_days: int = 5) -> List[float]:
    """
    Fetch T+1..T+horizon_days daily close prices from yfinance.
    Mirrors the tested pattern already used by
    opportunity_engine/klp_outcome_engine.py::_fetch_ohlcv_yfinance().
    Returns [] on any error or missing data.
    """
    try:
        import yfinance as yf
        from data_feeds.yahoo_feed import GLOBAL_SYMBOL_MAP

        start_dt = date.fromisoformat(trade_date) + timedelta(days=1)
        end_dt   = start_dt + timedelta(days=horizon_days * 3)  # buffer for weekends/holidays

        ticker_sym = GLOBAL_SYMBOL_MAP.get(symbol.upper()) or f"{symbol}.NS"

        df = yf.download(
            ticker_sym,
            start=str(start_dt),
            end=str(end_dt),
            interval="1d",
            progress=False,
            auto_adjust=True,
            timeout=10,
        )
        if df is None or df.empty:
            return []

        import pandas as pd
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.droplevel(level=-1)
            df = df.loc[:, ~df.columns.duplicated()]

        closes: List[float] = []
        for _, row in df.iterrows():
            try:
                closes.append(float(row["Close"]))
            except (KeyError, TypeError, ValueError):
                continue
        return closes[:horizon_days]
    except Exception:
        return []


class RejectionAttributionMonitor:
    """Standing agent: resolves PENDING rejections, reports per-reason reliability."""

    def __init__(self, tracker: Optional[RejectionTracker] = None) -> None:
        self._tracker = tracker or get_rejection_tracker()

    def run_daily_cycle(self, max_items: int = 200) -> Dict[str, Any]:
        """Run one resolution + reliability-reporting pass. Never raises.

        max_items bounds how many mature rows are network-fetched in a
        single call -- prevents a large backlog from making one EOD run
        balloon in duration. Rows beyond the cap stay PENDING for the
        next run.
        """
        try:
            return self._run_impl(max_items)
        except Exception as exc:
            log.debug("[RejectionAttributionMonitor] cycle error: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def _run_impl(self, max_items: int = 200) -> Dict[str, Any]:
        today = date.today()
        resolved = 0
        skipped_immature = 0
        skipped_no_data = 0
        capped = False

        for row in self._tracker.get_pending():
            try:
                trade_date = date.fromisoformat(row["trade_date"])
            except (ValueError, TypeError):
                skipped_no_data += 1
                continue

            if (today - trade_date).days < MATURITY_DAYS:
                skipped_immature += 1
                continue

            if resolved + skipped_no_data >= max_items:
                capped = True
                break

            closes = _fetch_ohlcv_closes(row["symbol"], row["trade_date"])
            if len(closes) < 5:
                skipped_no_data += 1
                continue

            ok = self._tracker.update_price_follow(
                row["id"], price_1d=closes[0], price_3d=closes[2], price_5d=closes[4],
            )
            if ok:
                resolved += 1

        reliability = self._compute_reliability_summary()
        self._write_daily_summary(resolved, skipped_immature, skipped_no_data, reliability)

        return {
            "status":            "OK",
            "resolved":          resolved,
            "skipped_immature":  skipped_immature,
            "skipped_no_data":   skipped_no_data,
            "capped":            capped,
            "pending_remaining": len(self._tracker.get_pending()),
            **reliability,
        }

    def _compute_reliability_summary(self) -> Dict[str, Any]:
        classified = [r for r in self._tracker.get_classified() if not r.get("is_backfill")]
        by_reason = accuracy_by_reason(classified)
        reliable = {
            reason: stats for reason, stats in by_reason.items()
            if stats.get("classified", 0) >= MIN_SAMPLES_FOR_RELIABILITY
        }
        return {
            "classified_total":       len(classified),
            "reasons_with_min_sample": sorted(reliable.keys()),
            "reliability":            reliable,
        }

    def get_reason_reliability(
        self, reason: str, min_samples: int = MIN_SAMPLES_FOR_RELIABILITY,
    ) -> Optional[Dict[str, Any]]:
        """
        Read-only accessor for a future consumer. Returns None until `reason`
        has >= min_samples classified (non-PENDING, non-backfill) rejections.
        Advisory only -- not wired into any live risk/decision gate in this
        phase.
        """
        try:
            recs = [
                r for r in self._tracker.get_all()
                if r.get("rejected_reason") == reason and not r.get("is_backfill")
            ]
            stats = compute_accuracy_stats(recs)
            if stats["classified"] < min_samples:
                return None
            return stats
        except Exception:
            return None

    def _write_daily_summary(
        self, resolved: int, skipped_immature: int, skipped_no_data: int,
        reliability: Dict[str, Any],
    ) -> None:
        try:
            os.makedirs(SUMMARY_DIR, exist_ok=True)
            record = {
                "date":              date.today().isoformat(),
                "resolved_today":    resolved,
                "skipped_immature":  skipped_immature,
                "skipped_no_data":   skipped_no_data,
                **reliability,
            }
            with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            log.debug("[RejectionAttributionMonitor] summary write skipped: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_monitor: Optional[RejectionAttributionMonitor] = None


def get_rejection_attribution_monitor() -> RejectionAttributionMonitor:
    global _monitor
    if _monitor is None:
        _monitor = RejectionAttributionMonitor()
    return _monitor


def run_daily_rejection_attribution() -> Dict[str, Any]:
    """Convenience entrypoint for master_orchestrator's EOD stage. Never raises."""
    try:
        return get_rejection_attribution_monitor().run_daily_cycle()
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}
