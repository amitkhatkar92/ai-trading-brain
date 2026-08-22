import sys
sys.path.insert(0, '/app')
from opportunity_engine import equity_scanner_ai as e

all_wl = e._BASE_WATCHLIST + e._EXTENDED_WATCHLIST
print(f'Total watchlist entries: {len(all_wl)}')

bad = [s for s in all_wl if not s.get('symbol','').strip()]
print(f'Empty/bad symbol entries: {bad}')

all_syms = [s['symbol'] for s in all_wl]
empty = [s for s in all_syms if not s.strip()]
print(f'Empty symbols: {empty}')

# Show the full batch that would be sent to yfinance
ns_syms = [f"{s}.NS" for s in all_syms]
print(f'\nFull NS batch ({len(ns_syms)} symbols):')
for s in ns_syms:
    print(f'  {repr(s)}')

# Now test the actual batch download to see if it works
print('\n=== Testing full batch download ===')
import yfinance as yf
try:
    batch_str = ' '.join(ns_syms)
    d = yf.download(batch_str, period='2d', interval='1d', timeout=8, progress=False, threads=False)
    print(f'Full batch result: rows={len(d)} empty={d.empty}')
    if hasattr(d.columns, 'levels'):
        symbols_got = list(d.columns.get_level_values(1).unique())
        print(f'Symbols with data: {len(symbols_got)}')
except Exception as ex:
    print(f'Full batch FAILED: {ex}')

print('WATCHLIST TEST DONE')
