import sys
sys.path.insert(0, '/app')
from data_feeds.yahoo_feed import YahooFeed
from data_feeds.base_feed import TickerQuote
f = YahooFeed()
print('YahooFeed import OK')
print('has get_feed_diagnostics:', hasattr(f, 'get_feed_diagnostics'))
print('has _ltp_cache:', hasattr(YahooFeed, '_ltp_cache'))
print('has _consec_failures:', hasattr(YahooFeed, '_consec_failures'))
# Check TickerQuote has feed_degraded
import dataclasses
fields = {fld.name for fld in dataclasses.fields(TickerQuote)}
print('TickerQuote.feed_degraded:', 'feed_degraded' in fields)
print('TickerQuote.consecutive_failures:', 'consecutive_failures' in fields)
# Verify feed_degraded TickerQuote can be constructed
tq = TickerQuote(
    symbol='TEST', timestamp=__import__('datetime').datetime.now(),
    ltp=1000.0, open=1000.0, high=1000.0, low=1000.0, close=1000.0,
    change=0.0, change_pct=0.0, volume=0.0,
    feed_degraded=True, consecutive_failures=3
)
print('FEED_DEGRADED TickerQuote:', tq.feed_degraded, tq.consecutive_failures)
print('ALL CHECKS PASSED')
