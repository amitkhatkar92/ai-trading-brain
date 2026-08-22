"""RE001 database query script — run after historical_replay.py completes."""
import sqlite3

db = sqlite3.connect("data/re001_replay.db")
db.row_factory = sqlite3.Row
c = db.cursor()

print("=== TABLES ===")
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print(tables)

print()
print("=== SIGNAL BIRTHS — total ===")
c.execute("SELECT COUNT(*) FROM signal_births")
print("  Total:", c.fetchone()[0])

print()
print("=== SIGNAL BIRTHS — by archetype ===")
c.execute("SELECT archetype_id, COUNT(*) as n FROM signal_births GROUP BY archetype_id ORDER BY n DESC")
for r in c.fetchall():
    print(f"  {r[0]:<40} {r[1]}")

print()
print("=== SIGNAL BIRTHS — by regime ===")
c.execute("SELECT regime_at_birth, COUNT(*) FROM signal_births GROUP BY regime_at_birth ORDER BY 2 DESC")
for r in c.fetchall():
    print(f"  {r[0]:<20} {r[1]}")

print()
print("=== SIGNAL BIRTHS — by sector (via opportunities) ===")
c.execute("""
    SELECT o.sector, COUNT(*) FROM signal_births sb
    LEFT JOIN opportunities o ON sb.opportunity_id = o.opportunity_id
    GROUP BY o.sector ORDER BY 2 DESC
""")
for r in c.fetchall():
    print(f"  {r[0]:<30} {r[1]}")

print()
print("=== SIGNAL BIRTHS — top symbols ===")
c.execute("SELECT symbol, COUNT(*) as n FROM signal_births GROUP BY symbol ORDER BY n DESC LIMIT 20")
for r in c.fetchall():
    print(f"  {r[0]:<25} {r[1]}")

print()
print("=== OPPORTUNITIES — lifecycle ===")
c.execute("""
    SELECT current_state, COUNT(*) as n,
           CAST(ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS TEXT) || '%' as pct
    FROM opportunities GROUP BY current_state ORDER BY n DESC
""")
for r in c.fetchall():
    print(f"  {r[0]:<20} {r[1]:>4}  ({r[2]})")

print()
print("=== OPPORTUNITIES — confirming count distribution ===")
c.execute("SELECT confirming_count, COUNT(*) FROM opportunities GROUP BY confirming_count ORDER BY confirming_count")
for r in c.fetchall():
    print(f"  confirming={r[0]}: {r[1]} opportunities")

print()
print("=== OPPORTUNITIES — top symbols by confirming count ===")
c.execute("SELECT symbol, confirming_count, current_state FROM opportunities ORDER BY confirming_count DESC LIMIT 15")
for r in c.fetchall():
    print(f"  {r[0]:<25} {r[1]} confirming  [{r[2]}]")

print()
print("=== SECTOR CONVICTION DAILY — summary ===")
try:
    c.execute("SELECT COUNT(*) FROM sector_conviction_daily")
    print("  Total sector_conviction_daily rows:", c.fetchone()[0])
    c.execute("SELECT sector, COUNT(*), ROUND(AVG(conviction),3), ROUND(MAX(conviction),3) FROM sector_conviction_daily GROUP BY sector ORDER BY AVG(conviction) DESC")
    for r in c.fetchall():
        print(f"  {r[0]:<30} n={r[1]}  avg={r[2]}  max={r[3]}")
except Exception as e:
    print("  Error:", e)

print()
print("=== THEME PHASE HISTORY ===")
try:
    c.execute("SELECT COUNT(*) FROM theme_phase_history")
    print("  Total rows:", c.fetchone()[0])
except Exception as e:
    print("  Not found:", e)

print()
print("=== REGIME BY DATE ===")
try:
    c.execute("SELECT date_simulated, regime FROM replay_daily_log ORDER BY date_simulated")
    for r in c.fetchall():
        print(f"  {r[0]}  {r[1]}")
except Exception as e:
    print("  Table not found:", e)

print()
print("=== OPPORTUNITIES — direction breakdown ===")
c.execute("SELECT direction, COUNT(*) FROM opportunities GROUP BY direction ORDER BY 2 DESC")
for r in c.fetchall():
    print(f"  {r[0]:<10} {r[1]}")

print()
print("=== SIGNAL BIRTHS — score distribution ===")
c.execute("""
    SELECT
        CASE WHEN base_score < 5.0 THEN 'below_5.0'
             WHEN base_score < 6.0 THEN '5.0-6.0'
             WHEN base_score < 7.0 THEN '6.0-7.0'
             WHEN base_score < 8.0 THEN '7.0-8.0'
             ELSE '8.0+' END as bucket,
        COUNT(*) as n
    FROM signal_births GROUP BY bucket ORDER BY bucket
""")
for r in c.fetchall():
    print(f"  {r[0]:<15} {r[1]}")

print()
print("=== MIN/MAX/AVG signal score ===")
c.execute("SELECT ROUND(MIN(base_score),2), ROUND(AVG(base_score),2), ROUND(MAX(base_score),2) FROM signal_births")
r = c.fetchone()
print(f"  min={r[0]}  avg={r[1]}  max={r[2]}")

db.close()
print("\nDone.")
