import yfinance as yf
t = yf.Ticker("TATAMOTORS.NS")
info = t.fast_info
print("last_price:", info.get("last_price") or info.get("regularMarketPrice"))
print("Keys:", list(info))
