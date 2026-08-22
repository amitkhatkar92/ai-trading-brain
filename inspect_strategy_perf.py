import json

with open('/root/ai-trading-brain/data/learning_db.json') as f:
    ldb = json.load(f)

print('=== STRATEGY STATS (Full) ===')
for k, v in sorted(ldb['strategy_stats'].items()):
    total = v.get('total_trades', 0)
    wins = v.get('wins', 0)
    wr = v.get('win_rate', 0)
    exp = v.get('expectancy', 0)
    total_pnl = v.get('total_pnl', 0)
    print(f'{k:<40}: trades={total:<4} wins={wins:<4} wr={wr:.1%}  expectancy={exp:.6f}  total_pnl={total_pnl:.6f}')

with open('/root/ai-trading-brain/data/ml_performance_dataset.json') as f:
    ml = json.load(f)

print('\n=== ML PERFORMANCE DATASET (Full) ===')
by_strat = {}
for row in ml:
    s = row['strategy']
    if s not in by_strat:
        by_strat[s] = []
    by_strat[s].append(row)

for strat, rows in sorted(by_strat.items()):
    wins = sum(1 for r in rows if r['won'])
    losses = len(rows) - wins
    avg_ret = sum(r['return_pct'] for r in rows) / len(rows)
    avg_rr = sum(r['r_multiple'] for r in rows) / len(rows)
    regimes = set(r['regime'] for r in rows)
    print(f'{strat}: n={len(rows)} wr={wins/len(rows):.1%} avg_ret={avg_ret:.2f}% avg_rr={avg_rr:.2f} regimes={regimes}')

print('\nAll rows:')
for row in ml:
    print(f"  {row['date']} {row['strategy']:<30} regime={row['regime']:<15} sector_str={row['sector_strength']} vix={row['vix']} won={row['won']} ret={row['return_pct']:.2f}% rr={row['r_multiple']:.2f}")

# check market_leader outcomes
import sqlite3
con = sqlite3.connect('/root/ai-trading-brain/data/market_behavior.db')
con.row_factory = sqlite3.Row

# Get winner vs control return distributions
winners = con.execute("SELECT mlo.* FROM market_leader_outcomes mlo JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id WHERE ml.leader_type='WINNER'").fetchall()
controls = con.execute("SELECT mlo.* FROM market_leader_outcomes mlo JOIN market_leaders_daily ml ON ml.leader_id = mlo.leader_id WHERE ml.leader_type!='WINNER'").fetchall()
con.close()

def stats(vals, label):
    v = [x for x in vals if x is not None]
    if not v: return
    avg = sum(v)/len(v)
    pos = sum(1 for x in v if x > 0) / len(v)
    print(f'  {label}: n={len(v)} avg={avg:.3f}% pos_rate={pos:.1%}')

print('\n=== MARKET LEADER OUTCOME DISTRIBUTIONS ===')
print('WINNERS:')
for col in ['return_1d','return_3d','return_5d','return_10d','return_20d','max_favorable','max_adverse']:
    stats([float(w[col]) for w in winners if w[col] is not None], col)
print('CONTROLS:')
for col in ['return_1d','return_3d','return_5d','return_10d','return_20d','max_favorable','max_adverse']:
    stats([float(c[col]) for c in controls if c[col] is not None], col)
