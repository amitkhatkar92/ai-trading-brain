"""
System Readiness Test
=====================
Pre-flight checklist that validates all 13 integration components
before the first pilot trade.

Usage::
    python system_readiness_test.py
    python system_readiness_test.py --quiet    # JSON-only output
    python system_readiness_test.py --fail-fast

Exit codes
----------
0 — All critical checks passed (READY FOR PILOT)
1 — One or more critical checks failed (NOT READY)
"""

from __future__ import annotations
import sys
import os
import json
import importlib
import argparse
from datetime import datetime
from typing import List, Tuple, Optional

# ── Ensure project root on sys.path ────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Helpers ────────────────────────────────────────────────────────────────

CHECK_OK   = "✅ PASS"
CHECK_WARN = "⚠️  WARN"
CHECK_FAIL = "❌ FAIL"


def _r(status: str, detail: str = "") -> Tuple[str, str]:
    return status, detail


class CheckResult:
    def __init__(self, name: str, critical: bool = True):
        self.name     = name
        self.critical = critical
        self.status   = "NOT_RUN"
        self.detail   = ""

    def passed(self, detail: str = "") -> "CheckResult":
        self.status = CHECK_OK; self.detail = detail; return self

    def warned(self, detail: str = "") -> "CheckResult":
        self.status = CHECK_WARN; self.detail = detail; return self

    def failed(self, detail: str = "") -> "CheckResult":
        self.status = CHECK_FAIL; self.detail = detail; return self

    @property
    def ok(self) -> bool:
        return self.status == CHECK_OK

    @property
    def blocking(self) -> bool:
        return self.critical and self.status == CHECK_FAIL


def check(name: str, critical: bool = True) -> CheckResult:
    return CheckResult(name, critical)


# ══════════════════════════════════════════════════════════════════════════
#  Individual checks
# ══════════════════════════════════════════════════════════════════════════

def check_python_version() -> CheckResult:
    c = check("Python version")
    major, minor = sys.version_info[:2]
    ver = f"{major}.{minor}"
    if major >= 3 and minor >= 10:
        return c.passed(f"Python {ver}")
    return c.failed(f"Need ≥ 3.10, got {ver}")


def check_config() -> CheckResult:
    c = check("Config loaded")
    try:
        import config
        cap = getattr(config, "TOTAL_CAPITAL", None)
        if cap:
            return c.passed(f"TOTAL_CAPITAL=₹{cap:,.0f}")
        return c.warned("TOTAL_CAPITAL not set — using default")
    except Exception as e:
        return c.failed(str(e))


def check_yahoo_feed() -> CheckResult:
    c = check("Yahoo data feed", critical=False)
    try:
        from data_feeds import get_feed_manager
        fm  = get_feed_manager()
        q   = fm.yahoo.get_quote("SP500")
        if q:
            live_tag = "LIVE" if fm.yahoo.is_live else "SIM"
            return c.passed(f"SP500={q.close:.0f}  [{live_tag}]")
        return c.warned("Quote returned None")
    except Exception as e:
        return c.warned(f"{e}")


def check_nse_feed() -> CheckResult:
    c = check("NSE data feed", critical=False)
    try:
        from data_feeds import get_feed_manager
        fm   = get_feed_manager()
        q    = fm.nse.get_quote("NIFTY")
        mode = fm.status().nse_mode
        if q:
            return c.passed(f"NIFTY={q.close:.0f}  [{mode}]")
        return c.warned(f"NSE quote returned None [{mode}]")
    except Exception as e:
        return c.warned(str(e))


def check_options_chain() -> CheckResult:
    c = check("Options chain feed", critical=False)
    try:
        from data_feeds import get_feed_manager
        fm   = get_feed_manager()
        snap = fm.get_options_snapshot("NIFTY")
        pcr  = snap.get("pcr", 0)
        if pcr:
            return c.passed(f"NIFTY PCR={pcr:.2f}  ATM_IV={snap.get('atm_iv', 0):.1f}%")
        return c.warned("Options snapshot empty")
    except Exception as e:
        return c.warned(str(e))


def check_database() -> CheckResult:
    c = check("Database (SQLite)")
    try:
        from database import get_db
        db   = get_db()
        db.log_event("system", "READINESS_CHECK", "system readiness test")
        summ = db.get_summary_stats()
        return c.passed(f"tables OK  trades={summ.get('total_trades', 0)}")
    except Exception as e:
        return c.failed(str(e))


