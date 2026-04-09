"""
Control Tower Dashboard — Streamlit Application
===============================================
Run:
    streamlit run control_tower/dashboard_app.py

This is a STANDALONE script — it reads exclusively from the SQLite
database written by TelemetryLogger.  It does NOT import the trading
brain code (no circular imports, no heavy dependencies at launch).

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  BANNER  — Regime · VIX · Current Cycle · Uptime    │
  ├──────────────┬──────────────────────────────────────┤
  │ Signal Funnel│ Strategy Distribution (bar chart)    │
  ├──────────────┴──────────────────────────────────────┤
  │ Recent Decisions table                              │
  ├─────────────────────────────────────────────────────┤
  │ Agent Health table                                   │
  ├─────────────────────────────────────────────────────┤
  │ Live Event Stream                                    │
  └─────────────────────────────────────────────────────┘

Auto-refreshes every 5 seconds.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ── Optional Streamlit guard ───────────────────────────────────────────────
try:
    import streamlit as st
except ImportError:
    raise SystemExit(
        "Streamlit not installed.  Run:  pip install streamlit>=1.32.0"
    )

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# ── Paths ──────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.abspath(os.path.join(_HERE, ".."))
DB_PATH   = os.path.join(_ROOT, "data", "control_tower.db")
REFRESH_S = 5   # auto-refresh interval


# ══════════════════════════════════════════════════════════════════════════
# DB helpers
# ══════════════════════════════════════════════════════════════════════════

def _connect() -> Optional[sqlite3.Connection]:
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _query(sql: str, params=()) -> List[Dict[str, Any]]:
    conn = _connect()
    if conn is None:
        return []
    try:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def _scalar(sql: str, params=(), default=0):
    conn = _connect()
    if conn is None:
        return default
    try:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception:
        return default
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
# Data-fetch functions
# ══════════════════════════════════════════════════════════════════════════

def fetch_latest_cycle() -> Dict[str, Any]:
    rows = _query(
        "SELECT * FROM ct_cycles ORDER BY started_at DESC LIMIT 1")
    return rows[0] if rows else {}


def fetch_cycle_history(n: int = 30) -> List[Dict[str, Any]]:
    return _query(
        "SELECT * FROM ct_cycles ORDER BY started_at DESC LIMIT ?", (n,))


def fetch_recent_decisions(n: int = 50) -> List[Dict[str, Any]]:
    return _query(
        "SELECT ts, symbol, strategy, decision, confidence, rejection_reason, "
        "       technical_score, risk_score, macro_score "
        "FROM   ct_decisions "
        "ORDER  BY id DESC LIMIT ?", (n,))


def fetch_recent_events(n: int = 80) -> List[Dict[str, Any]]:
    return _query(
        "SELECT ts, event_type, source_agent, payload "
        "FROM   ct_events "
        "ORDER  BY id DESC LIMIT ?", (n,))


def fetch_agent_stats() -> List[Dict[str, Any]]:
    """Derive per-agent stats from the events table."""
    # Exclude intentional risk rejections from error count — 'risk.check.failed'
    # is normal operation, not a real error.
    return _query(
        "SELECT source_agent, COUNT(*) AS event_count, "
        "       SUM(CASE WHEN (event_type LIKE '%fail%' OR event_type LIKE '%error%') "
        "                    AND event_type NOT IN ('risk.check.failed','trade.rejected') "
        "               THEN 1 ELSE 0 END) AS error_count, "
        "       MAX(ts) AS last_seen "
        "FROM   ct_events "
        "WHERE  source_agent IS NOT NULL AND source_agent != '' "
        "GROUP  BY source_agent "
        "ORDER  BY event_count DESC")


def fetch_strategy_distribution(cycle_id: str = "") -> List[Dict[str, Any]]:
    if cycle_id:
        return _query(
            "SELECT strategy, COUNT(*) AS cnt, "
            "       AVG(confidence) AS avg_conf "
            "FROM   ct_decisions WHERE cycle_id=? "
            "GROUP  BY strategy ORDER BY cnt DESC", (cycle_id,))
    return _query(
        "SELECT strategy, COUNT(*) AS cnt, AVG(confidence) AS avg_conf "
        "FROM   ct_decisions "
        "GROUP  BY strategy ORDER BY cnt DESC LIMIT 15")


def fetch_rejection_summary() -> List[Dict[str, Any]]:
    return _query(
        "SELECT rejection_reason AS reason, COUNT(*) AS cnt "
        "FROM   ct_decisions "
        "WHERE  decision='REJECTED' AND rejection_reason != '' "
        "GROUP  BY rejection_reason ORDER BY cnt DESC LIMIT 10")


def fetch_funnel_history(n: int = 20) -> List[Dict[str, Any]]:
    return _query(
        "SELECT cycle_id, signals_generated, strategies_assigned, "
        "       risk_approved, sim_approved, trades_executed "
        "FROM   ct_cycles "
        "WHERE  signals_generated > 0 "
        "ORDER  BY started_at DESC LIMIT ?", (n,))


# ══════════════════════════════════════════════════════════════════════════
# Service-status helpers
# ══════════════════════════════════════════════════════════════════════════

def fetch_service_status() -> Dict[str, Any]:
    """Derive live/offline status from the most-recent event timestamp."""
    rows = _query("SELECT ts, event_type FROM ct_events ORDER BY rowid DESC LIMIT 1")
    if not rows:
        return {"status": "UNKNOWN", "last_ts": None, "last_event": "", "age_min": None}
    ts_str = rows[0]["ts"]
    last_event = rows[0]["event_type"]
    try:
        ts = datetime.fromisoformat(ts_str[:19])
        now = datetime.now()
        age = (now - ts).total_seconds() / 60
        # Guard against TZ mismatch (naive timestamps from different zones)
        if age < -5:          # ts is ahead of now → TZ offset issue, treat as fresh
            age = abs(age) % (24 * 60)   # wrap to positive
        age = abs(age)        # always positive
    except Exception:
        return {"status": "UNKNOWN", "last_ts": ts_str, "last_event": last_event, "age_min": None}
    if age < 10:
        status = "ONLINE"
    elif age < 60:
        status = "IDLE"
    else:
        status = "OFFLINE"
    return {"status": status, "last_ts": ts_str[:19], "last_event": last_event, "age_min": round(age, 1)}


def fetch_today_events_count() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return _scalar("SELECT COUNT(*) FROM ct_events WHERE ts LIKE ?", (today + "%",), 0)


# ══════════════════════════════════════════════════════════════════════════
# Paper trading EOD helpers
# ══════════════════════════════════════════════════════════════════════════

def fetch_paper_trades_csv() -> List[Dict[str, Any]]:
    """Read data/paper_trades.csv and return the last 50 rows newest-first."""
    _path = os.path.join(_ROOT, "data", "paper_trades.csv")
    if not os.path.exists(_path):
        return []
    try:
        with open(_path, encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) < 2:
            return []
        header = [h.strip() for h in lines[0].split(",")]
        rows = []
        for ln in reversed(lines[1:]):
            if not ln.strip():
                continue
            vals = [v.strip() for v in ln.split(",")]
            if len(vals) >= len(header):
                rows.append(dict(zip(header, vals[:len(header)])))
            if len(rows) >= 50:
                break
        return rows
    except Exception:
        return []


def fetch_paper_trading_eod() -> Optional[Dict[str, Any]]:
    """Read data/paper_trading_daily.json written by the orchestrator at 15:35."""
    _path = os.path.join(_ROOT, "data", "paper_trading_daily.json")
    if not os.path.exists(_path):
        return None
    try:
        with open(_path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def fetch_latest_eod_report_text() -> Optional[str]:
    """Return the most-recently saved eod_report_*.txt for display."""
    import glob
    _logs = os.path.join(_ROOT, "data", "logs")
    files = sorted(glob.glob(os.path.join(_logs, "eod_report_*.txt")), reverse=True)
    if not files:
        return None
    try:
        with open(files[0], encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════
# New panel helpers — Cycle Monitor · Rejection Funnel · Trade Decision · Scheduler
# ══════════════════════════════════════════════════════════════════════════

def fetch_cycle_monitor() -> Dict[str, Any]:
    """Latest cycle with decision_passed derived from ct_decisions."""
    cycle = fetch_latest_cycle()
    if not cycle:
        return {}
    cid = cycle.get("cycle_id", "")
    cycle["decision_passed"] = _scalar(
        "SELECT COUNT(*) FROM ct_decisions WHERE cycle_id=? AND decision='APPROVED'",
        (cid,)
    )
    if cycle.get("had_error"):
        cycle["cycle_status"] = "ERROR"
    elif cycle.get("completed_at"):
        cycle["cycle_status"] = "COMPLETE"
    else:
        cycle["cycle_status"] = "RUNNING"
    # Compute duration from timestamps when cycle_ms is 0
    if not cycle.get("cycle_ms") and cycle.get("started_at") and cycle.get("completed_at"):
        try:
            s = datetime.fromisoformat(cycle["started_at"][:19])
            e = datetime.fromisoformat(cycle["completed_at"][:19])
            cycle["cycle_ms"] = int((e - s).total_seconds() * 1000)
        except Exception:
            pass
    return cycle


def fetch_latest_approved_trade() -> Dict[str, Any]:
    """Latest APPROVED decision + order details from ct_events payload."""
    rows = _query(
        "SELECT * FROM ct_decisions WHERE decision='APPROVED' ORDER BY id DESC LIMIT 1"
    )
    if not rows:
        return {}
    trade = dict(rows[0])
    # Try to enrich with ORDER_PLACED event payload for qty / rr / capital_pct
    order_rows = _query(
        "SELECT payload FROM ct_events "
        "WHERE event_type='order.placed' AND cycle_id=? AND payload LIKE ? "
        "ORDER BY id DESC LIMIT 1",
        (trade.get("cycle_id", ""), f"%{trade.get('symbol', '')}%")
    )
    if order_rows:
        try:
            pay = json.loads(order_rows[0].get("payload") or "{}")
            trade["qty"]         = pay.get("qty", "—")
            trade["rr"]          = pay.get("rr", pay.get("risk_reward", "—"))
            trade["capital_pct"] = pay.get("capital_pct", "—")
            trade["exec_status"] = pay.get("status", "PENDING")
        except Exception:
            trade.setdefault("qty", "—"); trade.setdefault("rr", "—")
            trade.setdefault("capital_pct", "—"); trade.setdefault("exec_status", "—")
    else:
        trade["qty"] = "—"; trade["rr"] = "—"
        trade["capital_pct"] = "—"; trade["exec_status"] = "DEFERRED"
    return trade


def _read_schedule_from_config() -> Dict[str, str]:
    """Parse SCHEDULE from config.py with regex — no import needed."""
    import re
    _LEGACY = {"market_regime_analysis", "opportunity_scan", "mid_day_review"}
    schedule: Dict[str, str] = {}
    try:
        with open(os.path.join(_ROOT, "config.py"), encoding="utf-8") as fh:
            in_block = False
            for line in fh:
                if re.search(r'^SCHEDULE\s*=\s*\{', line):
                    in_block = True
                    continue
                if in_block:
                    if "}" in line:
                        break
                    ls = line.strip()
                    if ls.startswith("#"):
                        continue
                    m = re.search(r'"(\w+)"\s*:\s*"(\d{2}:\d{2})"', ls)
                    if m and m.group(1) not in _LEGACY:
                        schedule[m.group(1)] = m.group(2)
    except Exception:
        pass
    return schedule


def fetch_scheduler_status() -> Dict[str, Any]:
    """Today's scheduled cycle list, completion status, and next-cycle countdown."""
    schedule = _read_schedule_from_config()
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_dt    = datetime.now()
    now_hhmm  = now_dt.strftime("%H:%M")

    done_rows  = _query(
        "SELECT started_at FROM ct_cycles WHERE started_at LIKE ?",
        (today_str + "%",)
    )
    done_times = [
        r["started_at"][11:16] for r in done_rows
        if len(r.get("started_at", "")) >= 16
    ]

    cycles = []
    for name, hhmm in sorted(schedule.items(), key=lambda x: x[1]):
        fired = any(
            abs(int(t.replace(":", "")) - int(hhmm.replace(":", ""))) <= 10
            for t in done_times
        )
        if fired:
            status = "✅ Done"
        elif hhmm <= now_hhmm:
            status = "⚠️ Missed"
        else:
            status = "⏳ Pending"
        cycles.append({
            "Scan": name.replace("_", " ").title(),
            "Time": hhmm,
            "Status": status,
        })

    # Next pending cycle
    next_name = next_hhmm = secs_until = None
    for name, hhmm in sorted(schedule.items(), key=lambda x: x[1]):
        if hhmm > now_hhmm:
            h, m      = map(int, hhmm.split(":"))
            tgt       = now_dt.replace(hour=h, minute=m, second=0, microsecond=0)
            secs_until = (tgt - now_dt).total_seconds()
            next_name  = name
            next_hhmm  = hhmm
            break

    return {
        "cycles":     cycles,
        "next_name":  next_name,
        "next_hhmm":  next_hhmm,
        "secs_until": secs_until,
    }


