import sqlite3, json, pathlib, os, time, glob

for db_path in ['/app/data/candidate_store.db', '/app/data/trading_brain.db', '/app/data/prepared_universe.db']:
    if pathlib.Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print('DB={} tables={}'.format(db_path, tables))
        for t in tables:
            cur.execute('SELECT COUNT(*) FROM ' + t)
            print('  {}: {} rows'.format(t, cur.fetchone()[0]))
            if 'candidate' in t.lower() or 'prepared' in t.lower():
                cur.execute('PRAGMA table_info({})'.format(t))
                cols = [c[1] for c in cur.fetchall()]
                print('  cols: {}'.format(cols))
                cur.execute('SELECT * FROM {} LIMIT 5'.format(t))
                for row in cur.fetchall():
                    print('    {}'.format(row))
        conn.close()
    else:
        print('NOT_FOUND: ' + db_path)

print()
for f in sorted(glob.glob('/app/data/*.json') + glob.glob('/app/data/*.db')):
    sz = os.path.getsize(f)
    age_h = (time.time() - os.path.getmtime(f)) / 3600
    print('FILE {} {}b age={:.1f}h'.format(f, sz, age_h))
