import sys, csv, os
sys.path.insert(0, '/app')

# Open positions from CSV
JOURNAL = '/app/data/paper_trades.csv'
open_rows = {}
closed = set()

with open(JOURNAL, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        oid = row.get('order_id', '').strip()
        event = row.get('event', '').strip().upper()
        if not oid:
            continue
        if event in ('OPEN', 'REENTRY_OPEN'):
            open_rows[oid] = row
        elif event in ('CLOSE', 'CANCELLED'):
            open_rows.pop(oid, None)
            closed.add(oid)

# Remove ghosts: any ID that has a CLOSE for the base name
# (handles the old SIM_NIFTY_SELL_43 ghost)
for oid in list(open_rows.keys()):
    if oid in closed:
        del open_rows[oid]

if not open_rows:
    print('No open positions.')
    sys.exit(0)

# Get live LTPs
try:
    from data_feeds.data_feed_manager import get_feed_manager
    fm = get_feed_manager()
    prices = {}
    for row in open_rows.values():
        sym = row['symbol']
        if sym not in prices:
            q = fm.get_quote(sym)
            prices[sym] = q.ltp if q else None
except Exception as e:
    prices = {}
    print(f'[WARN] Could not fetch live prices: {e}')

print('=' * 72)
print(f'  OPEN POSITIONS P&L  |  {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('=' * 72)
print(f'  {"Symbol":<10} {"Dir":<5} {"Qty":>6}  {"Entry":>8}  {"LTP":>8}  {"SL":>8}  {"R-mult":>7}  {"Unreal P&L":>12}  Strategy')
print('  ' + '-' * 70)

total_pnl = 0.0
for oid, row in open_rows.items():
    sym   = row['symbol']
    dirn  = row['direction']
    qty   = int(float(row.get('quantity', 1)))
    entry = float(row.get('entry_price', 0) or 0)
    sl    = float(row.get('stop_loss', 0) or 0)
    tgt   = float(row.get('target', 0) or 0)
    strat = row.get('strategy', '')
    ts    = row.get('timestamp', '')[:10]
    ltp   = prices.get(sym)

    if ltp is None:
        ltp_str = '  N/A   '
        r_str   = '  N/A  '
        pnl_str = '        N/A'
    else:
        risk = abs(entry - sl) if sl else 0
        if dirn == 'BUY':
            unreal = (ltp - entry) * qty
            r_mult = (ltp - entry) / risk if risk else 0
        else:  # SELL
            unreal = (entry - ltp) * qty
            r_mult = (entry - ltp) / risk if risk else 0
        total_pnl += unreal
        ltp_str = f'{ltp:>8.2f}'
        r_str   = f'{r_mult:>+7.2f}R'
        pnl_str = f'{unreal:>+12,.0f}'

    print(f'  {sym:<10} {dirn:<5} {qty:>6}  {entry:>8.2f}  {ltp_str}  {sl:>8.2f}  {r_str}  {pnl_str}  {strat} [{ts}]')

print('  ' + '-' * 70)
if prices:
    print(f'  {"TOTAL UNREALISED P&L":>52}  {total_pnl:>+12,.0f}')
print('=' * 72)
