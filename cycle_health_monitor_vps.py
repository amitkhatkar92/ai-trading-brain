"""
CycleHealthMonitor — Control Tower Module 6
============================================
After every CYCLE_COMPLETE event, performs a 12-point diagnostic and
writes a structured JSON report plus a human-readable summary line.

Reports are stored at:
  data/health_reports/cycle_NNN_HHMM.json    — full per-cycle JSON
  logs/health_monitor.log                    — rolling human summary

The monitor tracks per-cycle metrics entirely from EventBus events so it
adds zero latency to the trading pipeline.  All disk I/O happens on the
EventBus delivery thread (background), never on the scheduler thread.

Diagnostic parameters (mirrors the 12-step checklist):
  1.  Container health        — process-level (startup events)
  2.  Single instance         — pid-file check
  3.  Scheduler heartbeat     — SYSTEM_HEARTBEAT cadence
  4.  Market session gate     — CYCLE_STARTED vs outside-hours log
  5.  Cycle execution         — count + latency
  6.  Signal pipeline         — generated → backtest → sim
  7.  Decision engine         — scores + approve/reject ratio
  8.  Execution layer         — orders placed, DUP GUARD, fill rate
  9.  Position state          — stale OPEN positions in CSV
  10. Risk & limits           — capital caps, kill-switch
  11. Telemetry / DB          — error counters
  12. Final verdict           — HEALTHY / DEGRADED / BLOCKED + root cause
"""

from __future__ import annotations

import csv
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_APP_ROOT    = Path(__file__).resolve().parent.parent
REPORT_DIR   = _APP_ROOT / "data" / "health_reports"
HEALTH_LOG   = _APP_ROOT / "logs" / "health_monitor.log"
CSV_FILE     = _APP_ROOT / "data" / "paper_trades.csv"
PID_FILE     = _APP_ROOT / "data" / "trading_engine.pid"
KILL_SWITCH  = _APP_ROOT / "utils" / "kill_switch.json"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)

IST = timezone(timedelta(hours=5, minutes=30))

# Keep last N cycle reports in memory for the API/dashboard
HISTORY_SIZE = 50


def _now_ist() -> datetime:
    return datetime.now(IST)


# ─────────────────────────────────────────────────────────────────────────────

