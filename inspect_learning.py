import json, os, sqlite3, csv, glob

# 1. learning_db.json
with open('/root/ai-trading-brain/data/learning_db.json') as f:
    ldb = json.load(f)
print('=== learning_db.json ===')
print('Top-level keys:', list(ldb.keys()))
for k, v in list(ldb.items()):
    print(f'  {k}: {str(v)[:400]}')

# 2. ml_performance_dataset.json
ml_path = '/root/ai-trading-brain/data/ml_performance_dataset.json'
print('\n=== ml_performance_dataset.json ===')
if os.path.exists(ml_path):
    with open(ml_path) as f:
        ml_data = json.load(f)
    print('Type:', type(ml_data))
    if isinstance(ml_data, list):
        print(f'rows: {len(ml_data)}')
        if ml_data:
            print(f'sample keys: {list(ml_data[0].keys())}')
            print(f'sample row: {ml_data[0]}')
    elif isinstance(ml_data, dict):
        print(f'keys: {list(ml_data.keys())[:15]}')
        for k2, v2 in list(ml_data.items())[:5]:
            print(f'  {k2}: {str(v2)[:300]}')

# 3. Aggregate all closed_orders files
print('\n=== CLOSED ORDERS AGGREGATE ===')
order_files = sorted(glob.glob('/root/ai-trading-brain/data/closed_orders_*.txt'))
print(f'Files: {len(order_files)}')
all_orders = []
for filepath in order_files:
    try:
        with open(filepath) as f:
            content = f.read().strip()
        if not content:
            continue
        # Try JSON (list or single object)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                all_orders.extend(data)
            elif isinstance(data, dict):
                all_orders.append(data)
        except json.JSONDecodeError:
            # Try CSV-like
            lines = content.split('\n')
            for line in lines[:2]:
                print(f'  {filepath[-25:]}: {line[:100]}')
            break
    except Exception as e:
        print(f'  ERROR {filepath[-25:]}: {e}')

print(f'Total closed orders: {len(all_orders)}')
if all_orders:
    print(f'Sample keys: {list(all_orders[0].keys())}')
    print(f'Sample: {all_orders[0]}')

# Strategy breakdown of closed orders
from collections import defaultdict
strat_pnl = defaultdict(list)
for o in all_orders:
    strat = o.get('strategy_name') or o.get('strategy') or 'UNKNOWN'
    pnl = o.get('pnl') or o.get('pnl_pct') or o.get('net_pnl')
    if pnl is not None:
        try:
            strat_pnl[strat].append(float(pnl))
        except:
            pass

print('\nStrategy P&L from closed orders:')
for strat, pnls in sorted(strat_pnl.items()):
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / len(pnls) if pnls else 0
    avg = sum(pnls)/len(pnls) if pnls else 0
    print(f'  {strat}: n={len(pnls)}, WR={wr:.1%}, avg_pnl={avg:.4f}')
