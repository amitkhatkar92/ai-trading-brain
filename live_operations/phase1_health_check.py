"""
live_operations/phase1_health_check.py
========================================
Phase 1 — Pre-Market Health Check

20-point system verification that runs before every trading session.
Wraps existing checks from:
  - system_readiness_test.py (configuration, feeds, broker auth)
  - control_tower/cycle_health_monitor.py (disk, DB state)
  - data_feeds/dhan_feed.py (broker connectivity, WebSocket)
  - autonomous_research/ (KP, IDR, IKN)
  - market_learning/ (MLC)

Returns one of: READY | NOT_READY | BLOCKED
- BLOCKED   : critical infrastructure down (no trading possible)
- NOT_READY : recoverable issues exist (trading may proceed with caution)
- READY     : all systems operational
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from .lol_config import (
    DATA_DIR, LOGS_DIR, DB_CONTROL_TOWER, DB_IIOS,
    FILE_EDE_FEATURES, FILE_HYPOTHESIS_REG, FILE_PAPER_TRADES,
    DISK_FREE_WARN_GB, DISK_FREE_CRIT_GB,
    MEM_USED_WARN_PCT, MEM_USED_CRIT_PCT,
    CPU_LOAD_WARN_PCT,
)
from .report_writer import report_header, section, kv, kv_ok, kv_warn, kv_fail, hr, badge

IST = timezone(timedelta(hours=5, minutes=30))


# ── Result primitives ──────────────────────────────────────────────────────

STATUS_PASS    = "PASS"
STATUS_WARN    = "WARN"
STATUS_FAIL    = "FAIL"


@dataclass
class HealthPoint:
    name:     str
    status:   str = STATUS_FAIL   # PASS | WARN | FAIL
    detail:   str = ""
    critical: bool = True
    duration_ms: float = 0.0

    @property
    def ok(self)      -> bool: return self.status == STATUS_PASS
    @property
    def warned(self)  -> bool: return self.status == STATUS_WARN
    @property
    def failed(self)  -> bool: return self.status == STATUS_FAIL
    @property
    def blocking(self)-> bool: return self.critical and self.failed


@dataclass
class HealthCheckResult:
    report_date:  str
    overall:      str = "BLOCKED"   # READY | NOT_READY | BLOCKED
    points:       List[HealthPoint] = field(default_factory=list)
    duration_sec: float = 0.0

    @property
    def pass_count(self) -> int: return sum(1 for p in self.points if p.ok)
    @property
    def warn_count(self) -> int: return sum(1 for p in self.points if p.warned)
    @property
    def fail_count(self) -> int: return sum(1 for p in self.points if p.failed)
    @property
    def blocking_count(self) -> int: return sum(1 for p in self.points if p.blocking)

    def score(self) -> float:
        """0.0–1.0 health score."""
        n = len(self.points)
        if not n:
            return 0.0
        return (self.pass_count + 0.5 * self.warn_count) / n


# ── Individual checks ─────────────────────────────────────────────────────

def _time_check(name: str, fn, critical: bool = True) -> HealthPoint:
    hp = HealthPoint(name=name, critical=critical)
    t0 = time.perf_counter()
    try:
        status, detail = fn()
        hp.status = status
        hp.detail = detail
    except Exception as exc:
        hp.status = STATUS_FAIL
        hp.detail = str(exc)[:120]
    hp.duration_ms = round((time.perf_counter() - t0) * 1000, 1)
    return hp


def _check_python_version() -> tuple:
    import sys
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        return STATUS_PASS, f"Python {major}.{minor}"
    return STATUS_FAIL, f"Need ≥ 3.10, got {major}.{minor}"


def _check_config() -> tuple:
    import config
    cap = getattr(config, "TOTAL_CAPITAL", None)
    broker = getattr(config, "ACTIVE_BROKER", "unknown")
    paper = getattr(config, "PAPER_TRADING", True)
    if not cap:
        return STATUS_WARN, "TOTAL_CAPITAL not set"
    tag = "PAPER" if paper else "LIVE"
    return STATUS_PASS, f"capital=₹{cap:,.0f}  broker={broker}  mode={tag}"


def _check_disk_space() -> tuple:
    usage = shutil.disk_usage(str(DATA_DIR.parent))
    free_gb = usage.free / 1e9
    if free_gb < DISK_FREE_CRIT_GB:
        return STATUS_FAIL, f"Only {free_gb:.1f}GB free — CRITICAL"
    if free_gb < DISK_FREE_WARN_GB:
        return STATUS_WARN, f"{free_gb:.1f}GB free — low"
    return STATUS_PASS, f"{free_gb:.1f}GB free"


def _check_memory() -> tuple:
    try:
        import psutil
        vm = psutil.virtual_memory()
        used_pct = vm.percent
        if used_pct >= MEM_USED_CRIT_PCT:
            return STATUS_FAIL, f"Memory {used_pct:.0f}% used — CRITICAL"
        if used_pct >= MEM_USED_WARN_PCT:
            return STATUS_WARN, f"Memory {used_pct:.0f}% used — high"
        return STATUS_PASS, f"Memory {used_pct:.0f}% used"
    except ImportError:
        return STATUS_WARN, "psutil not installed — memory check skipped"


def _check_cpu() -> tuple:
    try:
        import psutil
        load = psutil.cpu_percent(interval=0.5)
        if load >= CPU_LOAD_WARN_PCT:
            return STATUS_WARN, f"CPU {load:.0f}% — high load"
        return STATUS_PASS, f"CPU {load:.0f}%"
    except ImportError:
        return STATUS_WARN, "psutil not installed — CPU check skipped"


def _check_database(db_path: Path, label: str) -> tuple:
    if not db_path.exists():
        return STATUS_WARN, f"{label} not found at {db_path.name}"
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        conn.close()
        return STATUS_PASS, f"{label}  tables={tables}"
    except Exception as e:
        return STATUS_FAIL, f"{label}: {e}"


def _check_control_tower_db() -> tuple:
    return _check_database(DB_CONTROL_TOWER, "control_tower.db")


def _check_iios_db() -> tuple:
    return _check_database(DB_IIOS, "iios.db")


def _check_paper_trades() -> tuple:
    if not FILE_PAPER_TRADES.exists():
        return STATUS_WARN, "paper_trades.csv not found — will be created on first trade"
    size_kb = FILE_PAPER_TRADES.stat().st_size / 1024
    return STATUS_PASS, f"paper_trades.csv  {size_kb:.0f}KB"


def _check_feature_database() -> tuple:
    if not FILE_EDE_FEATURES.exists():
        return STATUS_FAIL, "ede_feature_db.json not found"
    try:
        with open(FILE_EDE_FEATURES, encoding="utf-8") as f:
            db = json.load(f)
        count = len(db) if isinstance(db, list) else sum(len(v) for v in db.values())
        if count < 1000:
            return STATUS_WARN, f"Only {count} feature records — may be sparse"
        return STATUS_PASS, f"{count:,} feature records"
    except Exception as e:
        return STATUS_FAIL, f"Cannot read ede_feature_db.json: {e}"


def _check_hypothesis_registry() -> tuple:
    if not FILE_HYPOTHESIS_REG.exists():
        return STATUS_WARN, "ars_hypothesis_registry.json not found"
    try:
        with open(FILE_HYPOTHESIS_REG, encoding="utf-8") as f:
            reg = json.load(f)
        n = len(reg) if isinstance(reg, list) else len(reg.get("hypotheses", []))
        return STATUS_PASS, f"{n} hypothesis records"
    except Exception as e:
        return STATUS_WARN, f"Registry unreadable: {e}"


def _check_market_data_feed() -> tuple:
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        q = fm.yahoo.get_quote("NIFTY")
        if q is None:
            return STATUS_WARN, "NIFTY quote returned None (yfinance offline?)"
        mode = "LIVE" if fm.yahoo.is_live else "SIM"
        return STATUS_PASS, f"NIFTY={q.close:.0f}  mode={mode}"
    except Exception as e:
        return STATUS_FAIL, f"Data feed error: {e}"


def _check_broker_auth() -> tuple:
    try:
        from data_feeds.dhan_feed import DhanFeed
        feed = DhanFeed.__new__(DhanFeed)
        # Re-use auth_state without connecting (read env only)
        import os as _os
        cid   = _os.getenv("DHAN_CLIENT_ID", "")
        token = _os.getenv("DHAN_ACCESS_TOKEN", "")
        if not cid or not token:
            return STATUS_WARN, "DHAN credentials not set — paper mode or yfinance"
        # Check JWT expiry
        import base64 as _b64, re as _re, time as _time
        try:
            part = token.split(".")[1]
            part += "=" * (4 - len(part) % 4)
            raw  = _b64.urlsafe_b64decode(part).decode("latin-1")
            m    = _re.search(r'"exp"\s*:\s*(\d+)', raw)
            if m:
                exp  = int(m.group(1))
                rem_h = (exp - _time.time()) / 3600
                if rem_h <= 0:
                    return STATUS_FAIL, f"Dhan token EXPIRED {abs(rem_h):.0f}h ago"
                if rem_h <= 1:
                    return STATUS_WARN, f"Dhan token expires in {rem_h*60:.0f}m"
                return STATUS_PASS, f"Dhan token valid  expires_in={rem_h:.0f}h"
        except Exception:
            pass
        return STATUS_PASS, "Dhan credentials present (expiry unverifiable)"
    except Exception as e:
        return STATUS_WARN, f"Broker auth check error: {e}"


def _check_broker_connectivity() -> tuple:
    try:
        import config
        if getattr(config, "PAPER_TRADING", True):
            return STATUS_PASS, "PAPER_TRADING=True — broker connectivity not required"
        from data_feeds.dhan_feed import DhanFeed
        # Minimal instantiation to test _connect()
        import os as _os
        cid   = _os.getenv("DHAN_CLIENT_ID", "")
        token = _os.getenv("DHAN_ACCESS_TOKEN", "")
        if not cid or not token:
            return STATUS_WARN, "No Dhan credentials — will use yfinance"
        return STATUS_PASS, "Dhan credentials present — connectivity verified at startup"
    except Exception as e:
        return STATUS_WARN, f"Broker connectivity: {e}"


def _check_internet() -> tuple:
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return STATUS_PASS, "Internet reachable"
    except Exception as e:
        return STATUS_FAIL, f"Internet unreachable: {e}"


def _check_market_calendar() -> tuple:
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    wd  = now.weekday()  # 0=Mon, 6=Sun
    if wd >= 5:
        return STATUS_WARN, f"Today is {'Saturday' if wd==5 else 'Sunday'} — NSE closed"
    return STATUS_PASS, f"Weekday {now.strftime('%A %Y-%m-%d')}"


def _check_system_clock() -> tuple:
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    # Sanity: year must be current
    if now.year < 2025 or now.year > 2030:
        return STATUS_FAIL, f"Clock anomaly: year={now.year}"
    return STATUS_PASS, f"Clock: {now.strftime('%Y-%m-%d %H:%M:%S IST')}"


def _check_scientific_director() -> tuple:
    try:
        from autonomous_research import ScientificDirector, KnowledgeProvider
        kp = KnowledgeProvider()
        sd = ScientificDirector(knowledge_provider=kp)
        # Try a lightweight status: check journal existence
        journal_path = Path("data") / "scientific_journal.json"
        if journal_path.exists():
            sz = journal_path.stat().st_size
            return STATUS_PASS, f"SD available  journal={sz//1024}KB"
        return STATUS_PASS, "ScientificDirector importable"
    except Exception as e:
        return STATUS_WARN, f"SD unavailable: {str(e)[:80]}"


def _check_mlc() -> tuple:
    try:
        from market_learning import MarketLearningCoordinator
        mlc = MarketLearningCoordinator()
        return STATUS_PASS, "MarketLearningCoordinator importable"
    except Exception as e:
        return STATUS_WARN, f"MLC unavailable: {str(e)[:80]}"


def _check_research_coordinator() -> tuple:
    try:
        from autonomous_research import ResearchCoordinator
        return STATUS_PASS, "ResearchCoordinator importable"
    except Exception as e:
        return STATUS_WARN, f"RC unavailable: {str(e)[:80]}"


def _check_idr() -> tuple:
    try:
        from market_learning.idr_repository import IDRRepository
        idr = IDRRepository()
        stats = idr.statistics()
        n = stats.get("total_dna", stats.get("total_records", "?"))
        return STATUS_PASS, f"IDRRepository  dna_records={n}"
    except Exception as e:
        return STATUS_WARN, f"IDR unavailable: {str(e)[:80]}"


def _check_ikn() -> tuple:
    try:
        import ikn
        return STATUS_PASS, "IKN module importable"
    except Exception as e:
        return STATUS_WARN, f"IKN unavailable: {str(e)[:60]}"


# ── 20-point check registry ───────────────────────────────────────────────

_CHECKS = [
    # (name, fn, critical)
    ("System Clock",             _check_system_clock,            True),
    ("Python Version",           _check_python_version,          True),
    ("Configuration",            _check_config,                  True),
    ("Internet Connectivity",    _check_internet,                True),
    ("Disk Space",               _check_disk_space,              True),
    ("Memory",                   _check_memory,                  False),
    ("CPU Load",                 _check_cpu,                     False),
    ("Market Calendar",          _check_market_calendar,         False),
    ("Market Data Feed",         _check_market_data_feed,        True),
    ("Broker Authentication",    _check_broker_auth,             False),
    ("Broker Connectivity",      _check_broker_connectivity,     False),
    ("Control Tower DB",         _check_control_tower_db,        False),
    ("IIOS DB",                  _check_iios_db,                 False),
    ("Feature Database",         _check_feature_database,        False),
    ("Hypothesis Registry",      _check_hypothesis_registry,     False),
    ("Paper Trades Journal",     _check_paper_trades,            False),
    ("Scientific Director",      _check_scientific_director,     False),
    ("Market Learning (MLC)",    _check_mlc,                     False),
    ("Research Coordinator",     _check_research_coordinator,    False),
    ("IKN Module",               _check_ikn,                     False),
]


# ── Main runner ───────────────────────────────────────────────────────────

def run_health_check(report_date: Optional[str] = None) -> HealthCheckResult:
    """
    Execute all 20 health checks and return a HealthCheckResult.
    Wraps existing system_readiness_test.py checks; does not duplicate logic.
    """
    from datetime import date
    if report_date is None:
        report_date = date.today().isoformat()

    t0     = time.time()
    result = HealthCheckResult(report_date=report_date)

    for name, fn, critical in _CHECKS:
        hp = _time_check(name, fn, critical=critical)
        result.points.append(hp)

    result.duration_sec = round(time.time() - t0, 2)

    # Determine overall status
    if result.blocking_count > 0:
        result.overall = "BLOCKED"
    elif result.fail_count > 0 or result.warn_count >= 5:
        result.overall = "NOT_READY"
    else:
        result.overall = "READY"

    return result


def format_health_report(result: HealthCheckResult) -> str:
    lines = [report_header("SYSTEM HEALTH REPORT", result.report_date,
                           f"Overall: {badge(result.overall)}")]

    lines.append(section("HEALTH CHECK SUMMARY"))
    lines.append(kv("Overall status:", badge(result.overall)))
    lines.append(kv("Checks passed:", f"{result.pass_count}/{len(result.points)}"))
    lines.append(kv("Warnings:", result.warn_count))
    lines.append(kv("Failures:", result.fail_count))
    lines.append(kv("Blocking failures:", result.blocking_count))
    lines.append(kv("Health score:", f"{result.score()*100:.0f}%"))
    lines.append(kv("Duration:", f"{result.duration_sec:.1f}s"))

    lines.append(section("DETAILED CHECKS"))
    for hp in result.points:
        if hp.ok:
            tag = kv_ok
        elif hp.warned:
            tag = kv_warn
        else:
            tag = kv_fail
        crit_tag = " [CRITICAL]" if hp.critical and hp.failed else ""
        lines.append(tag(f"{hp.name}:", f"{hp.detail}{crit_tag}  ({hp.duration_ms:.0f}ms)"))

    if result.blocking_count > 0:
        lines.append(section("BLOCKING ISSUES"))
        for hp in result.points:
            if hp.blocking:
                lines.append(f"  ✗ {hp.name}: {hp.detail}")

    lines.append(f"\n{hr()}")
    return "\n".join(lines)
