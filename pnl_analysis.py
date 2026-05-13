import csv
from collections import defaultdict
rows = list(csv.DictReader(open('/app/data/paper_trades.csv')))
closed = [r for r in rows if r['event']=='CLOSE' and r['pnl'].strip() and r['reason'] != 'emergency_close']
real = [r for r in closed if float(r['pnl']) != 0]
print('=== ALL REAL CLOSED TRADES (chronological) ===')
for r in real:
    d = r['timestamp'][:10]
    pnl = float(r['pnl'])
    tag = 'WIN' if pnl > 0 else 'LOSS'
    print(f"  {tag:4s}  {r['symbol']:12s}  {d}  entry={float(r['entry_price']):>8.2f}  exit={float(r['exit_price']):>8.2f}  PnL=Rs {pnl:>10,.0f}  strategy={r['strategy'][:22]:22s}  reason={r['reason']}")

print()
print('=== BY STRATEGY ===')
by_strat = defaultdict(list)
for r in real:
    by_strat[r['strategy']].append(float(r['pnl']))
for s, pnls in sorted(by_strat.items()):
    w = sum(1 for p in pnls if p>0)
    l = sum(1 for p in pnls if p<0)
    total = sum(pnls)
    print(f'  {s:28s}  trades={len(pnls)}  W={w} L={l}  WR={int(w/len(pnls)*100)}%  total=Rs {int(total):,}')

print()
print('=== LOSS ANALYSIS ===')
losses = [r for r in real if float(r['pnl']) < 0]
for r in losses:
    entry = float(r['entry_price'])
    exit_ = float(r['exit_price'])
    sl    = float(r['stop_loss']) if r.get('stop_loss') else 0
    tgt   = float(r['target']) if r.get('target') else 0
    move  = (exit_ - entry) / entry * 100
    sl_dist = (sl - entry) / entry * 100 if sl else 0
    print(f"  {r['symbol']:12s}  entry={entry:.2f}  exit={exit_:.2f}  SL={sl:.2f}  move={move:.2f}%  SL_dist={sl_dist:.2f}%  reason={r['reason']:18s}  strat={r['strategy'][:20]}")

