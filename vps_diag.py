import sqlite3, json, os, csv
from datetime import datetime, timedelta

cutoff = (datetime.now() - timedelta(days=12)).isoformat()[:10]

print(f"=== Cutoff: {cutoff} | Now: {datetime.now().date()} ===")

# paper trades CSV
for fname in ['data/paper_trades.csv', 'data/paper_trades_legacy.csv', 'data/paper_trade_log.csv']:
    try:
        with open(fname) as f:
            content = f.read()
        lines = content.strip().split('\n')
        recent = [l for l in lines[1:] if l and l[:10] >= cutoff]
        print(f"\n=== {fname}: {len(lines)-1} total, {len(recent)} since {cutoff} ===")
        if lines[0]: print(f"Header: {lines[0]}")
        for l in lines[1:]:  # print ALL
            if 'LUPIN' in l.upper() or l[:10] >= cutoff:
                print(l)
    except Exception as e:
        print(f"{fname}: {e}")

# trading_brain.db
try:
    con = sqlite3.connect('data/trading_brain.db')
    cols = [d[1] for d in con.execute('PRAGMA table_info(trades)').fetchall()]
    rows = con.execute('SELECT * FROM trades ORDER BY rowid DESC LIMIT 100').fetchall()
    print(f"\n=== trading_brain.db trades: {len(rows)} rows, cols={cols} ===")
    for r in rows:
        d = dict(zip(cols, r))
        if d.get('symbol','').upper() in ('LUPIN','LUPIN.NS') or (str(d.get('entry_time','')+str(d.get('timestamp','')))[:10] >= cutoff):
            print(json.dumps(d, default=str))
    con.close()
except Exception as e:
    print(f"trading_brain.db: {e}")

# control_tower ct_cycles - recent
try:
    con = sqlite3.connect('data/control_tower.db')
    cols = [d[1] for d in con.execute('PRAGMA table_info(ct_cycles)').fetchall()]
    rows = con.execute("SELECT * FROM ct_cycles ORDER BY rowid DESC LIMIT 20").fetchall()
    print(f"\n=== ct_cycles last 20: cols={cols} ===")
    for r in rows:
        d = dict(zip(cols, r))
        print(json.dumps(d, default=str))

    # ct_decisions with LUPIN
    cols2 = [d[1] for d in con.execute('PRAGMA table_info(ct_decisions)').fetchall()]
    rows2 = con.execute("SELECT * FROM ct_decisions WHERE json_extract(payload,'$.symbol') LIKE '%LUPIN%' OR json_extract(payload,'$.symbol') LIKE '%lupin%' ORDER BY rowid DESC LIMIT 20").fetchall()
    print(f"\n=== ct_decisions LUPIN: {len(rows2)} ===")
    for r in rows2:
        print(dict(zip(cols2, r)))
    con.close()
except Exception as e:
    print(f"control_tower: {e}")

# logs
log_dir = 'data/logs'
if os.path.isdir(log_dir):
    all_logs = sorted(os.listdir(log_dir))
    print(f"\n=== Log files: {all_logs} ===")
    recent_logs = [l for l in all_logs if l[:10] >= cutoff]
    print(f"Recent log files (>= {cutoff}): {recent_logs}")
    for lf in sorted(all_logs)[-5:]:
        path = os.path.join(log_dir, lf)
        try:
            with open(path, 'r', errors='replace') as f:
                lines = f.readlines()
            lupin_lines = [(i+1, l.rstrip()) for i, l in enumerate(lines) if 'LUPIN' in l.upper()]
            err_lines   = [(i+1, l.rstrip()) for i, l in enumerate(lines)
                           if any(k in l for k in ['ERROR','FAILED','price not','no price','fallback to stop',
                                                   'exit_price=0','pnl=-','Loss booked','stop loss','STOP'])]
            if lupin_lines:
                print(f"\n  LUPIN in {lf}:")
                for n, l in lupin_lines:
                    print(f"    L{n}: {l}")
            if err_lines:
                print(f"\n  ERRORS/EXIT in {lf} (sample):")
                for n, l in err_lines[:30]:
                    print(f"    L{n}: {l}")
        except Exception as e:
            print(f"  {lf}: {e}")
