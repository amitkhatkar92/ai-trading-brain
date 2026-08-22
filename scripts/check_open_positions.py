import csv

rows = list(csv.reader(open('/app/data/paper_trades.csv')))
hdr = rows[0]
col = {h: i for i, h in enumerate(hdr)}

events = {}
for r in rows[1:]:
    if len(r) < 3:
        continue
    oid = r[col['order_id']]
    ev  = r[col['event']]
    events.setdefault(oid, []).append(ev)

open_oids = [oid for oid, evs in events.items()
             if 'OPEN' in evs and 'CLOSE' not in evs]

print(f'Currently OPEN positions (no paired CLOSE): {len(open_oids)}')
for oid in open_oids:
    r = next((x for x in rows[1:]
               if x[col['order_id']] == oid and x[col['event']] == 'OPEN'), None)
    if r:
        print(f"  {r[col['timestamp']][:10]}  {r[col['symbol']]:14}  {r[col['direction']]:5}"
              f"  entry={r[col['entry_price']]}")
