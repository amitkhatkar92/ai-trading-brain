"""Debug: check what LTPs _prefetch_restored_ltps would get for raw symbol names."""
import sys
sys.path.insert(0, "/app")
from data_feeds.yahoo_feed import YahooFeed
f = YahooFeed()
syms = ["NIFTY", "ICICIBANK", "COALINDIA", "TATASTEEL", "HDFCBANK", "BANKBARODA"]
q = f.get_multiple_quotes(syms)
for sym, quote in q.items():
    if quote:
        print(f"{sym}: ltp={round(quote.ltp, 2)}")
    else:
        print(f"{sym}: None")
