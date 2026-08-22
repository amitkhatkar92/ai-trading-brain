"""
Smoke test — AngelOne as PRIMARY feed.
Run:  PYTHONPATH=/app python3 /tmp/smoke_ao_audit.py
"""
import sys, os
os.environ.setdefault("ACTIVE_BROKER", "angelone")

errors = []

# 1. Imports
try:
    from data_feeds.options_feed import OptionsFeed
    from data_feeds.data_feed_manager import DataFeedManager, get_feed_manager
    print("[OK] imports")
except Exception as e:
    errors.append(f"[FAIL] imports: {e}")

# 2. get_quote() — AngelOne comes before Dhan
try:
    import inspect
    from data_feeds.data_feed_manager import DataFeedManager
    src = inspect.getsource(DataFeedManager.get_quote)
    ao_pos   = src.index("angelone.get_quote")
    dhan_pos = src.index("dhan.get_quote")
    assert ao_pos < dhan_pos, f"Dhan ({dhan_pos}) before AngelOne ({ao_pos}) in get_quote"
    print("[OK] get_quote: AngelOne first")
except Exception as e:
    errors.append(f"[FAIL] get_quote priority: {e}")

# 3. get_multiple_quotes() — AngelOne primary
try:
    src = inspect.getsource(DataFeedManager.get_multiple_quotes)
    assert "angelone.get_multiple_quotes" in src, "AngelOne not in get_multiple_quotes"
    ao_pos = src.index("angelone.get_multiple_quotes")
    dhan_pos = src.index("dhan.get_multiple_quotes")
    assert ao_pos < dhan_pos, "Dhan before AngelOne in get_multiple_quotes"
    print("[OK] get_multiple_quotes: AngelOne first")
except Exception as e:
    errors.append(f"[FAIL] get_multiple_quotes priority: {e}")

# 4. get_history() — AngelOne primary
try:
    src = inspect.getsource(DataFeedManager.get_history)
    ao_pos   = src.index("angelone.get_history")
    dhan_pos = src.index("dhan.get_history")
    assert ao_pos < dhan_pos, "Dhan before AngelOne in get_history"
    print("[OK] get_history: AngelOne first")
except Exception as e:
    errors.append(f"[FAIL] get_history priority: {e}")

# 5. get_options_chain() — AngelOne primary
try:
    src = inspect.getsource(DataFeedManager.get_options_chain)
    ao_pos   = src.index("angelone.get_options_chain")
    dhan_pos = src.index("dhan.get_options_chain")
    assert ao_pos < dhan_pos, "Dhan before AngelOne in get_options_chain"
    print("[OK] get_options_chain: AngelOne first")
except Exception as e:
    errors.append(f"[FAIL] get_options_chain priority: {e}")

# 6. options_feed._fetch_live() — AngelOne path comes before Dhan path
try:
    src = inspect.getsource(OptionsFeed._fetch_live)
    assert "Path 1: AngelOne" in src or "Path 1:" in src, "Path 1 label missing"
    ao_pos   = src.index("AngelOne live chain")  # appears in first block
    dhan_pos = src.index("Dhan live chain")
    assert ao_pos < dhan_pos, "Dhan before AngelOne in _fetch_live"
    print("[OK] options_feed._fetch_live: AngelOne first")
except Exception as e:
    errors.append(f"[FAIL] options_feed._fetch_live priority: {e}")

# 7. Live connectivity
try:
    fm = get_feed_manager()
    ao = getattr(fm, "angelone", None)
    assert ao is not None, "angelone attr missing"
    print(f"[OK] DataFeedManager.angelone present — is_live={ao.is_live}")
    if ao.is_live:
        q = fm.get_quote("NIFTY")
        assert q and q.ltp and q.ltp > 0, f"bad quote: {q}"
        assert "ANGELONE" in (getattr(q, "feed_source", "") or "").upper(), \
            f"Expected ANGELONE source but got: {q.feed_source}"
        print(f"[OK] NIFTY via get_quote → source={q.feed_source}  LTP={q.ltp}")
    else:
        print("[SKIP] AngelOne not live")
except Exception as e:
    errors.append(f"[FAIL] live connectivity: {e}")

if errors:
    print("\n--- FAILURES ---")
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print("\n=== ALL CHECKS PASSED — AngelOne is PRIMARY ===")