class CycleHealthMonitor:
    """
    Subscribes to '*' on the shared EventBus.
    Accumulates per-cycle metrics, writes a 12-point health report
    after every CYCLE_COMPLETE.
    """

    def __init__(self, bus) -> None:
        self._lock  = threading.Lock()
        self._bus   = bus
        self._cycle_number     = 0
        self._today_cycles     = 0
        self._heartbeat_times: Deque[float] = deque(maxlen=20)
        self._history: Deque[Dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self._order_manager = None  # injected after OrderManager init
        self._reset_cycle_state()

        bus.subscribe("*", self._on_event,
                      agent_name="ControlTower.CycleHealthMonitor", priority=97)
        log.info("[CycleHealthMonitor] Initialised. Reports → %s", REPORT_DIR)

    # ── Public API ─────────────────────────────────────────────────────────

    def inject_order_manager(self, om) -> None:
        """Wire the OrderManager so health monitor can distinguish active
        carries (legitimately open in memory) from true orphans (CSV-only)."""
        self._order_manager = om
        log.debug("[CycleHealthMonitor] OrderManager injected for carry reconciliation.")

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """Return the most recent health report dict (or None)."""
        with self._lock:
            return dict(self._history[-1]) if self._history else None

    def get_history(self) -> List[Dict[str, Any]]:
        """Return all retained cycle reports."""
        with self._lock:
            return list(self._history)

    # ── Internal state reset ───────────────────────────────────────────────

    def _reset_cycle_state(self) -> None:
        """Zero all per-cycle accumulators (called on CYCLE_STARTED)."""
        self._cycle_id: str = ""
        self._cycle_start_ts: Optional[float] = None
        # Step 6 — signal pipeline
        self._signals_generated    = 0
        self._backtest_pass        = 0
        self._backtest_fail        = 0
        self._sim_approved         = 0
        self._sim_rejected         = 0
        self._risk_guardian_passed = 0
        # Step 7 — decision engine
        self._decisions_approved   = 0
        self._decisions_rejected   = 0
        self._decision_scores: List[float] = []
        self._rejection_reasons: List[str] = []
        # Step 8 — execution
        self._orders_placed        = 0
        self._orders_filled        = 0
        self._dup_guard_blocks     = 0
        self._capital_caps         = 0
        self._liquidity_rejects    = 0
        # Step 11 — telemetry
        self._db_errors            = 0
        self._agent_errors: List[str] = []

    # ── EventBus handler ───────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            et  = (event.event_type.value
                   if hasattr(event.event_type, "value")
                   else str(event.event_type))
            pay = event.payload if isinstance(event.payload, dict) else {}

            with self._lock:
                # ── Heartbeat ──────────────────────────────────────
                if et == EventType.SYSTEM_HEARTBEAT.value:
                    self._heartbeat_times.append(time.monotonic())

                # ── Cycle start / reset ────────────────────────────
                elif et == EventType.CYCLE_STARTED.value:
                    self._reset_cycle_state()
                    self._cycle_start_ts = time.monotonic()
                    self._cycle_id = (event.correlation_id
                                      or _now_ist().strftime("%H:%M:%S"))

                # ── Signal pipeline ────────────────────────────────
                elif et == EventType.SCAN_COMPLETE.value:
                    self._signals_generated += (
                        pay.get("equity", 0) + pay.get("options", 0)
                        + pay.get("arb", 0) + pay.get("total", 0)
                    )

                elif et == EventType.BACKTEST_PASSED.value:
                    self._backtest_pass += 1

                elif et == EventType.BACKTEST_FAILED.value:
                    self._backtest_fail += 1

                elif et == EventType.SIMULATION_COMPLETE.value:
                    approved = pay.get("approved", pay.get("passed", 0))
                    rejected = pay.get("rejected", 0)
                    self._sim_approved += approved
                    self._sim_rejected += rejected

                elif et == EventType.RISK_GUARDIAN_COMPLETE.value:
                    self._risk_guardian_passed += pay.get("approved", 0)

                # ── Decision engine ────────────────────────────────
                elif et == EventType.TRADE_APPROVED.value:
                    self._decisions_approved += 1
                    score = pay.get("score") or pay.get("weighted_score")
                    if score is not None:
                        try:
                            self._decision_scores.append(float(score))
                        except (TypeError, ValueError):
                            pass

                elif et == EventType.TRADE_REJECTED.value:
                    self._decisions_rejected += 1
                    reason = pay.get("reason", "")
                    if reason:
                        self._rejection_reasons.append(str(reason)[:80])

                # ── Execution ──────────────────────────────────────
                elif et == EventType.ORDER_PLACED.value:
                    self._orders_placed += 1

                elif et == EventType.ORDER_FILLED.value:
                    self._orders_filled += 1

                elif et == EventType.ORDER_REJECTED.value:
                    reason = pay.get("reason", "")
                    if "dup" in reason.lower() or "duplicate" in reason.lower():
                        self._dup_guard_blocks += 1
                    elif "capital" in reason.lower() or "qty" in reason.lower():
                        self._capital_caps += 1
                    elif "liquidity" in reason.lower():
                        self._liquidity_rejects += 1

                # ── Agent errors ───────────────────────────────────
                elif et == EventType.AGENT_ERROR.value:
                    agent = pay.get("agent", "unknown")
                    err   = pay.get("error", "")[:80]
                    self._agent_errors.append(f"{agent}: {err}")
                    if "database" in err.lower() or "sqlite" in err.lower():
                        self._db_errors += 1

                # ── Cycle complete → produce report ────────────────
                elif et == EventType.CYCLE_COMPLETE.value:
                    self._cycle_number += 1
                    self._today_cycles += 1
                    report = self._build_report(pay)
                    self._history.append(report)
                    self._write_report(report)

        except Exception as exc:
            log.debug("[CycleHealthMonitor] handler error: %s", exc)

    # ── Report builder ─────────────────────────────────────────────────────

    def _build_report(self, cycle_pay: dict) -> Dict[str, Any]:
        """
        Assemble a 12-section health report from accumulated per-cycle state.
        Called while self._lock is held.
        """
        now_ist = _now_ist()
        cycle_duration_ms = (
            int((time.monotonic() - self._cycle_start_ts) * 1000)
            if self._cycle_start_ts else 0
        )

        # ── Step 3: heartbeat gap ──────────────────────────────────────────
        hb_times = list(self._heartbeat_times)
        hb_max_gap_min = 0.0
        if len(hb_times) >= 2:
            gaps = [(hb_times[i+1] - hb_times[i]) / 60
                    for i in range(len(hb_times) - 1)]
            hb_max_gap_min = round(max(gaps), 1)

        # ── Step 7: decision scores ───────────────────────────────────────
        scores = self._decision_scores
        avg_score = round(sum(scores) / len(scores), 2) if scores else None
        min_score = round(min(scores), 2) if scores else None
        max_score = round(max(scores), 2) if scores else None

        # ── Step 8: execution rate ────────────────────────────────────────
        exec_rate = (
            round(self._orders_placed / self._decisions_approved, 2)
            if self._decisions_approved > 0 else 0.0
        )

        # ── Step 9: stale positions ───────────────────────────────────────
        stale = _count_stale_positions(now_ist.strftime("%Y-%m-%d"))

        # ── Step 10: kill-switch ──────────────────────────────────────────
        kill_switch_enabled, kill_switch_reason = _read_kill_switch()

        # ── Step 12: verdict ──────────────────────────────────────────────
        issues   = []
        scope    = []

        # Classify unclosed CSV positions using the in-memory OrderManager as
        # the source of truth for "legitimately active carries".
        #
        # Three buckets:
        #   active_carry  — order_id present in OrderManager._orders (healthy)
        #   young_orphan  — NOT in OM, age ≤ _CARRY_MAX_DAYS (will auto-expire)
        #   old_stale     — NOT in OM, age >  _CARRY_MAX_DAYS (genuinely forgotten)
        today_str = _now_ist().strftime("%Y-%m-%d")
        prev_session = [p for p in stale
                        if not p.get("timestamp", "").startswith(today_str)]

        # Pull active order_ids from injected OrderManager (safe if not yet injected)
        _active_oids: set = set()
        if self._order_manager is not None:
            try:
                _active_oids = self._order_manager.get_open_order_ids()
            except Exception:
                pass

        active_carry  = [p for p in prev_session
                         if p.get("order_id") in _active_oids]
        non_active    = [p for p in prev_session
                         if p.get("order_id") not in _active_oids]
        young_orphan  = [p for p in non_active
                         if float(p.get("age_days", 0)) <= _CARRY_MAX_DAYS]
        old_stale     = [p for p in non_active
                         if float(p.get("age_days", 0)) > _CARRY_MAX_DAYS]

        stale_symbols = [p["symbol"] for p in old_stale]
        carry_symbols = [p["symbol"] for p in active_carry]

        if self._dup_guard_blocks > 0 and old_stale:
            issues.append(
                f"DUP_GUARD: {self._dup_guard_blocks} block(s) — "
                f"symbols: {', '.join(stale_symbols) or 'check CSV'}"
            )
        if old_stale:
            issues.append(
                f"STALE_POSITIONS: {len(old_stale)} orphan(s) exceed max carry window — "
                + ", ".join(f"{p['order_id']}({p['symbol']},{p['age_days']}d)"
                            for p in old_stale[:5])
            )
        if young_orphan:
            # Soft warning — these will auto-expire via check_and_expire_carries()
            log.warning(
                "[CycleHealthMonitor] ORPHAN_WATCH: %d position(s) in CSV not tracked "
                "in memory (will auto-expire) — %s",
                len(young_orphan),
                ", ".join(f"{p['order_id']}({p['symbol']},{p['age_days']}d)"
                          for p in young_orphan[:5])
            )
        if not kill_switch_enabled:
            issues.append(f"KILL_SWITCH: trading DISABLED — {kill_switch_reason}")
        if self._db_errors > 0:
            issues.append(f"DB_ERRORS: {self._db_errors} SQLite error(s) this cycle")
        if self._agent_errors:
            issues.append(f"AGENT_ERRORS: {'; '.join(self._agent_errors[:3])}")
        if self._signals_generated == 0:
            issues.append("NO_SIGNALS: scanner produced 0 opportunities")
        # Only flag execution gap if there are no known reasons (stale/dup) explaining zero orders
        if (self._decisions_approved > 0 and self._orders_placed == 0
                and self._dup_guard_blocks == 0 and not stale):
            issues.append(
                "EXECUTION_GAP: signals were approved but 0 orders placed "
                "(check OrderManager pipeline)"
            )
        if hb_max_gap_min > 10:
            issues.append(f"HEARTBEAT_GAP: {hb_max_gap_min} min between heartbeats")

        # Scope for improvement
        if self._decisions_rejected > self._decisions_approved and self._decisions_rejected > 0:
            rate = round(self._decisions_rejected /
                         max(self._decisions_approved + self._decisions_rejected, 1) * 100)
            scope.append(f"HIGH_REJECTION_RATE: {rate}% of decisions rejected — review thresholds")
        if self._backtest_fail > self._backtest_pass and self._backtest_fail > 0:
            scope.append(
                f"BACKTEST_FAILURES: {self._backtest_fail} fail vs {self._backtest_pass} pass "
                "— review strategy parameters"
            )
        if self._sim_rejected > self._sim_approved and self._sim_rejected > 0:
            scope.append(
                f"SIM_REJECTIONS: {self._sim_rejected} rejected vs {self._sim_approved} approved "
                "— market conditions very conservative"
            )
        if avg_score is not None and avg_score < 6.0:
            scope.append(f"LOW_SCORES: avg {avg_score}/10 — may be below decision threshold")
        if self._liquidity_rejects > 5:
            scope.append(
                f"LIQUIDITY_FILTER: {self._liquidity_rejects} rejects — "
                "consider expanding liquid symbol universe"
            )

        if issues:
            overall = ("BLOCKED"
                       if any("DUP_GUARD" in i or "KILL_SWITCH" in i
                               or "NO_SIGNALS" in i or "EXECUTION_GAP" in i
                               for i in issues)
                       else "DEGRADED")
        else:
            overall = "HEALTHY"

        trading_status = (
            "RUNNING"           if self._orders_placed > 0 else
            "NOT_TRADING"       if self._decisions_approved == 0 else
            "APPROVED_NOT_EXEC" if self._orders_placed == 0 else
            "IDLE"
        )

        return {
            "meta": {
                "cycle_number":   self._cycle_number,
                "cycle_id":       self._cycle_id,
                "timestamp_ist":  now_ist.isoformat(),
                "duration_ms":    cycle_duration_ms,
                "today_cycles":   self._today_cycles,
            },
            "step1_container": {
                "uptime_s":       _container_uptime_s(),
                "verdict":        "STABLE",
            },
            "step2_instance": {
                "verdict":        _single_instance_check(),
            },
            "step3_heartbeat": {
                "heartbeat_count": len(hb_times),
                "max_gap_min":     hb_max_gap_min,
                "verdict":        ("ALIVE" if hb_max_gap_min < 10
                                   else f"STALL_RISK — gap {hb_max_gap_min} min"),
            },
            "step4_session_gate": {
                "ist_time":       now_ist.strftime("%H:%M:%S"),
                "in_session":     _is_market_open(now_ist),
                "verdict":        "PASS",
            },
            "step5_cycles": {
                "today_total":    self._today_cycles,
                "expected_range": "6-8",
                "verdict":        ("NORMAL" if self._today_cycles >= 4
                                   else "LOW — check scheduler slots"),
            },
            "step6_signals": {
                "generated":      self._signals_generated,
                "backtest_pass":  self._backtest_pass,
                "backtest_fail":  self._backtest_fail,
                "sim_approved":   self._sim_approved,
                "sim_rejected":   self._sim_rejected,
                "guardian_pass":  self._risk_guardian_passed,
                "verdict":        ("ACTIVE" if self._signals_generated > 0
                                   else "NO_SIGNALS"),
            },
            "step7_decision": {
                "approved":       self._decisions_approved,
                "rejected":       self._decisions_rejected,
                "avg_score":      avg_score,
                "min_score":      min_score,
                "max_score":      max_score,
                "top_rejections": self._rejection_reasons[:5],
                "verdict":        (
                    "HEALTHY"         if avg_score and avg_score >= 6.5 else
                    "BELOW_THRESHOLD" if avg_score and avg_score < 6.5 else
                    "NO_DATA"
                ),
            },
            "step8_execution": {
                "orders_placed":     self._orders_placed,
                "orders_filled":     self._orders_filled,
                "exec_rate":         exec_rate,
                "dup_guard_blocks":  self._dup_guard_blocks,
                "capital_caps":      self._capital_caps,
                "liquidity_rejects": self._liquidity_rejects,
                "verdict":           (
                    "EXECUTING"       if self._orders_placed > 0 else
                    "DUP_BLOCKED"     if self._dup_guard_blocks > 0 else
                    "NO_ORDERS"
                ),
            },
            "step9_positions": {
                "open_today":     len([p for p in stale if p.get("timestamp","").startswith(today_str)]),
                "carry_count":    len(active_carry),
                "carry_details":  active_carry,
                "orphan_count":   len(young_orphan),
                "orphan_details": young_orphan,
                "stale_count":    len(old_stale),
                "stale_details":  old_stale,
                "restore_integrity": (
                    self._order_manager.get_restore_stats()
                    if self._order_manager is not None and hasattr(self._order_manager, "get_restore_stats")
                    else {}
                ),
                "verdict":        (
                    "CLEAN"          if not old_stale and not young_orphan and not active_carry else
                    f"CARRY: {len(active_carry)} active + {len(young_orphan)} orphan watch"
                                   if not old_stale else
                    f"STALE: {len(old_stale)} orphan(s) exceed max carry window"
                ),
            },
            "step10_risk": {
                "kill_switch_enabled": kill_switch_enabled,
                "kill_switch_reason":  kill_switch_reason,
                "capital_cap_events":  self._capital_caps,
                "verdict":             ("HEALTHY" if kill_switch_enabled else "DISABLED"),
            },
            "step11_telemetry": {
                "db_errors":   self._db_errors,
                "agent_errors": self._agent_errors[:10],
                "verdict":     ("STABLE" if self._db_errors == 0 else
                                f"DEGRADED — {self._db_errors} DB error(s)"),
            },
            "feed_health": self._build_feed_health_section(issues),
            "step12_verdict": {
                "system_health":    overall,
                "trading_status":   trading_status,
                "issues":           issues,
                "scope_for_improvement": scope,
                "action_required":  _action_for_issues(issues),
            },
        }

    # ── Feed health (MarketDataRouter observability) ───────────────────────

    def _build_feed_health_section(self, issues: list) -> dict:
        """Pull live stats from MarketDataRouter and add to cycle report."""
        try:
            from data_feeds.market_data_router import get_market_data_router
            s = get_market_data_router().get_router_stats()
            primary_health = (
                "DHAN_LIVE"     if s["dhan_live"] and s["dhan_success"] > 0 else
                "DHAN_SIM"      if not s["dhan_live"] else
                "DHAN_DEGRADED"
            )
            degraded = s["last_degraded"]
            if degraded:
                issues.append(
                    f"FEED_DEGRADED: {len(degraded)} symbol(s) have no live price "
                    f"— {degraded}"
                )
            if s["divergence_count"] > 0:
                issues.append(
                    f"FEED_DIVERGENCE: {s['divergence_count']} Dhan/Yahoo price disagreements"
                )
            return {
                "primary_feed":         "Dhan",
                "primary_feed_health":  primary_health,
                "dhan_success":         s["dhan_success"],
                "dhan_fail":            s["dhan_fail"],
                "dhan_success_pct":     s["dhan_success_pct"],
                "fallback_usage":       f"{s['yahoo_fallback_pct']}% via Yahoo",
                "yahoo_success":        s["yahoo_success"],
                "cache_served":         s["cache_served"],
                "degraded_symbols":     degraded,
                "divergence_count":     s["divergence_count"],
                "source_distribution":  s["last_source_dist"],
                "verdict": (
                    f"DEGRADED — {len(degraded)} symbol(s) no live price" if degraded else
                    "DHAN_LIVE" if s["dhan_live"] and s["dhan_success"] > 0 else
                    "YAHOO_ONLY — Dhan not configured"
                ),
            }
        except Exception as exc:
            return {
                "primary_feed":        "unknown",
                "primary_feed_health": "unavailable",
                "verdict":             f"error: {exc}",
            }

    # ── Disk I/O ───────────────────────────────────────────────────────────

    def _write_report(self, report: Dict[str, Any]) -> None:
        """Write JSON file + one-line health log summary."""
        try:
            cn   = report["meta"]["cycle_number"]
            ts   = _now_ist().strftime("%H%M")
            jpath = REPORT_DIR / f"cycle_{cn:04d}_{ts}.json"
            with open(jpath, "w") as f:
                json.dump(report, f, indent=2)

            # Keep only last 20 JSON files to avoid disk fill
            _prune_old_reports(REPORT_DIR, keep=20)

            # Human-readable summary line
            m     = report["meta"]
            v     = report["step12_verdict"]
            e     = report["step8_execution"]
            s6    = report["step6_signals"]
            s7    = report["step7_decision"]
            s9    = report["step9_positions"]
            fh    = report.get("feed_health", {})
            issues_str = " | ".join(v["issues"]) if v["issues"] else "none"
            feed_str   = (
                f"feed={fh.get('primary_feed_health','?')} "
                f"src={fh.get('source_distribution',{})} "
                f"degraded={fh.get('degraded_symbols',[])}"
            )

            line = (
                f"[{m['timestamp_ist'][:19]}] "
                f"Cycle#{m['cycle_number']:04d} ({m['duration_ms']}ms) "
                f"HEALTH={v['system_health']} "
                f"TRADING={v['trading_status']} "
                f"signals={s6['generated']} "
                f"approved={s7['approved']} rejected={s7['rejected']} "
                f"score_avg={s7['avg_score']} "
                f"orders={e['orders_placed']} filled={e['orders_filled']} "
                f"dup_blocks={e['dup_guard_blocks']} "
                f"open_today={s9.get('open_today',0)} "
                f"stale_old={s9['stale_count']} "
                f"restore_today={s9.get('restore_integrity',{}).get('restored_today','?')}_carry={s9.get('restore_integrity',{}).get('restored_carry','?')}_orphan={s9.get('restore_integrity',{}).get('orphan_watch','?')} "
                f"db_errors={report['step11_telemetry']['db_errors']} "
                f"{feed_str} "
                f"issues=[{issues_str}]\n"
            )
            with open(HEALTH_LOG, "a") as lf:
                lf.write(line)

            # Log to trading engine log at INFO level
            status_icon = "✅" if v["system_health"] == "HEALTHY" else "⚠️ " if v["system_health"] == "DEGRADED" else "❌"
            log.info(
                "[CycleHealthMonitor] %s Cycle#%d | %s | "
                "signals=%d approved=%d orders=%d stale=%d | issues: %s",
                status_icon, m["cycle_number"], v["system_health"],
                s6["generated"], s7["approved"], e["orders_placed"],
                s9["stale_count"],
                issues_str if v["issues"] else "none",
            )

        except Exception as exc:
            log.debug("[CycleHealthMonitor] write_report error: %s", exc)


