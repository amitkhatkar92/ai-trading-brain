import yfinance as yf
t = yf.Ticker("TATAMOTORS.NS")
info = t.fast_info
print("lastPrice:", info.get("lastPrice"))
print("previousClose:", info.get("previousClose"))
print("regularMarketPreviousClose:", info.get("regularMarketPreviousClose"))
