"""Daily pipeline health check: finds silently broken links and repairs the safe ones.

Several faults in this system stayed invisible for weeks because nothing alerted
on them (a stale price band blocking real orders, price bars arriving a day late,
a learning cohort waiting on data that would never come). This module checks the
data and learning pipeline end to end once per scan, alerts when a problem first
appears (and when it clears), and automatically repairs exactly one class of
problem: missing daily price bars, by re-fetching them through the existing
fetcher. Everything else is reported, never changed.

Read-only apart from that one repair and its own state under data/pipeline_health.
It never touches orders, risk, decisions or learning stores, and never raises.
"""
from __future__ import annotations

import html
import json
import os
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IST = timezone(timedelta(hours=5, minutes=30))
SESSION_FINAL_FROM = time(16, 0)         # daily bars are final from here (see oios fetcher)

COVERAGE_OK = 0.98
COVERAGE_FAIL = 0.90
MAX_REPAIR_SYMBOLS = 600
GATE_WINDOW_DAYS = 3
GATE_MIN_REPEAT = 3
COHORT_WARN_TRADING_DAYS = 3
COHORT_FAIL_TRADING_DAYS = 6
EXIT_WINDOW_DAYS = 3

OK, INFO, WARN, FAIL, ERROR = "OK", "INFO", "WARN", "FAIL", "ERROR"
_SEVERITY = {OK: 0, INFO: 1, WARN: 2, ERROR: 3, FAIL: 4}
_ISSUES = (WARN, FAIL, ERROR)

# (label, path under data/, maximum age in days) for evidence files that should
# keep growing while the system runs.
_FRESHNESS = (
    ("debate_vote_log", "debate/vote_log.jsonl", 5),
    ("execution_conversion_summary", "execution_conversion/daily_summary.jsonl", 5),
    ("rejection_attribution_summary", "rejection_attribution/daily_summary.jsonl", 5),
    ("shadow_selection_log", "logs/final_trading_architecture_shadow_001.jsonl", 4),
    ("shadow_evidence_ledger", "shadow_evidence_ledger.jsonl", 5),
)


def _now() -> datetime:
    return datetime.now(IST)


@dataclass
class HealthContext:
    now: datetime = field(default_factory=_now)
    data_dir: str = os.path.join(ROOT, "data")

    @property
    def market_db(self) -> str:
        return os.path.join(self.data_dir, "market_behavior.db")

    @property
    def ct_db(self) -> str:
        return os.path.join(self.data_dir, "control_tower.db")

    @property
    def out_dir(self) -> str:
        return os.path.join(self.data_dir, "pipeline_health")


def _result(name: str, status: str, detail: str, **metrics: Any) -> Dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "metrics": metrics}


def _trading_day(day: date) -> bool:
    try:
        from config import is_nse_holiday
        return not is_nse_holiday(day)
    except Exception:
        return day.weekday() < 5


def expected_session(now: datetime) -> date:
    """The most recent trading session whose daily bar should already be stored."""
    day = now.date()
    if _trading_day(day) and now.time() >= SESSION_FINAL_FROM:
        return day
    day -= timedelta(days=1)
    while not _trading_day(day):
        day -= timedelta(days=1)
    return day


def _trading_days_between(start: date, end: date) -> int:
    count, day = 0, start
    while day < end:
        day += timedelta(days=1)
        if _trading_day(day):
            count += 1
    return count


def _readonly(path: str) -> sqlite3.Connection:
    uri = f"file:{os.path.abspath(path).replace(os.sep, '/')}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2)


# ── checks ───────────────────────────────────────────────────────────────────

def check_price_freshness(ctx: HealthContext) -> Tuple[Dict[str, Any], List[str]]:
    """Did the active universe receive the latest session's daily bar?"""
    session = expected_session(ctx.now).isoformat()
    if not os.path.exists(ctx.market_db):
        return _result("price_freshness", ERROR, "market database missing"), []
    conn = _readonly(ctx.market_db)
    try:
        active = [r[0] for r in conn.execute(
            "SELECT symbol FROM universe_stocks WHERE is_active = 1")]
        have = {r[0] for r in conn.execute(
            "SELECT symbol FROM ohlcv_daily WHERE trade_date = ?", (session,))}
    finally:
        conn.close()
    if not active:
        return _result("price_freshness", ERROR, "no active universe symbols"), []
    missing = [s for s in active if s not in have]
    coverage = 1.0 - len(missing) / len(active)
    status = OK if coverage >= COVERAGE_OK else WARN if coverage >= COVERAGE_FAIL else FAIL
    detail = (f"{len(active) - len(missing)}/{len(active)} symbols have the {session} bar "
              f"({coverage:.1%})")
    return _result("price_freshness", status, detail, session=session,
                   coverage=round(coverage, 4), missing=len(missing)), missing