# ── Helpers (module-level, no lock needed) ─────────────────────────────────

def _count_stale_positions(today_str: str) -> List[Dict[str, str]]:
    """Read paper_trades.csv and return all unclosed positions."""
    if not CSV_FILE.exists():
        return []
    try:
        rows = list(csv.DictReader(open(CSV_FILE)))
        rows = [{k: v for k, v in r.items() if k} for r in rows]
        counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"OPEN": 0, "CLOSE": 0})
        last: Dict[str, dict] = {}
        # All event types that represent a closed/resolved position
        _CLOSE_EVENTS = {"CLOSE", "CANCELLED", "SESSION_EXPIRED",
                         "SESSION_EXPIRED_EXTENDED", "SYSTEM_CLEANUP"}
        for r in rows:
            oid = r.get("order_id", "")
            ev  = r.get("event", "").upper()
            if ev == "OPEN":
                counts[oid]["OPEN"] += 1
            elif ev in _CLOSE_EVENTS:
                counts[oid]["CLOSE"] += 1
            last[oid] = r
        return [
            {
                "order_id":    oid,
                "symbol":      last[oid].get("symbol", "?"),
                "entry_price": last[oid].get("entry_price", "?"),
                "timestamp":   last[oid].get("timestamp", "?"),
                "age_days":    _position_age_days(last[oid].get("timestamp", "")),
            }
            for oid, c in counts.items()
            if c["OPEN"] > 0 and c["CLOSE"] == 0
        ]
    except Exception as exc:
        log.debug("[CycleHealthMonitor] stale-scan error: %s", exc)
        return []


