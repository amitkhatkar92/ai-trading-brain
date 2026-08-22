import csv, datetime

WEEK_START = datetime.date(2026, 6, 9)
WEEK_END   = datetime.date(2026, 6, 12)

rows = []
with open("/root/ai-trading-brain/data/paper_trades.csv") as f:
    for r in csv.DictReader(f):
        try:
            dt = datetime.datetime.fromisoformat(r["timestamp"]).date()
        except Exception:
            continue
        if WEEK_START <= dt <= WEEK_END:
            rows.append(r)

print(f"Week {WEEK_START} to {WEEK_END}  total rows: {len(rows)}")

CLOSE_EVENTS = {"CLOSE","SL","TARGET","EXIT","FORCE_CLOSE","CARRY_EXIT","EXPIRY_EXIT","CARRY_EXPIRED"}
closed = [r for r in rows if r["event"].upper() in CLOSE_EVENTS]
print(f"\n{'='*60}")
print(f"REALIZED P&L  --  {len(closed)} closed trade(s)")
print(f"{'='*60}")
total_pnl = 0.0
wins, losses = 0, 0
for r in sorted(closed, key=lambda x: x["timestamp"]):
    pnl = float(r["pnl"] or 0)
    total_pnl += pnl
    tag = "WIN " if pnl > 0 else ("LOSS" if pnl < 0 else "BE  ")
    if pnl > 0: wins += 1
    elif pnl < 0: losses += 1
    print(f"  {tag}  {r['timestamp'][:10]}  {r['symbol']:<12} {r['direction']:<5} "
          f"Q={r['quantity']:<6} entry={r['entry_price']:<10} exit={r['exit_price']:<10} "
          f"PnL=Rs{pnl:+,.0f}  [{r['event']}]")

wr = int(wins*100/(wins+losses+0.001)) if (wins+losses) > 0 else 0
print(f"\n  TOTAL REALIZED  : Rs{total_pnl:+,.0f}")
print(f"  Win/Loss        : {wins}W / {losses}L  ({wr}% WR)")

opens = {}
for r in rows:
    oid = r["order_id"]
    if r["event"].upper() == "OPEN":
        opens[oid] = r
for r in rows:
    if r["event"].upper() != "OPEN":
        opens.pop(r.get("order_id",""), None)

# Also catch carries that were opened BEFORE this week and still open
all_opens = {}
with open("/root/ai-trading-brain/data/paper_trades.csv") as f:
    for r in csv.DictReader(f):
        oid = r["order_id"]
        if r["event"].upper() == "OPEN":
            all_opens[oid] = r
        elif r["event"].upper() in CLOSE_EVENTS:
            all_opens.pop(oid, None)

print(f"\n{'='*60}")
print(f"ALL OPEN POSITIONS (carries from any date)")
print(f"{'='*60}")
if not all_opens:
    print("  (no open positions)")
for r in all_opens.values():
    ep = float(r["entry_price"])
    print(f"  {r['timestamp'][:10]}  {r['symbol']:<12} {r['direction']:<5} "
          f"Q={r['quantity']:<6} entry={ep:,.2f}  strategy={r['strategy']}")

print(f"\n  Total open carries: {len(all_opens)}")
