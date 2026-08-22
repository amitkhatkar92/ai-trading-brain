import sys
sys.path.insert(0, '/app')
from data_feeds.angelone_feed import AngelOneFeed

feed = AngelOneFeed()
if not feed._connected:
    print('NOT CONNECTED'); sys.exit(1)

print('=== searchScrip NFO BANKNIFTY ===')
resp = feed._smart.searchScrip("NFO", "BANKNIFTY")
if not resp or not resp.get("data"):
    print(f'EMPTY response: {resp}')
    sys.exit(1)

data = resp["data"]
print(f'Total results: {len(data)}')

# Show first 10
for c in data[:10]:
    print(f'  ts={c.get("tradingsymbol")} token={c.get("symboltoken")} exch={c.get("exchange")}')

# Check what expiry tags appear
import re
tags = set()
for c in data:
    ts = (c.get("tradingsymbol") or "").upper()
    if ts.startswith("BANKNIFTY"):
        tag = ts[9:16]
        tags.add(tag)

print(f'\nExpiry tags found in contracts: {sorted(tags)}')

# Also try NIFTY for comparison
print('\n=== searchScrip NFO NIFTY (first 5) ===')
resp2 = feed._smart.searchScrip("NFO", "NIFTY")
data2 = resp2.get("data", [])
print(f'Total NIFTY results: {len(data2)}')
nifty_tags = set()
for c in data2:
    ts = (c.get("tradingsymbol") or "").upper()
    if ts.startswith("NIFTY") and not ts.startswith("NIFTYBANK") and not ts.startswith("NIFTYMID") and not ts.startswith("NIFTYFIN"):
        tag = ts[5:12]
        nifty_tags.add(tag)
print(f'NIFTY expiry tags: {sorted(nifty_tags)}')

# Now actually test get_options_chain
print('\n=== get_options_chain(BANKNIFTY) ===')
chain = feed.get_options_chain("BANKNIFTY")
if chain:
    print(f'CHAIN OK: contracts={len(getattr(chain,"contracts",[]))} spot={getattr(chain,"spot",None)}')
else:
    print('CHAIN RETURNED NONE')

print('DONE')
