"""Verify the new dhanhq DhanContext API works live."""
import os, sys
sys.path.insert(0, '/app')

token = os.environ.get('DHAN_ACCESS_TOKEN', '')
cid   = os.environ.get('DHAN_CLIENT_ID', '')
print(f"token_len={len(token)}  cid={cid[:6]}...")

from dhanhq import DhanContext, dhanhq
ctx  = DhanContext(cid, token)
dhan = dhanhq(ctx)

# Test 1: LTP data
print("\n--- get_ltp_data NSE_EQ HDFCBANK(1333) ---")
resp = dhan.get_ltp_data(securities={'NSE_EQ': [1333]})
print(f"type: {type(resp).__name__}")
print(f"resp: {repr(resp)[:800]}")

# Test 2: market quote
print("\n--- get_market_quote ---")
try:
    resp2 = dhan.get_market_quote(securities={'NSE_EQ': [1333]})
    print(f"type: {type(resp2).__name__}  repr: {repr(resp2)[:600]}")
except Exception as e:
    print(f"  ERROR: {e}")
