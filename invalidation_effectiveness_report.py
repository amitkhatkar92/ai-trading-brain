"""
Invalidation Effectiveness Report — on-demand multi-session reporter
=====================================================================
Run inside the container to get a full picture of invalidation intelligence
across all persisted sessions.

Usage (from VPS):
  docker exec ai-trading-brain python3 /tmp/invalidation_effectiveness_report.py

Data sources (in priority order):
  1. data/invalidation_state.json  — persistent multi-session state
  2. data/daily_candidates.json    — current store (lifecycle cross-reference)
  3. logs/YYYY-MM-DD.log           — today's session log (intraday events)

Output:
  Section 1 — Genuine invalidations (feed=LIVE) with recovery status
  Section 2 — Feed-induced invalidations (SYNTHETIC/FALLBACK/STALE)
  Section 3 — Top recurring symbols (all-time)
  Section 4 — Recovery rate (recovered / still_invalid / removed / active)
  Section 5 — Session summary counts
  Section 6 — Intraday log events (today's log file, if available)
"""

from __future__ import annotations

import json
import re
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, "/app")

ROOT       = Path("/app")
STATE_FILE = ROOT / "data" / "invalidation_state.json"
STORE_FILE = ROOT / "data" / "daily_candidates.json"
LOG_DIR    = ROOT / "logs"

SEP  = "═" * 72
SEP2 = "─" * 72

NOW_IST = datetime.now(timezone(timedelta(hours=5, minutes=30)))
TODAY   = NOW_IST.strftime("%Y-%m-%d")

# Feed classifications from tracker
FEED_LIVE      = "LIVE"
FEED_FALLBACK  = "FALLBACK"
FEED_SYNTHETIC = "SYNTHETIC"
FEED_STALE     = "STALE"


# ─── Data loaders ─────────────────────────────────────────────────────────────

def load_state() -> Dict[str, Dict[str, Any]]:
    if not STATE_FILE.exists():
        return {}
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as e:
        print(f"  [WARN] Could not load invalidation_state.json: {e}")
        return {}


