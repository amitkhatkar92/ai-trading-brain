import csv, json
from collections import defaultdict

with open('data/paper_trades.csv') as f:
    rows = list(csv.DictReader(f))

# Build trade pairs (OPEN+CLOSE on same order_id)
open_map = {r['order_id']: r for r in rows if r.get('event','').strip() == 'OPEN'}
close_map = {r['order_id']: r for r in rows if r.get('event','').strip() == 'CLOSE'}

paired = []
unpaired_opens = []
for oid, o in open_map.items():
    if oid in close_map:
        c = close_map[oid]
        try:
            entry = float(o['entry_price'])
            exit_p = float(c['entry_price'])
            sl = float(o['stop_loss'])
            risk = abs(entry - sl)
            if risk > 0:
                pnl_per_unit = (exit_p - entry) if o['direction'] == 'BUY' else (entry - exit_p)
                r_multiple = pnl_per_unit / risk
                paired.append({
                    'symbol': o['symbol'],
                    'strategy': o['strategy'],
                    'direction': o['direction'],
                    'r': round(r_multiple, 2),
                    'entry': entry,
                    'exit': exit_p,
                    'date': o['timestamp'][:10]
                })
        except Exception as e:
            pass
    else:
        unpaired_opens.append(o)

total = len(paired)
wins = [p for p in paired if p['r'] > 0]
losses = [p for p in paired if p['r'] <= 0]

print(f"Paired trades: {total}")
print(f"Still OPEN (no close): {len(unpaired_opens)}")
print(f"Wins: {len(wins)} ({100*len(wins)/total:.1f}%)  Losses: {len(losses)} ({100*len(losses)/total:.1f}%)")

r_vals = [p['r'] for p in paired]
avg_r = sum(r_vals) / total if total else 0
avg_win_r = sum(p['r'] for p in wins) / len(wins) if wins else 0
avg_loss_r = sum(p['r'] for p in losses) / len(losses) if losses else 0
print(f"Avg R: {avg_r:.3f}  Avg Win R: {avg_win_r:.3f}  Avg Loss R: {avg_loss_r:.3f}")

# Best and worst trades
paired_sorted = sorted(paired, key=lambda x: x['r'], reverse=True)
print("\n--- Top 5 Trades ---")
for p in paired_sorted[:5]:
    print(f"  {p['date']}  {p['symbol']:15s}  {p['strategy']:35s}  R={p['r']:+.2f}  {p['direction']}")
print("\n--- Bottom 5 Trades ---")
for p in paired_sorted[-5:]:
    print(f"  {p['date']}  {p['symbol']:15s}  {p['strategy']:35s}  R={p['r']:+.2f}  {p['direction']}")

# By strategy
print("\n--- Strategy Breakdown ---")
by_strat = defaultdict(list)
for p in paired:
    by_strat[p['strategy']].append(p['r'])
for s, rs in sorted(by_strat.items()):
    wins_s = [r for r in rs if r > 0]
    wr = 100 * len(wins_s) / len(rs)
    avg = sum(rs) / len(rs)
    print(f"  {s[:40]:40s}  N={len(rs):3d}  WR={wr:5.1f}%  AvgR={avg:+.3f}")

# By symbol (top 10)
print("\n--- Top 10 Symbols by Trade Count ---")
by_sym = defaultdict(list)
for p in paired:
    by_sym[p['symbol']].append(p['r'])
for s, rs in sorted(by_sym.items(), key=lambda x: -len(x[1]))[:10]:
    wins_s = [r for r in rs if r > 0]
    wr = 100 * len(wins_s) / len(rs)
    avg = sum(rs) / len(rs)
    print(f"  {s:15s}  N={len(rs):3d}  WR={wr:5.1f}%  AvgR={avg:+.3f}")

# Key R distribution
big_wins = [p for p in paired if p['r'] >= 2.0]
big_losses = [p for p in paired if p['r'] <= -1.0]
print(f"\n--- R Distribution ---")
print(f"  R >= +2.0 (big wins):   {len(big_wins)}")
print(f"  +1.0 <= R < +2.0:       {len([p for p in paired if 1.0 <= p['r'] < 2.0])}")
print(f"  0 < R < +1.0:           {len([p for p in paired if 0 < p['r'] < 1.0])}")
print(f"  -1.0 < R <= 0 (small L):{len([p for p in paired if -1.0 < p['r'] <= 0])}")
print(f"  R <= -1.0 (big losses): {len(big_losses)}")

# Expectancy
expectancy = avg_win_r * (len(wins)/total) - abs(avg_loss_r) * (len(losses)/total) if total else 0
print(f"\n--- Expectancy: {expectancy:+.4f}R per trade ---")
