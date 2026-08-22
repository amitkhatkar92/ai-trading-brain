"""Probe all available methods on the new dhanhq object."""
import os, sys
sys.path.insert(0, '/app')

token = os.environ.get('DHAN_ACCESS_TOKEN', '')
cid   = os.environ.get('DHAN_CLIENT_ID', '')
print(f"token_len={len(token)}  cid={cid[:6]}...")

from dhanhq import DhanContext, dhanhq
ctx  = DhanContext(cid, token)
dhan = dhanhq(ctx)

# List all public methods
methods = [m for m in dir(dhan) if not m.startswith('_')]
print("\nAll public methods on dhanhq instance:")
for m in methods:
    print(" ", m)
