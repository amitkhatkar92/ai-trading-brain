import sys
sys.path.insert(0, '/app')
from opportunity_engine.equity_scanner_ai import _do_fetch_prices

# Test with padded symbols (as they appear in _BASE_WATCHLIST)
padded = ['RELIANCE    ', 'HDFCBANK    ', 'SUNPHARMA   ', 'ICICIBANK   ']
r = _do_fetch_prices(padded)
print(f'prices got: {len(r)} keys: {list(r.keys())}')
for k, v in r.items():
    print(f'  {repr(k)}: {v}')

# Verify keys are clean (no trailing spaces)
has_spaces = [k for k in r.keys() if k != k.strip()]
print(f'Keys with trailing spaces: {has_spaces}')
print('STRIP FIX OK' if not has_spaces and len(r) > 0 else 'STRIP FIX NEEDED')
