import sqlite3
db = sqlite3.connect("data/re001_replay.db")
c = db.cursor()
state = "ACTIVE"
c.execute(
    "SELECT symbol, sector, conviction_score, confirming_count, created_at "
    "FROM opportunities WHERE current_state=? ORDER BY conviction_score DESC",
    (state,)
)
print("=== ACTIVE OPPORTUNITIES ===")
for r in c.fetchall():
    print(f"  {r[0]:<25} {r[1]:<22} conv={r[2]}  conf={r[3]}  {r[4]}")
db.close()
