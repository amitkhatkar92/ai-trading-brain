"""Probe ohlc_data and ticker_data responses with the correct new API."""
import os, sys
sys.path.insert(0, '/app')

token = os.environ.get('DHAN_ACCESS_TOKEN', '')
cid   = os.environ.get('DHAN_CLIENT_ID', '')
print(f"token_len={len(token)}  cid={cid[:6]}...")

from dhanhq import DhanContext, dhanhq
ctx  = DhanContext(cid, token)
dhan = dhanhq(ctx)

# HDFCBANK = 1333 NSE_EQ, RELIANCE = 2885 NSE_EQ
test_cases = [
    ("NSE_EQ", 1333, "HDFCBANK"),
    ("NSE_EQ", 2885, "RELIANCE"),
]

for seg, sid, name in test_cases:
    print(f"\n=== {name} ({seg} / {sid}) ===")

    print("--- ohlc_data ---")
    try:
        r = dhan.ohlc_data(securities={seg: [sid]})
        print(f"  type={type(r).__name__}  repr={repr(r)[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("--- ticker_data ---")
    try:
        r = dhan.ticker_data(securities={seg: [sid]})
        print(f"  type={type(r).__name__}  repr={repr(r)[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("--- quote_data ---")
    try:
        r = dhan.quote_data(securities={seg: [sid]})
        print(f"  type={type(r).__name__}  repr={repr(r)[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
