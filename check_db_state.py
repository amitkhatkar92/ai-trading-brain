import sqlite3
con = sqlite3.connect('/root/ai-trading-brain/data/market_behavior.db')
total = con.execute('SELECT COUNT(*) FROM signal_births').fetchone()[0]
null_fs = con.execute('SELECT COUNT(*) FROM signal_births WHERE final_state IS NULL').fetchone()[0]
set_fs  = con.execute('SELECT COUNT(*) FROM signal_births WHERE final_state IS NOT NULL').fetchone()[0]
print(f'total={total}  null={null_fs}  set={set_fs}')
rows = con.execute('SELECT final_state, COUNT(*) FROM signal_births GROUP BY final_state').fetchall()
for r in rows: print(f'  final_state={repr(r[0])}  count={r[1]}')
print()
rows2 = con.execute("SELECT substr(signal_id,1,8), symbol, detected_at, final_state, last_updated_at FROM signal_births WHERE final_state IS NOT NULL LIMIT 20").fetchall()
for r in rows2: print(r)

# Taxonomy gap: which consumer modules use old ELE final_state taxonomy
print()
print('--- Taxonomy check ---')
print('Consumers that check final_state = TTL_EXHAUSTED or INVALID:')
import subprocess, os
for d in ['oios/reporting', 'oios/engine']:
    path = f'/root/ai-trading-brain/{d}'
    if os.path.isdir(path):
        res = subprocess.run(['grep', '-rn', 'TTL_EXHAUSTED\|INVALID', '--include=*.py', path],
                             capture_output=True, text=True)
        for line in res.stdout.splitlines():
            print(f'  {line}')
