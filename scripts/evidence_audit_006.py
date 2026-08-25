"""DTA-LIVE-006: Evidence bridge and system state audit."""
import json
import os
from pathlib import Path
from collections import Counter
from datetime import date

base = Path(os.environ.get("DATA_BASE", "/app/data"))

# ── Evidence Ledgers ─────────────────────────────────────────────
for ledger_name in ("knowledge_evidence_ledger.jsonl", "shadow_evidence_ledger.jsonl"):
    path = base / ledger_name
    if not path.exists():
        print(f"{ledger_name}: NOT FOUND")
        continue
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    recs = []
    for l in lines:
        try:
            recs.append(json.loads(l))
        except Exception:
            pass
    sources = Counter(r.get("source") for r in recs)
    dates   = Counter(r.get("date", r.get("trading_date", r.get("decision_date")))  for r in recs)
    no_look = Counter(r.get("no_lookahead") for r in recs)
    today   = date.today().isoformat()
    today_recs = [r for r in recs if r.get("date", r.get("trading_date", "")) == today
                  or r.get("decision_date", "") == today]
    print(f"\n=== {ledger_name} ===")
    print(f"  total_lines: {len(lines)}")
    print(f"  sources: {dict(sources)}")
    print(f"  today({today})_records: {len(today_recs)}")
    print(f"  no_lookahead: {dict(no_look)}")
    # Last 2 records
    if recs:
        for r in recs[-2:]:
            print("  LAST_REC:", json.dumps({k: r.get(k) for k in [
                "observation_id", "source", "date", "trading_date", "decision_date",
                "no_lookahead", "outcome_class", "symbol"
            ]}))

# ── Strategy Performance ─────────────────────────────────────────
sp_path = base / "strategy_performance.json"
if sp_path.exists():
    sp = json.loads(sp_path.read_text())
    print("\n=== strategy_performance.json ===")
    for name, v in sp.items():
        print(f"  {name}: enabled={v.get('enabled')} total={v.get('total_trades')} "
              f"wins={v.get('winning_trades')} losses={v.get('losing_trades')} "
              f"consec_loss={v.get('consecutive_losses')} "
              f"official={v.get('official_trades')}")
else:
    print("strategy_performance.json: NOT FOUND")

# ── Protected files hash check ─────────────────────────────────
protected = [
    "execution_engine/order_manager.py",
    "risk_guardian/risk_guardian.py",
]
repo = Path(os.environ.get("REPO_BASE", "/app"))
print("\n=== Protected file check ===")
for f in protected:
    p = repo / f
    if p.exists():
        import hashlib
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        print(f"  {f}: sha256[:12]={h}")
    else:
        print(f"  {f}: NOT FOUND")
