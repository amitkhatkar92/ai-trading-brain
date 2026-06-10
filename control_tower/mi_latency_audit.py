"""
MarketIntelligenceLatencyAudit — Control Tower Module 7
========================================================
Passively tracks MarketIntelligence layer latency for every cycle.

How timing is derived (zero modification to SystemMonitor or orchestrator):

  EventBus event sequence each cycle:
    1. global.distortion.detected  ← DISTORTION_DETECTED fires immediately
                                      before the time_layer("MarketIntelligence")
                                      block in the orchestrator.
    2. ... MI layer runs internally ...
    3. market.data.ready           ← MARKET_DATA_READY fires at the end of
                                      _run_market_intelligence(), still inside
                                      the time_layer context.  Delta from (1)
                                      to (3) ≈ SystemMonitor MI latency ±2ms.

Latency buckets:
  NORMAL    <  10,000 ms
  SLOW      10,000 – 14,999 ms
  CRITICAL  >= 15,000 ms  (same threshold as LAYER_LATENCY_CRIT_OVERRIDES)

Persistent storage (appended to control_tower.db):
  mi_latency_records  — one row per cycle
  mi_latency_daily    — upserted daily aggregation

Emits to log:
  [MILatencyRecord]       — after each cycle
  [LatencyHealthSummary]  — on demand via emit_summary() or --summary CLI
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import threading
from datetime import datetime, timedelta
from typing import Optional

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

# ── Thresholds (must match LAYER_LATENCY_CRIT_OVERRIDES in system_monitor) ──
_NORMAL_MS   =  10_000
_SLOW_MS     =  15_000     # WARN zone: 10k–15k
_CRITICAL_MS =  15_000     # CRIT threshold

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "control_tower.db")

_CREATE_RECORDS = """
CREATE TABLE IF NOT EXISTS mi_latency_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    cycle_time      TEXT    NOT NULL,
    mi_latency_ms   REAL    NOT NULL,
    bucket          TEXT    NOT NULL,
    aborted         INTEGER NOT NULL DEFAULT 0,
    regime          TEXT,
    vix             REAL,
    pcr             REAL,
    created_at      TEXT    NOT NULL
);
"""

_CREATE_DAILY = """
CREATE TABLE IF NOT EXISTS mi_latency_daily (
    date              TEXT    PRIMARY KEY,
    total_cycles      INTEGER NOT NULL DEFAULT 0,
    normal_cycles     INTEGER NOT NULL DEFAULT 0,
    slow_cycles       INTEGER NOT NULL DEFAULT 0,
    critical_cycles   INTEGER NOT NULL DEFAULT 0,
    aborted_cycles    INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms    REAL,
    max_latency_ms    REAL,
    p95_latency_ms    REAL,
    last_updated      TEXT
);
"""

_CREATE_RECORDS_IDX = """
CREATE INDEX IF NOT EXISTS mi_latency_records_date
    ON mi_latency_records (date);