def check_transaction_costs() -> CheckResult:
    c = check("Transaction cost model")
    try:
        from models.transaction_costs import get_cost_model, InstrumentType
        model = get_cost_model()
        cb    = model.compute("NIFTY", 50, 22000, 22100, InstrumentType.EQUITY_INTRADAY)
        return c.passed(f"round-trip cost=₹{cb.total_cost:.2f}  "
                        f"cost_pct={cb.cost_pct:.4f}%")
    except Exception as e:
        return c.failed(str(e))


def check_notifications() -> CheckResult:
    c = check("Notification system", critical=False)
    try:
        import config
        token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
        cid   = getattr(config, "TELEGRAM_CHAT_ID",   "")
        if token and cid:
            return c.passed("Telegram configured ✔")
        return c.warned("Telegram not configured — log-only mode (set TELEGRAM_BOT_TOKEN)")
    except Exception as e:
        return c.warned(str(e))


def check_broker_config() -> CheckResult:
    c = check("Broker config")
    try:
        import config
        broker  = getattr(config, "ACTIVE_BROKER", "none")
        keys = {
            "zerodha":  getattr(config, "ZERODHA_API_KEY",  "") or
                        os.getenv("ZERODHA_API_KEY", ""),
            "dhan":     getattr(config, "DHAN_CLIENT_ID",   "") or
                        os.getenv("DHAN_CLIENT_ID",   ""),
            "angelone": getattr(config, "ANGELONE_API_KEY", "") or
                        os.getenv("ANGELONE_API_KEY",  ""),
        }
        paper_mode = getattr(config, "PAPER_TRADING", True)
        if paper_mode:
            return c.warned(f"Broker={broker}  PAPER_TRADING=True "
                             "(OK for pilot — no live orders)")
        for name, key in keys.items():
            if key:
                return c.passed(f"ACTIVE_BROKER={broker}  key present")
        return c.failed("No broker API keys found and PAPER_TRADING=False")
    except Exception as e:
        return c.failed(str(e))


def check_paper_trading() -> CheckResult:
    c = check("Paper trading mode")
    try:
        import config
        flag = getattr(config, "PAPER_TRADING", True)
        if flag:
            return c.passed("PAPER_TRADING=True ✔ (recommended for first 2–4 weeks)")
        return c.warned("PAPER_TRADING=False — live orders WILL be sent!")
    except Exception as e:
        return c.failed(str(e))


def check_pilot_config() -> CheckResult:
    c = check("Pilot capital config")
    try:
        from pilot import PILOT_CAPITAL, PILOT_RISK_PCT, PILOT_MAX_TRADES
        risk_rs = PILOT_CAPITAL * PILOT_RISK_PCT
        if risk_rs > 500:
            return c.warned(f"Risk/trade=₹{risk_rs:.0f} — consider lowering "
                             f"(safe max ₹100 for ₹20k capital)")
        return c.passed(
            f"capital=₹{PILOT_CAPITAL:,.0f}  "
            f"risk/trade=₹{risk_rs:.0f} ({PILOT_RISK_PCT*100:.1f}%)  "
            f"max_trades={PILOT_MAX_TRADES}"
        )
    except Exception as e:
        return c.failed(str(e))


def check_paper_broker() -> CheckResult:
    c = check("Paper broker (PaperTradingController)")
    try:
        from pilot import get_paper_broker
        pb   = get_paper_broker()
        snap = pb.get_portfolio_snapshot()
        return c.passed(f"portfolio_value=₹{snap['portfolio_value']:,.0f}  "
                        f"drawdown={snap['drawdown_pct']:.1f}%")
    except Exception as e:
        return c.failed(str(e))


def check_risk_guardian() -> CheckResult:
    c = check("Risk Guardian")
    try:
        import config
        max_dd   = getattr(config, "MAX_DRAWDOWN_PCT",     0)
        max_risk = getattr(config, "MAX_RISK_PER_TRADE_PCT", 0)
        if max_dd and max_risk:
            return c.passed(f"MAX_DRAWDOWN={max_dd:.0%}  MAX_RISK_PER_TRADE={max_risk:.2%}")
        return c.warned("Risk config missing — check MAX_DRAWDOWN_PCT in config.py")
    except Exception as e:
        return c.failed(str(e))


def check_edge_discovery() -> CheckResult:
    c = check("Edge Discovery Engine (EDE)", critical=False)
    try:
        from database import get_db
        db    = get_db()
        rows  = db.get_open_edges() if hasattr(db, "get_open_edges") else []
        count = len(rows)
        return c.passed(f"{count} active edges in DB")
    except Exception as e:
        # EDE may use a separate DB — not blocking
        return c.warned(str(e))


