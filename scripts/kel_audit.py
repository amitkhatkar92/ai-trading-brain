import json
from pathlib import Path

KEL = Path("/root/ai-trading-brain/data/knowledge_evidence_ledger.jsonl")
recs = [json.loads(l) for l in KEL.read_text().splitlines() if l.strip()]

ev_types = {}
for r in recs:
    k = r.get("event_type", "NONE")
    ev_types[k] = ev_types.get(k, 0) + 1
print("event_type distribution:", ev_types)

evidence = [r for r in recs if r.get("event_type") == "EVIDENCE"]
syms = set(r.get("symbol","").replace(".NS","").strip() for r in evidence)
print(f"unique symbols in EVIDENCE records: {len(syms)}")
print("sample symbols:", sorted(syms)[:15])

dates = sorted(r.get("trade_date","") for r in evidence if r.get("trade_date"))
print(f"date range: {dates[0] if dates else 'none'} -> {dates[-1] if dates else 'none'}")
print(f"total EVIDENCE records: {len(evidence)}")

# Check if any watchlist stocks (our 38) are covered
watchlist = ['RELIANCE','HDFCBANK','ICICIBANK','TATASTEEL','INFY','BANKBARODA',
             'COALINDIA','SBIN','AXISBANK','ONGC','ITC','NTPC','HAVELLS',
             'MARUTI','POWERGRID','TATACONSUM','ONGC','BANKBARODA']
covered = {s: sum(1 for r in evidence if r.get("symbol","").replace(".NS","").strip().upper() == s) for s in watchlist}
print("\nWatchlist coverage in KEL:")
for s, n in covered.items():
    print(f"  {s}: {n} records")
