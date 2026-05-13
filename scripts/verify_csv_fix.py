import csv
path = '/app/data/paper_trades.csv'
today = '2026-04-28'
with open(path, newline='', encoding='utf-8') as f:
    dr = csv.DictReader(f)
    print('Fieldnames:', dr.fieldnames)
    closes = [r for r in dr if r.get('event','').upper()=='CLOSE' and r.get('timestamp','').startswith(today)]
print(f'Today CLOSE rows: {len(closes)}')
for r in closes:
    print(f"  {r['symbol']:12} pnl={r.get('pnl','MISSING'):>12}  reason={r.get('reason','MISSING')}  None_key={r.get(None,'ok')}")
