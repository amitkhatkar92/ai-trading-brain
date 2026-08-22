"""Forensic: full price path for COALINDIA - what does the feed return?"""
import warnings, sys
warnings.filterwarnings("ignore")
sys.path.insert(0, "/app")

from data_feeds.data_feed_manager import get_feed_manager
feed = get_feed_manager()

# 1. get_multiple_quotes (used by _do_fetch_prices in OE)
print("=== get_multiple_quotes COALINDIA.NS ===")
q = feed.get_multiple_quotes(["COALINDIA.NS"])
if "COALINDIA.NS" in q:
    qq = q["COALINDIA.NS"]
    print(f"  ltp={qq.ltp}  source={getattr(qq,'feed_source','?')}  fallback={getattr(qq,'fallback_active',False)}")
else:
    print("  NOT FOUND in result:", list(q.keys())[:5])

# 2. get_quote (single)
print("=== get_quote COALINDIA.NS ===")
q2 = feed.get_quote("COALINDIA.NS")
if q2:
    print(f"  ltp={q2.ltp}  source={getattr(q2,'feed_source','?')}  fallback={getattr(q2,'fallback_active',False)}")
else:
    print("  returned None")

# 3. Raw yfinance batch download (what _parse_batch_row sees)
import yfinance as yf
import pandas as pd
print("=== yf.download batch with group_by=ticker ===")
data = yf.download("COALINDIA.NS RELIANCE.NS", period="2d", interval="1d",
                   group_by="ticker", auto_adjust=True, progress=False, threads=False)
print("  data.columns type:", type(data.columns).__name__)
print("  data.columns level 0 unique:", list(set(data.columns.get_level_values(0)))[:6])
print("  data.columns level 1 unique:", list(set(data.columns.get_level_values(1)))[:6])
if isinstance(data.columns, pd.MultiIndex):
    try:
        df_c = data["COALINDIA.NS"]
        row_c = df_c.dropna(subset=["Close"]).iloc[-1]
        print(f"  COALINDIA.NS Close: {row_c['Close']} type={type(row_c['Close']).__name__}")
    except Exception as e:
        print(f"  ERROR extracting COALINDIA.NS: {e}")
        print("  first 6 columns:", list(data.columns)[:6])


def normalize(df):
    try:
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.droplevel(level=-1)
            df = df.loc[:, ~df.columns.duplicated()]
    except Exception as e:
        print(f"normalize failed: {e}")
    return df

print("=== yfinance version:", yf.__version__)

# Test with period=22d (exact OE scanner call)
df22 = yf.download("COALINDIA.NS", period="22d", interval="1d",
                   auto_adjust=True, progress=False, threads=False)
print("=== 22d shape:", df22.shape, "cols:", list(df22.columns)[:6])
if not df22.empty:
    df22n = normalize(df22)
    row22 = df22n.iloc[-1]
    c22 = row22.get("Close", "MISSING")
    print("=== 22d last close:", c22, type(c22).__name__)
    try:
        print("=== float(22d close):", float(c22))
    except Exception as e:
        print("=== float(22d close) ERROR:", e)
    # Check all rows for non-float close values
    bad_rows = [(i, type(r.get("Close","")).__name__) for i,r in df22n.iterrows() if not isinstance(r.get("Close",0), (int, float))]
    import numpy as np
    bad_rows2 = [(i, type(r.get("Close","")).__name__) for i,r in df22n.iterrows() if not isinstance(r.get("Close",0), (int, float, np.floating))]
    print("=== non-int/float close rows (excluding numpy):", len(bad_rows2))

df = yf.download("COALINDIA.NS", period="5d", interval="1d",
                 auto_adjust=True, progress=False, threads=False)
print("=== raw columns type:", type(df.columns).__name__)
print("=== raw columns:", list(df.columns)[:10])
print("=== shape:", df.shape)
print("=== empty:", df.empty)

if not df.empty:
    df2 = normalize(df)
    print("=== normalized columns:", list(df2.columns)[:10])
    row = df2.iloc[-1]
    c = row.get("Close", row.get("close", "MISSING"))
    print("=== row['Close'] type:", type(c).__name__)
    print("=== row['Close'] value:", c)
    try:
        print("=== float(Close):", float(c))
    except Exception as e:
        print("=== float() ERROR:", e)
    # Also print actual last close
    print("=== Last row:\n", row)
