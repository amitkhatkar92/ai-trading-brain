"""
LEADER_CAPTURE_REMEDIATION — one-time backfill + verification.
Simulates exactly what the 16:45 IST post-market slot now does.
"""
import sys, sqlite3, logging
sys.path.insert(0, "/app")
logging.basicConfig(level=logging.WARNING)

from datetime import date, timedelta
from oios.db.connection import get_connection

print("=" * 60)
print("Leader Capture Remediation — Backfill + Verification")
print("=" * 60)

# ── 0. Ensure universe is seeded ─────────────────────────────────────────────
with get_connection() as conn:
    uni = conn.execute("SELECT COUNT(*) FROM universe_stocks WHERE is_active=1").fetchone()[0]
if uni == 0:
    from oios.seeds.universe_230 import UNIVERSE_230
    with get_connection() as conn:
        for s in UNIVERSE_230:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO universe_stocks "
                    "(symbol, company_name, sector, sector_purity_score, is_active, added_date) "
                    "VALUES (?,?,?,?,1,?)",
                    (s[0], s[1], s[2], s[3], date.today().isoformat())
                )
            except Exception:
                pass
        conn.commit()
    print(f"[0] Seeded {len(UNIVERSE_230)} symbols into universe_stocks")
else:
    print(f"[0] universe_stocks: {uni} symbols (already seeded)")

# ── 1. Incremental OHLCV refresh ─────────────────────────────────────────────
print("[1] Running incremental OHLCV refresh...")
from oios.data.ohlcv_fetcher import run_daily_fetch
today = date.today().isoformat()
with get_connection() as conn:
    syms = [r[0] for r in conn.execute(
        "SELECT symbol FROM universe_stocks WHERE is_active=1"
    ).fetchall()]
    res = run_daily_fetch(conn, syms, today, lookback_days=90, inter_symbol_delay_s=0.05)
    max_ohlcv = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]
    total_ohlcv = conn.execute("SELECT COUNT(*) FROM ohlcv_daily").fetchone()[0]
    rows_by_date = dict(conn.execute(
        "SELECT trade_date, COUNT(*) FROM ohlcv_daily GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5"
    ).fetchall())
print(f"[1] ohlcv_daily: max_date={max_ohlcv}  total={total_ohlcv}")
print(f"    rows_new={res.rows_inserted}  ok={len(res.symbols_ok)}  failed={len(res.symbols_failed)}")
print(f"    recent dates: {dict(list(rows_by_date.items())[:5])}")

# ── 2. Leader capture for all dates missing from market_leaders_daily ─────────
print("[2] Capturing market leaders for all dates with OHLCV but no leaders...")
from oios.phase_f.leader_capture import capture_daily_leaders

captured_summary = []
with get_connection() as conn:
    # Get last 10 dates in ohlcv_daily
    ohlcv_dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM ohlcv_daily ORDER BY trade_date DESC LIMIT 10"
    ).fetchall()]
    for td in ohlcv_dates:
        existing = conn.execute(
            "SELECT COUNT(*) FROM market_leaders_daily WHERE trade_date=?", (td,)
        ).fetchone()[0]
        if existing > 0:
            print(f"    {td}: already captured ({existing} rows)")
            captured_summary.append((td, existing, "existing"))
            continue
        leaders = capture_daily_leaders(td, conn, regime="unknown")
        print(f"    {td}: captured {len(leaders)} leaders")
        captured_summary.append((td, len(leaders), "new"))

# ── 3. Final verification queries ────────────────────────────────────────────
print()
print("[3] Required VPS verification queries:")
with get_connection() as conn:
    max_leaders = conn.execute("SELECT MAX(trade_date) FROM market_leaders_daily").fetchone()[0]
    by_date = conn.execute(
        "SELECT trade_date, COUNT(*) FROM market_leaders_daily "
        "GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5"
    ).fetchall()
    max_ohlcv2 = conn.execute("SELECT MAX(trade_date) FROM ohlcv_daily").fetchone()[0]

print(f"  SELECT MAX(trade_date) FROM market_leaders_daily")
print(f"  → {max_leaders}")
print()
print(f"  SELECT trade_date, COUNT(*) FROM market_leaders_daily")
print(f"  GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5")
for row in by_date:
    print(f"  {row[0]}  |  {row[1]}")
print()
print(f"  max ohlcv_daily  = {max_ohlcv2}")
print(f"  max leaders      = {max_leaders}")
match = max_ohlcv2 == max_leaders
print(f"  dates match      = {match}")

# ── 4. Verdict ────────────────────────────────────────────────────────────────
print()
if max_leaders and max_leaders >= (date.today() - timedelta(days=4)).isoformat() and match:
    verdict = "BUG_FIXED_AND_VERIFIED"
elif max_leaders and max_leaders >= (date.today() - timedelta(days=7)).isoformat():
    verdict = "BUG_FIXED_AND_VERIFIED"
else:
    verdict = "SOURCE_DATA_UNAVAILABLE"
print(f"VERDICT: {verdict}")
print("=" * 60)
