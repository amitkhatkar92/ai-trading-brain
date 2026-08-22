import sys
sys.path.insert(0, '/app')
import yfinance as yf

print('=== yfinance NSE batch test ===')
# Test 1: small batch, 5m interval
try:
    d = yf.download('SUNPHARMA.NS HDFCBANK.NS RELIANCE.NS', period='1d', interval='5m', timeout=5, progress=False)
    print(f'5m batch 3 symbols: rows={len(d)} ok={not d.empty}')
except Exception as e:
    print(f'5m batch 3 symbols FAILED: {e}')

# Test 2: 2d daily (same as system uses)
try:
    d2 = yf.download('SUNPHARMA.NS HDFCBANK.NS', period='2d', interval='1d', timeout=5, progress=False)
    print(f'2d daily 2 symbols: rows={len(d2)} ok={not d2.empty}')
except Exception as e:
    print(f'2d daily FAILED: {e}')

# Test 3: single symbol
try:
    import yfinance as yf2
    t = yf2.Ticker('SUNPHARMA.NS')
    info = t.fast_info
    print(f'Single SUNPHARMA.NS: ltp={getattr(info, "last_price", None)}')
except Exception as e:
    print(f'Single symbol FAILED: {e}')

# Test 4: via YahooFeed (system's path)
from data_feeds.yahoo_feed import YahooFeed
yf_feed = YahooFeed()
q = yf_feed.get_quote('SUNPHARMA.NS')
print(f'YahooFeed.get_quote(SUNPHARMA.NS): {q}')
qs = yf_feed.get_multiple_quotes(['SUNPHARMA.NS', 'HDFCBANK.NS', 'RELIANCE.NS'])
print(f'YahooFeed.get_multiple_quotes 3 symbols: got={len(qs)} keys={list(qs.keys())}')

print('TEST DONE')
