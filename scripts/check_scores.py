"""Quick script to check scoring data in ct_decisions."""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), "..", "data", "control_tower.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== RECENT DECISIONS (last 10) ===")
for r in conn.execute(
    "SELECT symbol, strategy, confidence, technical_score, risk_score, "
    "macro_score, sentiment_score, regime_score, decision "
    "FROM ct_decisions ORDER BY id DESC LIMIT 10"
):
    print(dict(r))

print("\n=== SCORE DISTRIBUTIONS (APPROVED) ===")
for r in conn.execute(
    "SELECT AVG(confidence), MIN(confidence), MAX(confidence), "
    "AVG(technical_score), AVG(risk_score), AVG(macro_score) "
    "FROM ct_decisions WHERE decision='APPROVED'"
):
    print(f"Confidence  avg={r[0]}  min={r[1]}  max={r[2]}")
    print(f"TechScore   avg={r[3]}")
    print(f"RiskScore   avg={r[4]}")
    print(f"MacroScore  avg={r[5]}")

print("\n=== DISTINCT CONFIDENCE VALUES ===")
for r in conn.execute(
    "SELECT DISTINCT confidence FROM ct_decisions ORDER BY confidence DESC LIMIT 20"
):
    print(r[0])

conn.close()