def check_expectancy_model() -> CheckResult:
    c = check("Expectancy model")
    try:
        from models.trade_expectancy import ExpectancyCalculator
        calc  = ExpectancyCalculator()
        exp   = calc.expectancy_r(win_rate=0.45, avg_win_r=2.2, avg_loss_r=1.0)
        bwr   = calc.breakeven_win_rate(rr_ratio=2.2)
        return c.passed(f"Exp(45%,RR=2.2)={exp:+.3f}R  BEV_WR={bwr:.1%}")
    except Exception as e:
        return c.failed(str(e))


def check_scheduler() -> CheckResult:
    c = check("Schedule config", critical=False)
    try:
        import config
        sched = getattr(config, "SCHEDULE", None)
        if sched:
            return c.passed(f"SCHEDULE={sched}")
        return c.warned("SCHEDULE not defined in config.py")
    except Exception as e:
        return c.warned(str(e))


def check_control_tower_db() -> CheckResult:
    c = check("Control Tower DB", critical=False)
    try:
        import sqlite3, os
        db_path = os.path.join(ROOT, "data", "control_tower.db")
        if not os.path.exists(db_path):
            return c.warned(f"Not found: {db_path}")
        conn  = sqlite3.connect(db_path)
        cur   = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()
        return c.passed(f"tables={tables}")
    except Exception as e:
        return c.warned(str(e))


def check_orchestrator_importable() -> CheckResult:
    c = check("Master orchestrator")
    try:
        import orchestrator.master_orchestrator
        return c.passed("import OK")
    except Exception as e:
        return c.failed(str(e))


# ══════════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════════

ALL_CHECKS = [
    check_python_version,
    check_config,
    check_yahoo_feed,
    check_nse_feed,
    check_options_chain,
    check_database,
    check_transaction_costs,
    check_notifications,
    check_broker_config,
    check_paper_trading,
    check_pilot_config,
    check_paper_broker,
    check_risk_guardian,
    check_edge_discovery,
    check_expectancy_model,
    check_scheduler,
    check_control_tower_db,
    check_orchestrator_importable,
]


def run_all(fail_fast: bool = False, quiet: bool = False) -> List[CheckResult]:
    results: List[CheckResult] = []
    for fn in ALL_CHECKS:
        name = fn.__name__.replace("check_", "").replace("_", " ").title()
        try:
            res = fn()
        except Exception as exc:
            res = CheckResult(name, critical=True)
            res.failed(str(exc))
        if not quiet:
            print(f"  {res.status:<10}  {res.name:<40}  {res.detail}")
        results.append(res)
        if fail_fast and res.blocking:
            if not quiet:
                print("\n  ⚡ --fail-fast triggered, stopping early.")
            break
    return results


def print_summary(results: List[CheckResult]) -> int:
    total    = len(results)
    passed   = sum(1 for r in results if r.ok)
    warned   = sum(1 for r in results if r.status == CHECK_WARN)
    failed   = sum(1 for r in results if r.status == CHECK_FAIL)
    blocking = sum(1 for r in results if r.blocking)

    print("\n" + "━" * 65)
    print(f"  Checks: {total}   Pass: {passed}   Warn: {warned}   Fail: {failed}")
    print("━" * 65)

    if blocking == 0:
        print("  🚀  ALL CRITICAL CHECKS PASSED — READY FOR PILOT TRADING")
        if warned:
            print(f"  ⚠️   {warned} warning(s) — review before going live")
    else:
        print(f"  🛑  {blocking} CRITICAL FAILURE(S) — NOT READY")
        print("     Fix the ❌ FAIL items above before trading.")
    print("━" * 65)
    return 0 if blocking == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Trading Brain — System Readiness Check"
    )
    parser.add_argument("--fail-fast", action="store_true",
                        help="Stop at first critical failure")
    parser.add_argument("--quiet",     action="store_true",
                        help="Suppress per-check output, print JSON summary")
    parser.add_argument("--json",      action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    if not args.quiet:
        print("\n" + "═" * 65)
        print("  AI Trading Brain — System Readiness Test")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("═" * 65)

    results = run_all(fail_fast=args.fail_fast, quiet=args.quiet)

    if args.json or args.quiet:
        out = [
            {"check": r.name, "status": r.status,
             "detail": r.detail, "critical": r.critical}
            for r in results
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))

    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
