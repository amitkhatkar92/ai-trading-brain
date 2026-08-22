"""
Fix phantom price COALINDIA position and run syntax check.
"""
import py_compile
import csv, sys, io

for f in ['/app/data_feeds/dhan_feed.py', '/app/data_feeds/yahoo_feed.py']:
    try:
        py_compile.compile(f, doraise=True)
        print(f'SYNTAX OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'SYNTAX ERROR: {e}')
        sys.exit(1)

# Close the bad COALINDIA position in paper_trades.csv
CSV_PATH = '/app/data/paper_trades.csv'
BAD_ORDER_ID = 'SIM_COALINDIA_BUY_Q749_P1001.15_1780031205127'
EXIT_PRICE = 465.0
ENTRY_PRICE = 1000.05
QTY = 749
PNL = round(QTY * (EXIT_PRICE - ENTRY_PRICE), 2)  # -400,752.45

# Read existing CSV
with open(CSV_PATH, 'r', newline='') as f:
    reader = csv.reader(f)
    rows = list(reader)

# Check if already closed
header = rows[0] if rows else []
already_closed = any(
    r[1] == BAD_ORDER_ID and len(r) > 11 and r[11] == 'CLOSE'
    for r in rows[1:] if len(r) > 11
)

if already_closed:
    print(f'Position {BAD_ORDER_ID} already closed in CSV.')
else:
    # Find the OPEN row
    open_row = next(
        (r for r in rows[1:] if len(r) > 11 and r[1] == BAD_ORDER_ID and r[11] == 'OPEN'),
        None
    )
    if not open_row:
        print(f'WARNING: OPEN row for {BAD_ORDER_ID} not found.')
    else:
        # Build close row preserving all columns from open row, changing status
        close_row = list(open_row)
        close_row[0] = '2026-05-29 11:10:00'   # timestamp
        close_row[11] = 'CLOSE'                  # status
        close_row[12] = str(EXIT_PRICE)          # exit_price
        close_row[13] = str(PNL)                 # pnl
        close_row[14] = 'PHANTOM_PRICE_CORRECTION'  # close_reason

        # Pad if needed
        while len(close_row) < 15:
            close_row.append('')

        rows.append(close_row)
        with open(CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f'Position closed: entry={ENTRY_PRICE} exit={EXIT_PRICE} pnl={PNL}')

print('Done.')
