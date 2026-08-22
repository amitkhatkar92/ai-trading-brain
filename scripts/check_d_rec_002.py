import sqlite3, os
ROOT = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain"
c = sqlite3.connect(os.path.join(ROOT, "data/recommendations.db"))
r = c.execute("SELECT rec_id, status, category, reviewer_notes FROM recommendations WHERE rec_id='D-REC-002'").fetchone()
if r:
    print("rec_id:", r[0])
    print("status:", r[1])
    print("category:", r[2])
    print("notes:", r[3])
else:
    print("NOT FOUND")