"""


def _bucket(ms: float) -> str:
    if ms >= _CRITICAL_MS:
        return "CRITICAL"
    if ms >= _NORMAL_MS:
        return "SLOW"
    return "NORMAL"


class MILatencyAudit:
    """
    Passive EventBus subscriber.  Records MarketIntelligence layer
    latency for every trading cycle and maintains daily aggregates.

    Thread-safe: all state mutations use _state_lock.
    DB writes use a dedicated sqlite connection created on the writer thread.
    """

    _instance: Optional["MILatencyAudit"] = None
    _cls_lock = threading.Lock()

    # ── Singleton ──────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, bus=None) -> "MILatencyAudit":
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    if bus is None:
                        from communication.event_bus import get_bus
                        bus = get_bus()
                    cls._instance = cls(bus)
        return cls._instance

    # ── Init ───────────────────────────────────────────────────────────────

    def __init__(self, bus) -> None:
        self._state_lock = threading.Lock()
        self._mi_start_ts: Optional[datetime] = None    # set by DISTORTION_DETECTED
        self._pending_regime: Optional[str]   = None    # set by MARKET_DATA_READY

        self._db_lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._subscribe(bus)
        log.info("[MILatencyAudit] Initialised. Tracking MarketIntelligence "
                 "latency per cycle.")

    # ── Database ───────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        with self._db_lock:
            c = self._get_conn()
            c.execute(_CREATE_RECORDS)
            c.execute(_CREATE_DAILY)
            c.execute(_CREATE_RECORDS_IDX)
            c.commit()

    # ── EventBus subscriptions ─────────────────────────────────────────────

    def _subscribe(self, bus) -> None:
        bus.subscribe(
            EventType.DISTORTION_DETECTED,
            self._on_distortion,
            agent_name="MILatencyAudit",
        )
        bus.subscribe(
            EventType.MARKET_DATA_READY,
            self._on_data_ready,
            agent_name="MILatencyAudit",
        )

    def _on_distortion(self, event: Event) -> None:
        """
        DISTORTION_DETECTED fires immediately before the MI time_layer starts.
        Record the start timestamp; reset any stale pending state.
        """
        with self._state_lock:
            self._mi_start_ts    = event.timestamp
            self._pending_regime = None

    def _on_data_ready(self, event: Event) -> None:
        """
        MARKET_DATA_READY fires at the end of _run_market_intelligence(),
        still inside the time_layer context — delta from _mi_start_ts
        equals the SystemMonitor-measured MI latency.
        """
        with self._state_lock:
            if self._mi_start_ts is None:
                return   # no start recorded (first cycle, or duplicate event)

            ts_end = event.timestamp
            mi_ms  = (ts_end - self._mi_start_ts).total_seconds() * 1000

            regime = str(event.payload.get("regime", self._pending_regime or ""))
            vix    = float(event.payload.get("vix",  0.0) or 0.0)
            pcr    = float(event.payload.get("pcr",  0.0) or 0.0)

            bucket  = _bucket(mi_ms)
            aborted = int(mi_ms >= _CRITICAL_MS)

            self._mi_start_ts = None   # reset for next cycle

        # DB write outside state lock (can be slow)
        self._write_record(
            cycle_time=ts_end,
            mi_latency_ms=round(mi_ms, 1),
            bucket=bucket,
            aborted=aborted,
            regime=regime,
            vix=vix,
            pcr=pcr,
        )

    # ── Record persistence ─────────────────────────────────────────────────

    def _write_record(
        self,
        cycle_time: datetime,
        mi_latency_ms: float,
        bucket: str,
        aborted: int,
        regime: str,
        vix: float,
        pcr: float,
    ) -> None:
        date = cycle_time.strftime("%Y-%m-%d")
        now  = datetime.now().isoformat()

        log.info(
            "[MILatencyRecord] time=%s mi_ms=%.0f bucket=%s aborted=%s "
            "regime=%s vix=%.1f pcr=%.2f",
            cycle_time.strftime("%H:%M:%S"), mi_latency_ms, bucket,
            bool(aborted), regime, vix, pcr,
        )

        with self._db_lock:
            c = self._get_conn()
            c.execute(
                """INSERT INTO mi_latency_records
                   (date, cycle_time, mi_latency_ms, bucket, aborted,
                    regime, vix, pcr, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (date, cycle_time.isoformat(), mi_latency_ms, bucket,
                 aborted, regime, vix, pcr, now),
            )
            self._upsert_daily(c, date)
            c.commit()

    def _upsert_daily(self, c: sqlite3.Connection, date: str) -> None:
        """Recompute and upsert the daily aggregate for `date`."""
        rows = c.execute(
            """SELECT mi_latency_ms, bucket, aborted
               FROM mi_latency_records WHERE date = ?""",
            (date,),
        ).fetchall()

        if not rows:
            return

        latencies       = [r["mi_latency_ms"] for r in rows]
        total           = len(rows)
        normal_cnt      = sum(1 for r in rows if r["bucket"] == "NORMAL")
        slow_cnt        = sum(1 for r in rows if r["bucket"] == "SLOW")
        critical_cnt    = sum(1 for r in rows if r["bucket"] == "CRITICAL")
        aborted_cnt     = sum(1 for r in rows if r["aborted"])
        avg_ms          = round(statistics.mean(latencies), 1)
        max_ms          = round(max(latencies), 1)
        sorted_lat      = sorted(latencies)
        p95_idx         = max(0, int(len(sorted_lat) * 0.95) - 1)
        p95_ms          = round(sorted_lat[p95_idx], 1)

        c.execute(
            """INSERT INTO mi_latency_daily
               (date, total_cycles, normal_cycles, slow_cycles,
                critical_cycles, aborted_cycles,
                avg_latency_ms, max_latency_ms, p95_latency_ms, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
                 total_cycles    = excluded.total_cycles,
                 normal_cycles   = excluded.normal_cycles,
                 slow_cycles     = excluded.slow_cycles,
                 critical_cycles = excluded.critical_cycles,
                 aborted_cycles  = excluded.aborted_cycles,
                 avg_latency_ms  = excluded.avg_latency_ms,
                 max_latency_ms  = excluded.max_latency_ms,
                 p95_latency_ms  = excluded.p95_latency_ms,
                 last_updated    = excluded.last_updated""",
            (date, total, normal_cnt, slow_cnt, critical_cnt, aborted_cnt,
             avg_ms, max_ms, p95_ms, datetime.now().isoformat()),
        )

    # ── Backfill from ct_events ────────────────────────────────────────────

    def backfill_from_events(self, days: int = 30) -> int:
        """
        Derive historical MI latency from ct_events timestamps.
        Pairs global.distortion.detected (start) with market.data.ready
        (end) on the same cycle_id.  Skips cycles already in mi_latency_records.

        Returns number of records written.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self._db_lock:
            c = self._get_conn()

            # Fetch already-recorded cycle_times (avoid duplicate writes)
            existing = {
                r[0] for r in
                c.execute("SELECT cycle_time FROM mi_latency_records").fetchall()
            }

            rows = c.execute(
                """
                SELECT
                    d.ts        AS start_ts,
                    m.ts        AS end_ts,
                    m.cycle_id  AS cycle_id,
                    m.payload   AS payload
                FROM ct_events d
                JOIN ct_events m
                    ON  m.cycle_id  = d.cycle_id
                    AND m.event_type = 'market.data.ready'
                WHERE d.event_type = 'global.distortion.detected'
                  AND d.ts >= ?
                ORDER BY d.ts
                """,
                (cutoff,),
            ).fetchall()

        written = 0
        for row in rows:
            if row["end_ts"] in existing:
                continue
            try:
                ts_start = datetime.fromisoformat(row["start_ts"])
                ts_end   = datetime.fromisoformat(row["end_ts"])
                mi_ms    = (ts_end - ts_start).total_seconds() * 1000
                payload  = json.loads(row["payload"]) if row["payload"] else {}
                regime   = str(payload.get("regime", ""))
                vix      = float(payload.get("vix",  0.0) or 0.0)
                pcr      = float(payload.get("pcr",  0.0) or 0.0)
                bucket   = _bucket(mi_ms)
                aborted  = int(mi_ms >= _CRITICAL_MS)
                self._write_record(
                    cycle_time=ts_end,
                    mi_latency_ms=round(mi_ms, 1),
                    bucket=bucket,
                    aborted=aborted,
                    regime=regime,
                    vix=vix,
                    pcr=pcr,
                )
                written += 1
            except Exception as exc:
                log.debug("[MILatencyAudit] backfill parse error: %s", exc)

        log.info("[MILatencyAudit] Backfill complete: %d records written.", written)
        return written

    # ── Reporting ──────────────────────────────────────────────────────────

    def emit_summary(self, days: int = 30) -> None:
        """
        Query mi_latency_records and mi_latency_daily for the last `days`
        trading days and emit a [LatencyHealthSummary] log line plus a
        full per-day table.
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        with self._db_lock:
            c = self._get_conn()

            # Per-cycle records
            records = c.execute(
                """SELECT date, cycle_time, mi_latency_ms, bucket, aborted,
                          regime, vix, pcr
                   FROM mi_latency_records
                   WHERE date >= ?
                   ORDER BY cycle_time""",
                (cutoff,),
            ).fetchall()

            # Daily summaries
            daily = c.execute(
                """SELECT date, total_cycles, normal_cycles, slow_cycles,
                          critical_cycles, aborted_cycles,
                          avg_latency_ms, max_latency_ms, p95_latency_ms
                   FROM mi_latency_daily
                   WHERE date >= ?
                   ORDER BY date""",
                (cutoff,),
            ).fetchall()

        if not records:
            log.info("[LatencyHealthSummary] No MI latency records found "
                     "(run backfill_from_events() for historical data).")
            return

        # ── Aggregate across all days in window ───────────────────────
        all_ms     = [r["mi_latency_ms"] for r in records]
        total_cyc  = len(records)
        norm_cyc   = sum(1 for r in records if r["bucket"] == "NORMAL")
        slow_cyc   = sum(1 for r in records if r["bucket"] == "SLOW")
        crit_cyc   = sum(1 for r in records if r["bucket"] == "CRITICAL")
        abort_cyc  = sum(1 for r in records if r["aborted"])
        avg_ms     = round(statistics.mean(all_ms), 0)
        max_ms     = round(max(all_ms), 0)
        sorted_ms  = sorted(all_ms)
        p95_idx    = max(0, int(len(sorted_ms) * 0.95) - 1)
        p95_ms     = round(sorted_ms[p95_idx], 0)
        worst_day  = max(daily, key=lambda d: d["max_latency_ms"] or 0,
                         default=None)
        abort_days = sum(1 for d in daily if (d["aborted_cycles"] or 0) > 0)

        # ── Emit single-line verdict ───────────────────────────────────
        log.info(
            "[LatencyHealthSummary] window=%dd total_cycles=%d "
            "normal=%d slow=%d critical=%d aborted=%d "
            "avg_ms=%.0f max_ms=%.0f p95_ms=%.0f "
            "abort_days=%d worst_day=%s",
            days, total_cyc,
            norm_cyc, slow_cyc, crit_cyc, abort_cyc,
            avg_ms, max_ms, p95_ms,
            abort_days,
            worst_day["date"] if worst_day else "N/A",
        )

        # ── Per-cycle table ───────────────────────────────────────────
        sep  = "=" * 80
        sep2 = "-" * 80
        lines = [
            "",
            sep,
            "MARKETINTELLIGENCE LATENCY AUDIT",
            f"Window: last {days} trading days | "
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sep,
            "",
            "PER-CYCLE RECORDS",
            sep2,
            f"{'Date':<12} {'Time':<10} {'Latency':>10} {'Bucket':<10} "
            f"{'Aborted':<8} {'Regime':<18} {'VIX':>5} {'PCR':>6}",
            sep2,
        ]
        for r in records:
            ct = r["cycle_time"][:19]  # trim microseconds
            time_part = ct[11:19]
            regime = (r["regime"] or "")[:16]
            lines.append(
                f"{r['date']:<12} {time_part:<10} "
                f"{r['mi_latency_ms']:>9.0f}ms "
                f"{r['bucket']:<10} "
                f"{'YES' if r['aborted'] else 'no':<8} "
                f"{regime:<18} "
                f"{(r['vix'] or 0.0):>5.1f} {(r['pcr'] or 0.0):>6.2f}"
            )

        # ── Daily summary table ───────────────────────────────────────
        lines += [
            "",
            "DAILY SUMMARY",
            sep2,
            f"{'Date':<12} {'Total':>6} {'Normal':>7} {'Slow':>6} "
            f"{'Crit':>6} {'Aborted':>8} {'Avg ms':>8} "
            f"{'Max ms':>8} {'P95 ms':>8}",
            sep2,
        ]
        for d in daily:
            marker = " ◀ ABORT DAY" if (d["aborted_cycles"] or 0) > 0 else ""
            lines.append(
                f"{d['date']:<12} {d['total_cycles']:>6} "
                f"{d['normal_cycles']:>7} {d['slow_cycles']:>6} "
                f"{d['critical_cycles']:>6} {d['aborted_cycles']:>8} "
                f"{(d['avg_latency_ms'] or 0):>8.0f} "
                f"{(d['max_latency_ms'] or 0):>8.0f} "
                f"{(d['p95_latency_ms'] or 0):>8.0f}"
                f"{marker}"
            )

        # ── Window aggregate ──────────────────────────────────────────
        lines += [
            sep2,
            f"{'TOTAL':<12} {total_cyc:>6} {norm_cyc:>7} {slow_cyc:>6} "
            f"{crit_cyc:>6} {abort_cyc:>8} {avg_ms:>8.0f} "
            f"{max_ms:>8.0f} {p95_ms:>8.0f}",
            "",
            "VERDICT",
            sep2,
        ]

        # Determine health status
        abort_rate = crit_cyc / total_cyc if total_cyc else 0.0
        if abort_rate == 0 and p95_ms < _NORMAL_MS:
            status = "HEALTHY"
            detail = f"p95={p95_ms:.0f}ms — well within NORMAL bucket"
        elif abort_rate == 0 and p95_ms < _SLOW_MS:
            status = "ACCEPTABLE"
            detail = f"p95={p95_ms:.0f}ms — in SLOW zone but no aborts"
        elif abort_rate < 0.10:
            status = "DEGRADED"
            detail = (f"abort_rate={abort_rate:.1%} — {abort_cyc} CRITICAL "
                      f"cycles across {abort_days} day(s)")
        else:
            status = "FAILING"
            detail = (f"abort_rate={abort_rate:.1%} — threshold miscalibrated "
                      f"for normal API latency profile")

        lines += [
            f"  status         = {status}",
            f"  detail         = {detail}",
            f"  total_cycles   = {total_cyc}",
            f"  normal_pct     = {100 * norm_cyc / total_cyc:.1f}%",
            f"  slow_pct       = {100 * slow_cyc / total_cyc:.1f}%",
            f"  critical_pct   = {100 * crit_cyc / total_cyc:.1f}%",
            f"  abort_days     = {abort_days}",
            f"  avg_latency_ms = {avg_ms:.0f}",
            f"  max_latency_ms = {max_ms:.0f}",
            f"  p95_latency_ms = {p95_ms:.0f}",
            f"  worst_day      = {worst_day['date'] if worst_day else 'N/A'}",
            sep,
            "",
        ]

        output = "\n".join(lines)
        log.info(output)
        return output
