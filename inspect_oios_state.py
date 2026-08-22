"""
Inspect all databases on VPS to understand OIOS data flow.
Reads: signal_births schema, ohlcv_daily presence, ELE scheduling.
"""
import sqlite3, os, glob

BASE = "/root/ai-trading-brain/data"

def check_db(path):
    if not os.path.exists(path):
        print(f"  MISSING: {path}")
        return
    try:
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        print(f"\n  DB: {os.path.basename(path)}")
        print(f"  Tables: {tables}")

        if "signal_births" in tables:
            cols = [r[1] for r in con.execute("PRAGMA table_info(signal_births)").fetchall()]
            print(f"  signal_births cols: {cols}")
            n = con.execute("SELECT COUNT(*) FROM signal_births").fetchone()[0]
            print(f"  signal_births rows: {n}")
            sample = con.execute("""
                SELECT signal_id, symbol, detected_at, current_state, final_state,
                       actual_move_pct, trade_executed, expected_move_direction, birth_price
                FROM signal_births ORDER BY detected_at DESC LIMIT 5
            """).fetchall()
            for r in sample:
                print(f"    [{r['detected_at']}] {r['symbol']} dir={r['expected_move_direction']} "
                      f"price={r['birth_price']} state={r['current_state']} "
                      f"final={r['final_state']} move={r['actual_move_pct']} exec={r['trade_executed']}")

        if "ohlcv_daily" in tables:
            n = con.execute("SELECT COUNT(*) FROM ohlcv_daily").fetchone()[0]
            dates = con.execute("SELECT MIN(trade_date), MAX(trade_date) FROM ohlcv_daily").fetchone()
            syms = con.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv_daily").fetchone()[0]
            print(f"  ohlcv_daily: {n} rows, {syms} symbols, dates {dates[0]} to {dates[1]}")
            # Check if signal_births symbols are covered
            if "signal_births" in tables:
                sb_syms = [r[0] for r in con.execute("SELECT DISTINCT symbol FROM signal_births").fetchall()]
                covered = 0
                for sym in sb_syms[:20]:
                    has_data = con.execute("SELECT COUNT(*) FROM ohlcv_daily WHERE symbol=?", (sym,)).fetchone()[0]
                    if has_data > 0:
                        covered += 1
                print(f"  ohlcv coverage: {covered}/{min(20, len(sb_syms))} checked symbols have data")

        if "opportunities" in tables:
            n = con.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            states = {r[0]: r[1] for r in con.execute("SELECT current_state, COUNT(*) FROM opportunities GROUP BY current_state").fetchall()}
            print(f"  opportunities: {n} rows, states: {states}")

        if "trading_calendar" in tables:
            n = con.execute("SELECT COUNT(*) FROM trading_calendar").fetchone()[0]
            dates = con.execute("SELECT MIN(calendar_date), MAX(calendar_date) FROM trading_calendar WHERE is_trading_day=1").fetchone()
            print(f"  trading_calendar: {n} rows, trading days {dates[0]} to {dates[1]}")

        con.close()
    except Exception as e:
        print(f"  ERROR reading {path}: {e}")

print("=== DATABASE INVENTORY ===")
dbs = sorted(glob.glob(f"{BASE}/*.db") + glob.glob(f"{BASE}/**/*.db"))
for db in dbs:
    check_db(db)

print("\n\n=== OIOS CONFIG / SCHEDULER ===")
# Check if ELE is being called from orchestrator
for f in [
    "/root/ai-trading-brain/orchestrator/master_orchestrator.py",
    "/root/ai-trading-brain/oios/engine/ele.py",
]:
    if os.path.exists(f):
        with open(f) as fp:
            content = fp.read()
        # Look for ELE calls
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'ele' in line.lower() and ('run' in line.lower() or 'cycle' in line.lower() or 'call' in line.lower()):
                print(f"  {f}:{i+1}: {line.strip()}")

print("\n=== OIOS DB PATH CONFIGURATION ===")
for f in glob.glob("/root/ai-trading-brain/oios/**/*.py", recursive=True):
    with open(f) as fp:
        content = fp.read()
    if 'market_behavior.db' in content or 'replay.db' in content or 'oios.db' in content or 'DB_PATH' in content or 'db_path' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if any(x in line for x in ['market_behavior.db', 'replay.db', 'oios.db', 'DB_PATH', 'db_path', 'DB =', 'DATABASE']):
                print(f"  {f}:{i+1}: {line.strip()}")
