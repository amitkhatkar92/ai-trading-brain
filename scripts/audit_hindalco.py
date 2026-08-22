import yfinance as yf

h = yf.download('HINDALCO.NS', start='2026-05-10', end='2026-05-30', interval='1d', progress=False)
print('HINDALCO.NS actual daily close prices:')
print(h[['Close']].to_string())

# Also check what the feed manager currently returns for HINDALCO
try:
    from data_feeds.data_feed_manager import DataFeedManager
    dfm = DataFeedManager()
    q = dfm.get_quote('HINDALCO.NS')
    if q:
        print(f'\nLIVE FEED: HINDALCO.NS ltp={q.ltp:.2f} source={q.source}')
    else:
        print('\nLIVE FEED: No quote returned')
except Exception as e:
    print(f'\nFeed error: {e}')