def check_universe_learning(ctx: HealthContext) -> Dict[str, Any]:
    """Is the full-universe learning store capturing and resolving cohorts?"""
    base = os.path.join(ctx.data_dir, "universe_selection_learning")
    snapshots = os.path.join(base, "snapshots")
    if not os.path.isdir(snapshots):
        return _result("universe_learning", INFO, "store not started")
    session = expected_session(ctx.now)
    dates = sorted(f[:-5] for f in os.listdir(snapshots) if f.endswith(".json"))
    resolved = {f[:-5] for f in os.listdir(os.path.join(base, "resolved"))
                if f.endswith(".json")} if os.path.isdir(os.path.join(base, "resolved")) else set()
    pending = [d for d in dates if d not in resolved]
    worst_age = max((_trading_days_between(date.fromisoformat(d), session) for d in pending),
                    default=0)
    problems = []
    if session.isoformat() not in dates:
        problems.append(f"no snapshot for {session}")
    status = OK
    if problems:
        status = WARN
    if worst_age >= COHORT_FAIL_TRADING_DAYS:
        status, problems = FAIL, problems + [f"a cohort is unresolved after {worst_age} sessions"]
    elif worst_age >= COHORT_WARN_TRADING_DAYS:
        status = max(status, WARN, key=_SEVERITY.get)
        problems.append(f"a cohort is unresolved after {worst_age} sessions")
    detail = "; ".join(problems) or f"{len(dates)} snapshot(s), {len(pending)} awaiting outcomes"
    return _result("universe_learning", status, detail, snapshots=len(dates),
                   pending=len(pending), oldest_pending_sessions=worst_age)