def load_store() -> Dict[str, str]:
    """Returns symbol → lifecycle_state mapping."""
    if not STORE_FILE.exists():
        return {}
    try:
        raw = json.loads(STORE_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return {
                c["symbol"]: c.get("lifecycle_state", "ACTIVE")
                for c in raw
                if isinstance(c, dict) and c.get("symbol")
            }
    except Exception as e:
        print(f"  [WARN] Could not load daily_candidates.json: {e}")
    return {}


def load_today_log_events(days: int = 5) -> Dict[str, List[str]]:
    """
    Read up to `days` recent log files and extract invalidation-related lines.
    Returns a dict keyed by log tag.
    """
    events: Dict[str, List[str]] = defaultdict(list)
    tags = [
        "InvalidationPersistence",
        "InvalidationRecovery",
        "InvalidationFeedSource",
        "RepeatedInvalidation",
        "InvalidationRepeatFire",
        "BreakoutInvalidation",
        "InvalidationEffectivenessReport",
    ]
    tag_pattern = re.compile(r"\[(" + "|".join(tags) + r")\](.+)")

    for d in range(days):
        date_str = (NOW_IST - timedelta(days=d)).strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"{date_str}.log"
        if not log_file.exists():
            continue
        try:
            for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
                m = tag_pattern.search(line)
                if m:
                    events[m.group(1)].append(f"[{date_str}] {m.group(2).strip()}")
        except Exception as e:
            print(f"  [WARN] Could not read {log_file}: {e}")

    return dict(events)


# ─── Report builder ───────────────────────────────────────────────────────────

def build_report(
    state: Dict[str, Dict[str, Any]],
    store_lc: Dict[str, str],
    log_events: Dict[str, List[str]],
) -> None:

    ever_invalidated: Set[str] = set(state.keys())

    # Classify outcomes
    genuine_list:      List[Dict] = []
    feed_induced_list: List[Dict] = []

    # Infer recovered from log events (InvalidationRecovery lines)
    recovered_from_logs: Set[str] = set()
    for line in log_events.get("InvalidationRecovery", []):
        # pattern: "symbol=XXXXX  prior_reason=..."
        m = re.search(r"symbol=(\S+)", line)
        if m:
            recovered_from_logs.add(m.group(1).strip())

    for sym, rec in state.items():
        g  = rec.get("genuine_count", 0)
        fi = rec.get("feed_induced_count", 0)
        lc = store_lc.get(sym)

        if lc is None:
            outcome = "REMOVED"
        elif lc == "INVALIDATED":
            outcome = "STILL_INVALID"
        elif sym in recovered_from_logs:
            outcome = "RECOVERED"
        else:
            outcome = "ACTIVE_IN_STORE"

        entry = {
            "symbol":  sym,
            "reason":  rec.get("invalidation_reason", ""),
            "feed":    rec.get("feed_classification", ""),
            "source":  rec.get("last_feed_source", ""),
            "total":   rec.get("invalidation_count", 0),
            "g":       g,
            "fi":      fi,
            "rt":      rec.get("recurrence_type", ""),
            "first":   rec.get("first_invalidated_at", "")[:19],
            "last":    rec.get("last_invalidated_at", "")[:19],
            "ltp":     rec.get("last_live_ltp", 0.0),
            "base":    rec.get("last_base_ltp", 0.0),
            "outcome": outcome,
        }

        if g > 0:
            genuine_list.append(entry)
        if fi > 0:
            feed_induced_list.append(entry)

    genuine_list.sort(key=lambda x: -x["g"])
    feed_induced_list.sort(key=lambda x: -x["fi"])
    top_recurring = sorted(state.items(), key=lambda x: -x[1].get("invalidation_count", 0))

    # Recovery rate buckets
    n_recovered     = len({s for s in ever_invalidated if s in recovered_from_logs})
    n_still_invalid = len({s for s in ever_invalidated if store_lc.get(s) == "INVALIDATED"})
    n_removed       = len({s for s in ever_invalidated if s not in store_lc})
    n_active        = len({
        s for s in ever_invalidated
        if s in store_lc and store_lc[s] not in ("INVALIDATED", "EXPIRED")
    })
    total_sym      = max(len(ever_invalidated), 1)
    total_events   = sum(v.get("invalidation_count", 0) for v in state.values())
    total_genuine  = sum(v.get("genuine_count", 0) for v in state.values())
    total_fi       = sum(v.get("feed_induced_count", 0) for v in state.values())
    total_repeats  = sum(
        v.get("invalidation_count", 0) - 1
        for v in state.values()
        if v.get("invalidation_count", 0) > 1
    )

    # ── Print ──────────────────────────────────────────────────────────────────
    print()
    print(SEP)
    print(f"  INVALIDATION EFFECTIVENESS REPORT  —  {TODAY}  (IST {NOW_IST.strftime('%H:%M')})")
    print(f"  State file: {STATE_FILE}")
    print(f"  Store file: {STORE_FILE}")
    print(SEP)
    print(f"  Unique symbols ever invalidated  : {len(ever_invalidated)}")
    print(f"  Total invalidation events        : {total_events}")
    print(f"  Genuine (LIVE feed)              : {total_genuine}")
    print(f"  Feed-induced (SYNTHETIC/FALLBACK): {total_fi}")
    print(f"  Repeated fires (excess)          : {total_repeats}")
    print()

    # ── Section 1: Genuine ────────────────────────────────────────────────────
    print(SEP2)
    print(f"  [1/5]  GENUINE INVALIDATIONS  ({len(genuine_list)} symbol(s))")
    print(SEP2)
    if genuine_list:
        print(f"  {'Symbol':<16}  {'Fires':>5}  {'Feed':<5}  {'Outcome':<14}  {'Reason'}")
        print(f"  {'-'*16}  {'-'*5}  {'-'*5}  {'-'*14}  {'-'*52}")
        for g in genuine_list:
            print(
                f"  {g['symbol']:<16}  {g['g']:>5}  {g['feed']:<5}  {g['outcome']:<14}"
                f"  {g['reason'][:52]}"
            )
            print(f"  {'':16}  LTP={g['ltp']:.2f}  base={g['base']:.2f}"
                  f"  first={g['first']}  last={g['last']}")
    else:
        print("  (none — no LIVE-feed invalidations recorded)")
    print()

    # ── Section 2: Feed-induced ───────────────────────────────────────────────
    print(SEP2)
    print(f"  [2/5]  FEED-INDUCED INVALIDATIONS  ({len(feed_induced_list)} symbol(s))")
    print(SEP2)
    if feed_induced_list:
        print(f"  {'Symbol':<16}  {'Count':>5}  {'Class':<10}  {'Src':<6}  {'Recurrence':<14}  First")
        print(f"  {'-'*16}  {'-'*5}  {'-'*10}  {'-'*6}  {'-'*14}  {'-'*19}")
        for fi in feed_induced_list:
            print(
                f"  {fi['symbol']:<16}  {fi['fi']:>5}  {fi['feed']:<10}"
                f"  {fi['source']:<6}  {fi['rt']:<14}  {fi['first']}"
            )
    else:
        print("  (none — feed quality was clean across all persisted sessions)")
    print()

    # ── Section 3: Top recurring ──────────────────────────────────────────────
    print(SEP2)
    print("  [3/5]  TOP RECURRING SYMBOLS  (all-time, top 10)")
    print(SEP2)
    print(f"  {'Symbol':<16}  {'Total':>5}  {'Genuine':>7}  {'FeedInd':>7}  {'RecurrType':<14}  Last reason")
    print(f"  {'-'*16}  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*14}  {'-'*40}")
    for sym, rec in top_recurring[:10]:
        print(
            f"  {sym:<16}  {rec.get('invalidation_count',0):>5}"
            f"  {rec.get('genuine_count',0):>7}  {rec.get('feed_induced_count',0):>7}"
            f"  {rec.get('recurrence_type',''):>14}  {rec.get('invalidation_reason','')[:40]}"
        )
    print()

    # ── Section 4: Recovery rate ──────────────────────────────────────────────
    print(SEP2)
    print(f"  [4/5]  RECOVERY RATE")
    print(SEP2)
    print(f"  RECOVERED      : {n_recovered:>3}  ({100*n_recovered/total_sym:>4.0f}%)")
    print(f"  STILL_INVALID  : {n_still_invalid:>3}  ({100*n_still_invalid/total_sym:>4.0f}%)")
    print(f"  REMOVED        : {n_removed:>3}  ({100*n_removed/total_sym:>4.0f}%)  ← not in store")
    print(f"  ACTIVE         : {n_active:>3}  ({100*n_active/total_sym:>4.0f}%)  ← passed in later cycle")
    print()

    for sym in sorted(s for s in ever_invalidated if s in recovered_from_logs):
        print(f"    RECOVERED     : {sym}")
    for sym in sorted(s for s in ever_invalidated if store_lc.get(s) == "INVALIDATED"):
        reason = state.get(sym, {}).get("invalidation_reason", "")[:50]
        print(f"    STILL_INVALID : {sym}  — {reason}")
    for sym in sorted(s for s in ever_invalidated if s not in store_lc):
        print(f"    REMOVED       : {sym}")

    print()

    # ── Section 5: Summary counts ─────────────────────────────────────────────
    print(SEP2)
    print("  [5/5]  SESSION SUMMARY COUNTS")
    print(SEP2)
    print(f"  genuine_invalidations              : {total_genuine}")
    print(f"  feed_induced_invalidations         : {total_fi}")
    print(f"  recovered_candidates               : {n_recovered}")
    print(f"  permanently_removed_candidates     : {n_removed}")
    print(f"  repeated_invalidations (excess)    : {total_repeats}")
    print()

    # ── Section 6: Today's intraday log events ────────────────────────────────
    print(SEP2)
    print("  [6/6]  INTRADAY LOG EVENTS  (last 5 days)")
    print(SEP2)

    for tag in [
        "InvalidationPersistence",
        "InvalidationRecovery",
        "InvalidationRepeatFire",
        "RepeatedInvalidation",
        "BreakoutInvalidation",
    ]:
        lines = log_events.get(tag, [])
        if lines:
            print(f"\n  [{tag}]  ({len(lines)} events)")
            for line in lines[-15:]:   # cap at last 15 per tag to avoid wall-of-text
                print(f"    {line}")

    if not any(log_events.get(t) for t in [
        "InvalidationPersistence", "InvalidationRecovery",
        "InvalidationRepeatFire", "RepeatedInvalidation", "BreakoutInvalidation",
    ]):
        print("  (no log events found — tracker may not have fired yet today)")

    print()
    print(SEP)
    print(f"  Report complete  {NOW_IST.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print(SEP)
    print()

    # ── Intelligence verdict ───────────────────────────────────────────────────
    if len(ever_invalidated) == 0:
        verdict = "NO DATA — persistence layer has not accumulated events yet."
        quality = "PENDING"
    elif total_genuine >= 3 and total_fi == 0:
        verdict = "HIGH QUALITY — genuine invalidations only; feed quality clean."
        quality = "HIGH"
    elif total_genuine > 0 and total_fi > 0 and total_genuine > total_fi:
        verdict = "MIXED — genuine detections dominant; feed artifacts present but minority."
        quality = "MODERATE"
    elif total_fi > total_genuine:
        verdict = "CONTAMINATED — feed-induced events outnumber genuine detections."
        quality = "LOW"
    elif total_genuine == 0 and total_fi == 0:
        verdict = "NO EVENTS — either market was stable or persistence not yet populated."
        quality = "PENDING"
    else:
        verdict = "BUILDING — insufficient events for full assessment."
        quality = "BUILDING"

    print(f"  INTELLIGENCE QUALITY: {quality}")
    print(f"  Verdict: {verdict}")
    print()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nLoading data...")
    state      = load_state()
    store_lc   = load_store()
    log_events = load_today_log_events(days=5)

    print(f"  invalidation_state.json  : {len(state)} symbol records")
    print(f"  daily_candidates.json    : {len(store_lc)} current candidates")
    print(f"  Log files scanned        : last 5 days under {LOG_DIR}")

    build_report(state, store_lc, log_events)