# ══════════════════════════════════════════════════════════════════════════
# Dashboard layout
# ══════════════════════════════════════════════════════════════════════════

def run_dashboard() -> None:
    st.set_page_config(
        page_title="AI Trading Brain — Control Tower",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS with better contrast and visibility
    st.markdown("""
    <style>
    * {
        color: #ffffff !important;
    }
    
    body, .main {
        background-color: #0a0f1a;
        color: #ffffff !important;
    }
    
    .metric-card { 
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 8px;
        padding: 12px;
        margin: 4px;
        color: #ffffff !important;
        border: 2px solid #00d4ff;
    }
    
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #162a47 0%, #1a3a52 100%) !important;
        border: 2px solid #00d4ff !important;
        padding: 12px !important;
        border-radius: 8px !important;
    }
    
    [data-testid="metric-container"] label {
        color: #64b5f6 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    [data-testid="metric-container"] div {
        color: #ffffff !important;
    }
    
    .stMetric {
        background: linear-gradient(135deg, #1a2540 0%, #243050 100%) !important;
        border-radius: 8px !important;
        padding: 12px !important;
        color: #ffffff !important;
        border-left: 4px solid #00d4ff !important;
    }
    
    h1, h2, h3, h4, h5, h6 { 
        color: #ffffff !important;
    }
    
    .approved    { color: #00ff88 !important; font-weight: bold; }
    .rejected    { color: #ff6b6b !important; font-weight: bold; }
    
    table { color: #ffffff !important; }
    table thead { background-color: #1a2540 !important; }
    table tbody tr { background-color: #162a47 !important; }
    table tbody tr:hover { background-color: #1e3a5f !important; }
    
    .stDataFrame { background-color: #162a47 !important; color: #ffffff !important; }
    .stDataFrame th { background-color: #1a2540 !important; color: #64b5f6 !important; }
    
    [data-testid="stMarkdownContainer"] { color: #ffffff !important; }
    
    </style>
    """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────────────────
    st.title("🧠 AI Trading Brain — Control Tower")
    st.caption(f"Auto-refreshing every {REFRESH_S}s  ·  DB: {DB_PATH}")

    # ── Service status banner ───────────────────────────────────────────────
    svc = fetch_service_status()
    s_status  = svc["status"]
    s_icon    = {"ONLINE": "🟢", "IDLE": "🟡", "OFFLINE": "🔴", "UNKNOWN": "⚪"}.get(s_status, "⚪")
    s_colour  = {"ONLINE": "#00ff88", "IDLE": "#ffd700", "OFFLINE": "#ff4444", "UNKNOWN": "#aaaaaa"}.get(s_status, "#aaa")
    s_age_txt = f"{svc['age_min']} min ago" if svc["age_min"] is not None else "unknown"
    today_evts = fetch_today_events_count()
    st.markdown(
        f"<div style='background:#162a47;border-radius:8px;padding:12px 18px;"
        f"border-left:5px solid {s_colour};margin-bottom:8px'>"
        f"<span style='font-size:1.3em;font-weight:bold;color:{s_colour}'>{s_icon} VPS Service: {s_status}</span>"
        f"&nbsp;&nbsp;&nbsp;<span style='color:#aaa'>Last activity: {svc['last_ts'] or 'none'} ({s_age_txt})&nbsp;|&nbsp;"
        f"Today events: {today_evts}&nbsp;|&nbsp;Mode: 🧪 PAPER</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not os.path.exists(DB_PATH):
        st.error("⚠️  Database not found.  Start the trading brain first "
                 f"(`python main.py`) so data can be logged.\n\nExpected: {DB_PATH}")
        time.sleep(REFRESH_S)
        st.rerun()
        return

    # ── Banner row (key metrics) ────────────────────────────────────────────
    cycle = fetch_latest_cycle()
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Regime",  cycle.get("regime") or "–")
    c2.metric("VIX",     f"{cycle.get('vix') or 0:.1f}")
    c3.metric("PCR",     f"{cycle.get('pcr') or 0:.2f}")
    c4.metric("Signals", cycle.get("signals_generated") or 0)
    c5.metric("Risk ✓",  cycle.get("risk_approved") or 0)
    c6.metric("Sim ✓",   cycle.get("sim_approved") or 0)
    c7.metric("Executed",cycle.get("trades_executed") or 0)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # PANEL 1 — Cycle Monitor
    # ══════════════════════════════════════════════════════════════════════
    st.subheader("🔄 Cycle Monitor")
    cm = fetch_cycle_monitor()
    if cm:
        _cs     = cm.get("cycle_status", "—")
        _s_col  = {"COMPLETE": "#00ff88", "RUNNING": "#ffd700", "ERROR": "#ff4444"}.get(_cs, "#aaa")
        _s_icon = {"COMPLETE": "✅", "RUNNING": "🔄", "ERROR": "❌"}.get(_cs, "⚪")
        _dur    = cm.get("cycle_ms", 0)
        _start  = (cm.get("started_at") or "")[:19]
        st.markdown(
            f"<div style='background:#162a47;border-radius:8px;padding:10px 18px;"
            f"border-left:5px solid {_s_col};margin-bottom:10px'>"
            f"<span style='font-size:1.05em;font-weight:bold;color:{_s_col}'>"
            f"{_s_icon} Cycle — {cm.get('cycle_id','—')}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Started: {_start or '—'}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Duration: {_dur:,} ms</span></div>",
            unsafe_allow_html=True,
        )
        p1, p2, p3, p4, p5, p6, p7, p8 = st.columns(8)
        p1.metric("Status",      _cs)
        p2.metric("Signals",     cm.get("signals_generated")   or 0)
        p3.metric("Strategy ✓",  cm.get("strategies_assigned") or 0)
        p4.metric("Risk ✓",      cm.get("risk_approved")       or 0)
        p5.metric("Sim ✓",       cm.get("sim_approved")        or 0)
        p6.metric("Decision ✓",  cm.get("decision_passed")     or 0)
        p7.metric("Executed",    cm.get("trades_executed")     or 0)
        p8.metric("Duration ms", f"{_dur or 0:,}")
    else:
        st.info("No cycle data yet — start the trading brain to see live stats.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # PANEL 2 — Rejection Funnel  |  PANEL 3 — Latest Approved Trade
    # ══════════════════════════════════════════════════════════════════════
    col_rf, col_td = st.columns([1, 1])

    with col_rf:
        st.subheader("🔽 Rejection Funnel")
        cm2 = cm or {}
        funnel_data = [
            ("Generated",  cm2.get("signals_generated",   0)),
            ("Strategy ✓", cm2.get("strategies_assigned", 0)),
            ("Risk ✓",     cm2.get("risk_approved",       0)),
            ("Sim ✓",      cm2.get("sim_approved",        0)),
            ("Decision ✓", cm2.get("decision_passed",     0)),
            ("Executed",   cm2.get("trades_executed",     0)),
        ]
        base = funnel_data[0][1] or 1
        for i, (label, val) in enumerate(funnel_data):
            prev     = funnel_data[i - 1][1] if i > 0 else val
            drop     = prev - val if i > 0 and prev > 0 else 0
            pct      = val / base * 100
            bar      = "█" * max(int(pct / 5), 0)
            drop_txt = f"  ▼{drop}" if drop > 0 else ""
            drop_col = "#ff6b6b" if drop > 0 else "#aaa"
            fa, fb   = st.columns([3, 1])
            fa.markdown(f"**{label}** `{val}`  {bar}")
            fb.markdown(
                f"<span style='color:{drop_col}'>{pct:.0f}%{drop_txt}</span>",
                unsafe_allow_html=True,
            )

    with col_td:
        st.subheader("🎯 Latest Approved Trade")
        lt = fetch_latest_approved_trade()
        if lt:
            _ec = "#ffd700" if str(lt.get("exec_status", "")).upper() in (
                "DEFERRED", "PENDING", "—") else "#00ff88"
            st.markdown(
                f"<div style='background:#162a47;border-radius:8px;padding:12px;"
                f"border-left:5px solid #00ff88;margin-bottom:10px'>"
                f"<span style='font-size:1.4em;font-weight:bold;color:#00ff88'>"
                f"✅ {lt.get('symbol','—')}</span>"
                f"&nbsp;&nbsp;<span style='color:#aaa'>{lt.get('strategy','—')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            ta, tb, tc = st.columns(3)
            ta.metric("Score",      f"{lt.get('confidence', 0):.2f} / 10")
            tb.metric("R:R",        str(lt.get("rr", "—")))
            tc.metric("Qty",        str(lt.get("qty", "—")))
            td, te, tf = st.columns(3)
            td.metric("Capital %",  str(lt.get("capital_pct", "—")))
            te.metric("Pos Mod",    f"{float(lt.get('position_modifier', 1.0)) * 100:.0f}%")
            tf.metric("Exec Status", str(lt.get("exec_status", "—")))
            if lt.get("rejection_reason"):
                st.markdown(
                    f"<span style='color:#ff6b6b'>Rejection reason: {lt['rejection_reason']}</span>",
                    unsafe_allow_html=True,
                )
            if lt.get("ts"):
                st.caption(f"Decision at {str(lt['ts'])[:19]}")
        else:
            st.info("No approved trade yet today.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # PANEL 4 — Scheduler
    # ══════════════════════════════════════════════════════════════════════
    st.subheader("📅 Scheduler — Today's Cycles")
    sch = fetch_scheduler_status()
    s_cycles = sch.get("cycles", [])
    if s_cycles:
        col_sched, col_next = st.columns([2, 1])
        with col_sched:
            if HAS_PANDAS:
                df_sch = pd.DataFrame(s_cycles)
                st.dataframe(df_sch, hide_index=True, width='stretch',
                             height=min(60 + 35 * len(df_sch), 380))
            else:
                for c in s_cycles:
                    st.write(f"{c['Status']}  `{c['Time']}`  {c['Scan']}")
        with col_next:
            next_name  = sch.get("next_name")
            secs_until = sch.get("secs_until")
            if next_name and secs_until is not None:
                mins = int(secs_until // 60)
                secs = int(secs_until % 60)
                st.markdown(
                    f"<div style='background:#1a2e1a;border-radius:8px;padding:20px;"
                    f"border:2px solid #00ff88;text-align:center'>"
                    f"<div style='color:#aaa;font-size:0.85em;margin-bottom:6px'>Next Cycle</div>"
                    f"<div style='color:#00ff88;font-size:2em;font-weight:bold'>⏱ {mins:02d}:{secs:02d}</div>"
                    f"<div style='color:#fff;font-size:0.9em;margin-top:6px'>"
                    f"{sch.get('next_hhmm','')} — "
                    f"{next_name.replace('_',' ').title()}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:#1a1a2e;border-radius:8px;padding:20px;"
                    "border:2px solid #555;text-align:center'>"
                    "<div style='color:#aaa'>No more cycles today</div>"
                    "<div style='color:#ffd700;font-size:1.3em;margin-top:6px'>🌙 Market Closed</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Schedule not loaded — ensure config.py is present in the project root.")

    st.divider()

    # ── Row 1: Signal Funnel + Strategy Distribution ────────────────────────
    col_funnel, col_strat = st.columns([1, 1])

    with col_funnel:
        st.subheader("Signal Funnel — Current Cycle")
        funnel_stages = [
            ("Generated",    cycle.get("signals_generated",    0)),
            ("Strat Assign", cycle.get("strategies_assigned",  0)),
            ("Risk ✓",       cycle.get("risk_approved",        0)),
            ("Sim ✓",        cycle.get("sim_approved",         0)),
            ("Executed",     cycle.get("trades_executed",      0)),
        ]
        for label, val in funnel_stages:
            base = cycle.get("signals_generated", 0) or 1
            pct  = val / base * 100
            bar  = int(pct / 5) * "█"
            st.markdown(
                f"**{label:<14}** `{val:>3}`  {bar} {pct:.0f}%")

        # Funnel history sparkline
        history = fetch_funnel_history(20)
        if history and HAS_PANDAS:
            df = pd.DataFrame(history[::-1])   # oldest first
            if "trades_executed" in df.columns:
                st.line_chart(df[["signals_generated", "risk_approved",
                                  "trades_executed"]].rename(columns={
                    "signals_generated": "Generated",
                    "risk_approved":     "Risk ✓",
                    "trades_executed":   "Executed",
                }), height=150)

    with col_strat:
        st.subheader("Strategy Distribution")
        strat_data = fetch_strategy_distribution(cycle.get("cycle_id", ""))
        if strat_data and HAS_PANDAS:
            df = pd.DataFrame(strat_data)
            df["avg_conf"] = df["avg_conf"].map(lambda x: f"{x:.2f}")
            st.dataframe(df.rename(columns={
                "strategy": "Strategy",
                "cnt":      "Count",
                "avg_conf": "Avg Conf",
            }), width='stretch', hide_index=True)
        elif strat_data:
            for row in strat_data:
                st.write(f"**{row['strategy']}** — {row['cnt']} signals  "
                         f"(conf ≈ {row['avg_conf']:.2f})")
        else:
            st.info("No strategy data yet for this cycle.")

    st.divider()

    # ── Row 2: Recent Decisions ─────────────────────────────────────────────
    st.subheader("Recent Decisions")
    decisions = fetch_recent_decisions(40)
    if decisions and HAS_PANDAS:
        df = pd.DataFrame(decisions)

        def _colour(val: str) -> str:
            if val == "APPROVED":
                return "color: #00ff88; font-weight: bold"
            if val == "REJECTED":
                return "color: #ff6b6b; font-weight: bold"
            return ""

        styled = df.style.map(_colour, subset=["decision"])
        st.dataframe(styled, width='stretch', hide_index=True,
                     height=min(40 + 35 * len(df), 400))
    elif decisions:
        for d in decisions[:20]:
            icon = "✅" if d["decision"] == "APPROVED" else "❌"
            reason = f" — {d['rejection_reason']}" if d.get("rejection_reason") else ""
            st.write(f"{icon} `{d['ts']}` **{d['symbol']}** "
                     f"{d['strategy']} conf={d.get('confidence',0):.2f}{reason}")
    else:
        st.info("No decisions recorded yet.")

    # Rejection reason summary
    with st.expander("Rejection Reason Breakdown"):
        rej = fetch_rejection_summary()
        if rej and HAS_PANDAS:
            st.bar_chart(
                pd.DataFrame(rej).set_index("reason")["cnt"],
                height=200)
        elif rej:
            for r in rej:
                st.write(f"• {r['reason']}: **{r['cnt']}**")
        else:
            st.info("No rejections yet.")

    st.divider()

    # ── Row 3: Agent Health ─────────────────────────────────────────────────
    st.subheader("Agent Health")
    agents = fetch_agent_stats()
    if agents and HAS_PANDAS:
        df = pd.DataFrame(agents)

        def _age_str(ts_str) -> str:
            """Return human-readable age, e.g. '5m', '2h', '3d'."""
            try:
                ts  = datetime.fromisoformat(str(ts_str)[:26])
                age = (datetime.now() - ts).total_seconds()
                if age < 0:
                    age = abs(age)
                if age < 3600:
                    return f"{int(age/60)}m ago"
                if age < 86400:
                    return f"{int(age/3600)}h ago"
                return f"{int(age/86400)}d ago"
            except Exception:
                return str(ts_str)[:19]

        def _status(row) -> str:
            try:
                ts  = datetime.fromisoformat(str(row["last_seen"])[:26])
                age = (datetime.now() - ts).total_seconds()
                if age < 0:
                    age = abs(age)
            except Exception:
                age = None
            if row["error_count"] > 0 and row["error_count"] > row["event_count"] * 0.05:
                return "⚠️ ERROR"
            if age is not None and age > 86400:   # > 24 h
                return "💤 STANDBY"
            if age is not None and age > 3600:    # > 1 h
                return "🟡 IDLE"
            return "✅ OK"

        df["Age"]    = df["last_seen"].apply(_age_str)
        df["status"] = df.apply(_status, axis=1)
        df = df[["source_agent", "event_count", "error_count", "Age", "status"]]
        df.columns   = ["Agent", "Events", "Errors", "Last Seen", "Status"]
        st.dataframe(df, width='stretch', hide_index=True,
                     height=min(60 + 35 * len(df), 350))
    elif agents:
        for a in agents:
            icon = "⚠️" if a["error_count"] else "✅"
            st.write(f"{icon} **{a['source_agent']}** — "
                     f"{a['event_count']} events | last: {a['last_seen']}")
    else:
        st.info("No agent events recorded yet.")

    st.divider()
    # ── Row 3b: Paper Trades (live CSV) ─────────────────────────────────────
    st.subheader("📋 Paper Trades Log")
    pt_rows = fetch_paper_trades_csv()
    if pt_rows and HAS_PANDAS:
        df_pt = pd.DataFrame(pt_rows)
        # Split into recent (≤3 days) vs legacy (older)
        cutoff_3d = (datetime.now() - __import__('datetime').timedelta(days=3)).strftime("%Y-%m-%d")
        if "timestamp" in df_pt.columns:
            recent_mask = df_pt["timestamp"] >= cutoff_3d
            df_recent  = df_pt[recent_mask]
            df_legacy  = df_pt[~recent_mask]
        else:
            df_recent = df_pt
            df_legacy = pd.DataFrame()

        def _dir_colour(val):
            if str(val).upper() == "BUY":  return "color:#00ff88;font-weight:bold"
            if str(val).upper() == "SELL": return "color:#ff6b6b;font-weight:bold"
            return ""
        def _ev_colour(val):
            if str(val) in ("CLOSE", "CANCELLED"): return "color:#ffd700"
            if str(val) == "OPEN": return "color:#64b5f6"
            return ""

        if not df_recent.empty:
            styled_pt = df_recent.style
            if "direction" in df_recent.columns:
                styled_pt = styled_pt.map(_dir_colour, subset=["direction"])
            if "event" in df_recent.columns:
                styled_pt = styled_pt.map(_ev_colour, subset=["event"])
            st.dataframe(styled_pt, width='stretch', hide_index=True,
                         height=min(60 + 35 * len(df_recent), 400))
            st.caption(f"Showing {len(df_recent)} trades from last 3 days (newest first).")
        else:
            st.info("No paper trades in the last 3 days. Waiting for next cycle.")

        if not df_legacy.empty:
            with st.expander(f"🗂 Legacy positions ({len(df_legacy)} rows — pre-restart, OPEN slots auto-expired)"):
                st.dataframe(df_legacy, width='stretch', hide_index=True,
                             height=min(60 + 35 * len(df_legacy), 300))
                st.caption("These OPEN positions are from a previous container instance and have no effect on current trading.")
    elif pt_rows:
        for r in pt_rows[:20]:
            st.write(r)
    else:
        st.info("No paper trades recorded yet. First trade will appear here automatically.")

    st.divider()
    # ── Row 3c: Paper Trading EOD Report ────────────────────────────
    eod = fetch_paper_trading_eod()
    if eod:
        _today       = eod.get("today",       {})
        _cum         = eod.get("cumulative",  {})
        _pilot_cap   = eod.get("pilot_capital", 100_000)
        _eod_date    = eod.get("date", "—")
        _generated   = eod.get("generated_at", "")
        st.subheader(f"📄 Paper Trading EOD Report — {_eod_date}")
        st.caption(f"Generated at {_generated}  ·  Capital: ₹{_pilot_cap:,.0f}")

        e1, e2, e3, e4, e5, e6 = st.columns(6)
        e1.metric("Today Trades",  _today.get("trades", 0))
        e2.metric("Wins / Losses",
                  f"{_today.get('wins', 0)}W / {_today.get('losses', 0)}L")
        e3.metric("Win Rate",      f"{_today.get('win_rate_pct', 0):.0f}%")
        _pnl = _today.get("net_pnl", 0)
        e4.metric("Today P&L",
                  f"₹{_pnl:+,.0f}",
                  delta=f"{'+'if _pnl>=0 else ''}{_pnl:,.0f}")
        _cum_pnl = _cum.get("cum_pnl", 0)
        e5.metric("Cumul. P&L",
                  f"₹{_cum_pnl:+,.0f}",
                  delta=f"{_cum.get('cum_return_pct', 0):+.2f}%")
        e6.metric("Open Positions", _cum.get("open_trades", 0))

        with st.expander("🧠 AI Self-Evaluation Report (full text)"):
            _report_text = fetch_latest_eod_report_text()
            if _report_text:
                st.text(_report_text)
            else:
                st.info("Report will appear here after the first EOD cycle (15:35).")
    else:
        st.info("📄 EOD report will appear here after 15:35 today."
                "  The orchestrator writes it automatically at end of day.")

    st.divider()
    # ── Row 4: Live Event Stream ────────────────────────────────────────────
    st.subheader("Live Event Stream")
    events = fetch_recent_events(60)
    if events:
        for ev in events:
            pay_str = ev.get("payload", "{}")
            try:
                pay = json.loads(pay_str or "{}")
            except Exception:
                pay = {}
            et  = ev.get("event_type", "")
            src = ev.get("source_agent", "")
            ts  = ev.get("ts", "")

            icon = "🔵"
            if "approved" in et.lower() or "placed" in et.lower():
                icon = "✅"
            elif "rejected" in et.lower() or "fail" in et.lower():
                icon = "❌"
            elif "cycle" in et.lower():
                icon = "🔄"
            elif "order" in et.lower():
                icon = "📋"

            detail = ""
            if pay:
                top = {k: v for k, v in list(pay.items())[:3]}
                detail = "  " + "  ".join(f"{k}={v}" for k, v in top.items())

            st.write(f"{icon} `{ts}` **{et}** _{src}_{detail}")
    else:
        st.info("Waiting for events… start `python main.py` in a terminal.")

    # ── Footer / cycle list ─────────────────────────────────────────────────
    with st.expander("Cycle History (last 20)"):
        history = fetch_cycle_history(20)
        if history and HAS_PANDAS:
            df = pd.DataFrame(history)
            cols = [c for c in ["cycle_id", "started_at", "regime",
                                 "signals_generated", "risk_approved",
                                 "sim_approved", "trades_executed",
                                 "had_error"] if c in df.columns]
            st.dataframe(df[cols], width='stretch', hide_index=True)
        elif history:
            for row in history:
                st.write(row)
        else:
            st.info("No completed cycles yet.")

    # ── Auto-refresh ────────────────────────────────────────────────────────
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(REFRESH_S)
    st.rerun()


# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_dashboard()