def _position_age_days(ts_str: str) -> float:
    """Return how many days ago a position was opened."""
    try:
        dt = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
        return round((datetime.now() - dt).total_seconds() / 86400, 1)
    except Exception:
        return 0.0


def _read_kill_switch() -> tuple[bool, str]:
    """Return (enabled, reason) from kill_switch.json."""
    try:
        raw = KILL_SWITCH.read_bytes()
        # Strip UTF-8 BOM if present
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        ks = json.loads(raw.decode("utf-8"))
        return bool(ks.get("trading_enabled", True)), ks.get("reason", "")
    except FileNotFoundError:
        return True, "file missing (default=enabled)"
    except Exception as exc:
        log.debug("[CycleHealthMonitor] kill-switch read error: %s", exc)
        return True, f"parse error: {exc}"


def _container_uptime_s() -> int:
    """Return container uptime in seconds from /proc/uptime."""
    try:
        return int(float(open("/proc/uptime").read().split()[0]))
    except Exception:
        return -1


def _single_instance_check() -> str:
    """Check for duplicate processes via PID file."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if os.path.exists(f"/proc/{pid}"):
                return f"PASS — pid={pid}"
            return "STALE_PID — process not running"
        except Exception:
            pass
    return "NO_PID_FILE — cannot verify"


def _is_market_open(dt: datetime) -> bool:
    h, m_val = dt.hour, dt.minute
    total = h * 60 + m_val
    return (9 * 60 + 15) <= total <= (15 * 60 + 30)


def _action_for_issues(issues: List[str]) -> List[str]:
    actions = []
    for issue in issues:
        if "DUP_GUARD" in issue:
            actions.append(
                "Run close-stale script: "
                "scripts/close_stale_positions.py — then restart container"
            )
        if "STALE_POSITIONS" in issue:
            actions.append(
                "Stale positions in CSV will be blocked on next restart. "
                "Close them now or they will block DUP GUARD permanently."
            )
        if "KILL_SWITCH" in issue:
            actions.append(
                "Re-enable trading: set trading_enabled=true in utils/kill_switch.json"
            )
        if "DB_ERRORS" in issue:
            actions.append(
                "DB errors present — verify TelemetryLogger WAL fix is deployed"
            )
        if "NO_SIGNALS" in issue:
            actions.append(
                "Scanner returned 0 opportunities — check data feed (yfinance/Dhan) "
                "and market hours guard"
            )
        if "EXECUTION_GAP" in issue:
            actions.append(
                "Approved signals not reaching execution — "
                "trace DecisionEngine → SmartExecutionEngine → OrderManager logs"
            )
        if "HEARTBEAT_GAP" in issue:
            actions.append(
                "Scheduler stall detected — check orchestrator scheduler thread "
                "and whether a layer timed out"
            )
    if not actions:
        actions.append("No action required — system healthy")
    return actions


def _prune_old_reports(directory: Path, keep: int = 20) -> None:
    """Delete oldest JSON reports, keeping only the newest `keep` files."""
    try:
        files = sorted(directory.glob("cycle_*.json"), key=os.path.getmtime)
        for f in files[:-keep]:
            f.unlink(missing_ok=True)
    except Exception:
        pass
