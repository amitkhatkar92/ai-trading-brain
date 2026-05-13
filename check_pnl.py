"""Quick P&L report from paper_trades.csv"""
import csv
from collections import defaultdict

opens = {}
trades = []

with open('data/paper_trades.csv', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        event = row[11] if len(row) > 11 else ''
        oid   = row[1]
        sym   = row[2]
        dirn  = row[3]
        qty   = int(row[4])   if row[4] else 0
        entry = float(row[5]) if row[5] else 0.0
        sl    = float(row[6]) if row[6] else 0.0
        tgt   = float(row[7]) if row[7] else 0.0
        strat = row[8]
        ts    = row[0]

        if event == 'OPEN':
            opens[oid] = dict(symbol=sym, direction=dirn, qty=qty,
                              entry=entry, sl=sl, target=tgt,
                              strategy=strat, open_ts=ts)
        elif event.upper().startswith('CLOSE'):
            exit_price = float(row[12]) if len(row) > 12 and row[12] else entry
            reason     = row[14]        if len(row) > 14 else ''
            base = opens.pop(oid, dict(symbol=sym, direction=dirn, qty=qty,
                                       entry=entry, sl=sl, target=tgt,
                                       strategy=strat, open_ts=ts))
            pnl = ((exit_price - base['entry']) * base['qty']
                   if base['direction'] == 'BUY'
                   else (base['entry'] - exit_price) * base['qty'])
            trades.append({**base, 'exit': exit_price, 'pnl': pnl,
                           'close_ts': ts, 'reason': reason})

still_open = list(opens.values())

# Deduplicate identical open+close replays (same symbol/entry/exit/reason)
seen_keys = set()
unique_trades = []
for t in trades:
    key = (t['symbol'], t['entry'], t['exit'], t['reason'])
    if key not in seen_keys:
        seen_keys.add(key)
        unique_trades.append(t)

total_pnl = sum(t['pnl'] for t in unique_trades)
by_symbol = defaultdict(float)

SEP = "=" * 82
print(SEP)
print(f"  PAPER TRADING P&L REPORT   |   Total raw closes: {len(trades)}   |   Unique: {len(unique_trades)}")
print(SEP)
print(f"  {'Symbol':<14} {'Dir':<5} {'Qty':<6} {'Entry':>10} {'Exit':>10} {'PnL (Rs)':>12}  Reason")
print("  " + "-" * 74)
for t in sorted(unique_trades, key=lambda x: x['close_ts']):
    pnl_str = f"Rs {t['pnl']:+,.0f}"
    by_symbol[t['symbol']] += t['pnl']
    print(f"  {t['symbol']:<14} {t['direction']:<5} {t['qty']:<6} {t['entry']:>10.2f} "
          f"{t['exit']:>10.2f} {pnl_str:>12}  {t['reason']}")

print()
print(f"  TOTAL REALISED P&L:  Rs {total_pnl:+,.0f}")
print()
print("  P&L by Symbol:")
for sym, pnl in sorted(by_symbol.items(), key=lambda x: x[1]):
    print(f"    {sym:<16}  Rs {pnl:+,.0f}")

print()
if still_open:
    print(f"  OPEN POSITIONS ({len(still_open)}):")
    for p in still_open:
        print(f"    {p['symbol']:<14}  {p['direction']}  qty={p['qty']}  "
              f"entry={p['entry']:.2f}  strategy={p['strategy']}")
else:
    print("  No positions currently open in the journal.")
print(SEP)