def check_order_gates(ctx: HealthContext) -> Dict[str, Any]:
    """Is one safety gate repeatedly blocking the same symbol?"""
    if not os.path.exists(ctx.ct_db):
        return _result("order_gates", INFO, "control tower database missing")
    since = (ctx.now - timedelta(days=GATE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    conn = _readonly(ctx.ct_db)
    try:
        rows = conn.execute(
            "SELECT payload FROM ct_events WHERE ts >= ? AND event_type IN "
            "('execution.order.not_placed', 'execution.order.rejected')", (since,)).fetchall()
    finally:
        conn.close()
    repeats: Counter = Counter()
    for (payload,) in rows:
        try:
            data = json.loads(payload) if payload else {}
        except ValueError:
            continue
        reason = str(data.get("reason") or "")
        if reason.startswith("PRICE_INTEGRITY") or reason == "INSUFFICIENT_REAL_MARGIN":
            repeats[(reason, data.get("symbol") or "?")] += 1
    flagged = [(k, n) for k, n in repeats.items() if n >= GATE_MIN_REPEAT]
    if not flagged:
        return _result("order_gates", OK, f"no gate repeatedly blocking one symbol ({len(rows)} blocks)")
    flagged.sort(key=lambda item: -item[1])
    detail = "; ".join(f"{reason} x{n} on {symbol}" for (reason, symbol), n in flagged[:5])
    return _result("order_gates", WARN, detail, flagged=len(flagged))


def check_price_bands(ctx: HealthContext) -> Dict[str, Any]:
    """Which hand-maintained bands no longer match the market? Informational.

    Stale bands no longer block orders (recent history overrides them), so this
    only lists the table entries that need maintenance.
    """
    try:
        from data_integrity import instrument_registry
        bands = dict(instrument_registry._BANDS)
    except Exception as exc:
        return _result("price_bands", ERROR, f"registry unavailable: {exc}")
    if not os.path.exists(ctx.market_db):
        return _result("price_bands", INFO, "market database missing")
    conn = _readonly(ctx.market_db)
    stale: List[str] = []
    try:
        for symbol, (low, high) in bands.items():
            row = conn.execute("SELECT close FROM ohlcv_daily WHERE symbol = ? "
                               "ORDER BY trade_date DESC LIMIT 1", (f"{symbol}.NS",)).fetchone()
            if row and not low <= row[0] <= high:
                stale.append(symbol)
    finally:
        conn.close()
    if stale:
        return _result("price_bands", INFO,
                       f"{len(stale)} static band(s) are stale (recent history overrides them): "
                       f"{', '.join(sorted(stale)[:10])}", stale=len(stale))
    return _result("price_bands", OK, "all static bands match the market")


def check_exit_prices(ctx: HealthContext) -> Dict[str, Any]:
    """Was any recent exit booked at a price the market never traded?"""
    journal = os.path.join(ctx.data_dir, "live", "live_orders.jsonl")
    if not os.path.exists(journal):
        return _result("exit_prices", INFO, "no live order journal")
    from data_integrity.session_close_reference import is_implausible_price
    since = (ctx.now - timedelta(days=EXIT_WINDOW_DAYS)).strftime("%Y-%m-%d")
    suspect: List[str] = []
    checked = 0
    with open(journal, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("event") != "CLOSE" or str(row.get("timestamp", ""))[:10] < since:
                continue
            checked += 1
            try:
                price, day = float(row["exit_price"]), str(row["timestamp"])[:10]
            except (KeyError, TypeError, ValueError):
                continue
            if is_implausible_price(row.get("symbol", ""), price, today=day,
                                    db_path=Path(ctx.market_db)):
                suspect.append(f"{row.get('symbol')} @ {price:g} ({day})")
    if suspect:
        return _result("exit_prices", FAIL, "implausible exit price: " + "; ".join(suspect[:5]),
                       suspect=len(suspect), checked=checked)
    return _result("exit_prices", OK, f"{checked} recent exit(s) within the market's range")


def published_session(now: datetime) -> date:
    """Latest trading session whose end-of-day files (bhav copy, bulk/block deals) NSE has
    published: they appear in the evening, so a session counts once 21:00 IST has passed."""
    day = now.date()
    while True:
        if _trading_day(day) and now >= datetime.combine(day, time(21, 0), tzinfo=IST):
            return day
        day -= timedelta(days=1)


def check_event_data(ctx: HealthContext) -> Dict[str, Any]:
    """Are announcements, bhav copies and bulk/block deals actually being stored?

    These tables sat empty because their loaders were never wired or were broken
    (wrong URL, unparsable headers), with no signal anywhere. Absence is the failure here.
    """
    if not os.path.exists(ctx.market_db):
        return _result("event_data", INFO, "market database not present")
    announced = expected_session(ctx.now).isoformat()
    published = published_session(ctx.now).isoformat()
    try:
        with closing(_readonly(ctx.market_db)) as conn:
            counts = {
                "announcements": conn.execute(
                    "SELECT COUNT(*) FROM daily_events WHERE event_date = ?", (announced,)
                ).fetchone()[0],
                "bhav_rows": conn.execute(
                    "SELECT COUNT(*) FROM bhav_daily WHERE trade_date = ?", (published,)
                ).fetchone()[0],
                "bulk_block_deals": conn.execute(
                    "SELECT COUNT(*) FROM bulk_block_deals WHERE trade_date = ?", (published,)
                ).fetchone()[0],
            }
    except sqlite3.Error as exc:
        return _result("event_data", ERROR, f"could not read event tables: {exc}")
    missing = []
    if not counts["announcements"]:
        missing.append(f"no announcements stored for {announced}")
    if not counts["bhav_rows"]:
        missing.append(f"no bhav copy stored for {published}")
    if not counts["bulk_block_deals"]:
        missing.append(f"no bulk/block deals stored for {published}")
    if missing:
        return _result("event_data", WARN, "; ".join(missing), **counts)
    return _result("event_data", OK, (
        f"{counts['announcements']} announcements ({announced}), {counts['bhav_rows']} bhav rows "
        f"and {counts['bulk_block_deals']} bulk/block deals ({published})"), **counts)


def check_stores(ctx: HealthContext) -> Dict[str, Any]:
    """Has EOD completed for the last session, and are the evidence files still growing?"""
    session = expected_session(ctx.now).isoformat()
    problems: List[str] = []
    status_path = os.path.join(ctx.data_dir, "eod_status.json")
    try:
        with open(status_path, "r", encoding="utf-8") as handle:
            eod = json.load(handle)
        if eod.get("last_eod_date", "") < session or eod.get("status") != "COMPLETED":
            problems.append(f"EOD not completed for {session} "
                            f"(last {eod.get('last_eod_date')} {eod.get('status')})")
    except (OSError, ValueError):
        problems.append("EOD status unreadable")
    fail = bool(problems)
    stale = []
    for label, relative, max_age in _FRESHNESS:
        path = os.path.join(ctx.data_dir, relative)
        if not os.path.exists(path):
            stale.append(f"{label} missing")
            continue
        age = (ctx.now - datetime.fromtimestamp(os.path.getmtime(path), IST)).days
        if age > max_age:
            stale.append(f"{label} not updated for {age}d")
    problems += stale
    if not problems:
        return _result("learning_stores", OK, "EOD completed and evidence files are current")
    return _result("learning_stores", FAIL if fail else WARN, "; ".join(problems),
                   stale=len(stale))


# ── repair ───────────────────────────────────────────────────────────────────

def _default_price_repair(symbols: List[str], today: str) -> int:
    from contextlib import closing
    from oios.data.ohlcv_fetcher import run_daily_fetch
    from oios.db.connection import get_connection
    with closing(get_connection()) as conn:
        result = run_daily_fetch(conn, symbols, today, lookback_days=10,
                                 inter_symbol_delay_s=0.1)
    return result.rows_inserted


# ── orchestration ────────────────────────────────────────────────────────────

def _safe(name: str, check: Callable[[], Any]) -> Any:
    try:
        return check()
    except Exception as exc:
        log.warning("[PipelineHealth] %s check failed: %s", name, exc, exc_info=True)
        return _result(name, ERROR, f"check raised {type(exc).__name__}: {exc}")


def _load_state(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return dict(json.load(handle))
    except (OSError, ValueError):
        return {}


def _write(path: str, content: str, append: bool = False) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if append:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(content)
        return
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(temp, path)


def _alert(notifier: Any, new: Dict[str, Dict[str, Any]], recovered: List[str]) -> None:
    lines = ["🩺 <b>Pipeline health</b>"]
    for name, result in new.items():
        lines.append(f"• <b>{html.escape(name)}</b> [{result['status']}]: {html.escape(result['detail'])}")
    if recovered:
        lines.append("✅ Recovered: " + ", ".join(html.escape(n) for n in recovered))
    if notifier is None:
        from notifications.notifier_manager import get_notifier
        notifier = get_notifier()
    notifier.send_alert("\n".join(lines))


def run_pipeline_health_check(
    repair: bool = True,
    ctx: Optional[HealthContext] = None,
    repair_fn: Optional[Callable[[List[str], str], int]] = None,
    notifier: Any = None,
) -> Dict[str, Any]:
    """Run every check, repair missing price bars, alert on change. Never raises."""
    try:
        ctx = ctx or HealthContext()
        results: List[Dict[str, Any]] = []
        repaired = 0

        outcome = _safe("price_freshness", lambda: check_price_freshness(ctx))
        if isinstance(outcome, tuple):
            freshness, missing = outcome
            if repair and freshness["status"] in (WARN, FAIL) and missing:
                batch = missing[:MAX_REPAIR_SYMBOLS]
                before = freshness["metrics"].get("coverage")
                try:
                    repaired = (repair_fn or _default_price_repair)(batch, ctx.now.date().isoformat())
                except Exception as exc:
                    log.warning("[PipelineHealth] price repair failed: %s", exc)
                    freshness["detail"] += f" (repair failed: {type(exc).__name__})"
                else:
                    after = _safe("price_freshness", lambda: check_price_freshness(ctx))
                    if isinstance(after, tuple):
                        freshness = after[0]
                        freshness["detail"] += (f" (repair attempted for {len(batch)}; "
                                                f"coverage was {before:.1%})")
            results.append(freshness)
        else:
            results.append(outcome)

        for name, check in (("universe_learning", check_universe_learning),
                            ("order_gates", check_order_gates),
                            ("price_bands", check_price_bands),
                            ("exit_prices", check_exit_prices),
                            ("event_data", check_event_data),
                            ("learning_stores", check_stores)):
            results.append(_safe(name, lambda check=check: check(ctx)))

        overall = max((r["status"] for r in results), key=_SEVERITY.get)
        issues = {r["name"]: r for r in results if r["status"] in _ISSUES}
        previous = _load_state(os.path.join(ctx.out_dir, "state.json"))
        new = {n: r for n, r in issues.items() if previous.get(n) != r["status"]}
        recovered = [n for n in previous if n not in issues]
        if new or recovered:
            try:
                _alert(notifier, new, recovered)
            except Exception as exc:
                log.warning("[PipelineHealth] alert failed: %s", exc)
        summary = {
            "checked_at": ctx.now.isoformat(), "overall": overall,
            "issues": sorted(issues), "repaired_rows": repaired, "results": results,
        }
        try:
            _write(os.path.join(ctx.out_dir, "state.json"),
                   json.dumps({n: r["status"] for n, r in issues.items()}))
            _write(os.path.join(ctx.out_dir, "history.jsonl"), json.dumps(summary) + "\n", append=True)
        except OSError as exc:
            log.warning("[PipelineHealth] could not persist state: %s", exc)
        return summary
    except Exception as exc:
        log.warning("[PipelineHealth] run failed: %s", exc, exc_info=True)
        return {"overall": ERROR, "issues": [], "error": str(exc), "results": []}


def get_latest_health(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Most recent summary, or an empty dict when none exists."""
    path = os.path.join(data_dir or os.path.join(ROOT, "data"), "pipeline_health", "history.jsonl")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        return json.loads(lines[-1]) if lines else {}
    except (OSError, ValueError):
        return {}
