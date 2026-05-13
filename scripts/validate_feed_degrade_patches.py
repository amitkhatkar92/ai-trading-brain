"""Full validation of all 4 patched files."""
import sys
sys.path.insert(0, '/app')

errors = []

# 1. base_feed - TickerQuote has new fields
try:
    import dataclasses
    from data_feeds.base_feed import TickerQuote
    fields = {f.name for f in dataclasses.fields(TickerQuote)}
    assert 'feed_degraded' in fields, 'feed_degraded missing'
    assert 'consecutive_failures' in fields, 'consecutive_failures missing'
    tq = TickerQuote(
        symbol='X', timestamp=__import__('datetime').datetime.now(),
        ltp=100.0, open=100.0, high=100.0, low=100.0, close=100.0,
        change=0.0, change_pct=0.0, volume=0.0,
        feed_degraded=True, consecutive_failures=5
    )
    assert tq.feed_degraded is True
    assert tq.consecutive_failures == 5
    print('[OK] base_feed.TickerQuote has feed_degraded + consecutive_failures')
except Exception as e:
    errors.append(f'base_feed: {e}')

# 2. yahoo_feed - new fields + diagnostics
try:
    from data_feeds.yahoo_feed import YahooFeed
    f = YahooFeed()
    assert hasattr(YahooFeed, '_ltp_cache'), '_ltp_cache missing'
    assert hasattr(YahooFeed, '_consec_failures'), '_consec_failures missing'
    assert hasattr(f, 'get_feed_diagnostics'), 'get_feed_diagnostics missing'
    # Verify _sim_quote no longer appears in get_multiple_quotes failure path
    import inspect
    src = inspect.getsource(f.get_multiple_quotes)
    assert '_sim_quote' not in src, '_sim_quote still in get_multiple_quotes!'
    print('[OK] yahoo_feed: LTP cache, no sim fallback, diagnostics OK')
except Exception as e:
    errors.append(f'yahoo_feed: {e}')

# 3. trade_monitor - new signature + degraded tracking
try:
    from trade_monitoring.trade_monitor import TradeMonitor
    import inspect
    tm = TradeMonitor()
    assert hasattr(tm, '_feed_degraded_cycles'), '_feed_degraded_cycles missing'
    assert hasattr(tm, 'get_feed_degraded_summary'), 'get_feed_degraded_summary missing'
    sig = inspect.signature(tm.check_all)
    assert 'degraded_symbols' in sig.parameters, 'degraded_symbols param missing from check_all'
    src = inspect.getsource(tm.check_all)
    assert '_sym_degraded' in src, '_sym_degraded flag missing'
    assert 'not _sym_degraded' in src, 'adaptive suppression guard missing'
    print('[OK] trade_monitor: degraded guard, signature, adaptive suppression OK')
except Exception as e:
    errors.append(f'trade_monitor: {e}')

# 4. master_orchestrator imports
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('mo', '/app/orchestrator/master_orchestrator.py')
    # Just parse/compile, don't exec (avoids side effects)
    with open('/app/orchestrator/master_orchestrator.py', encoding='utf-8') as mf:
        msrc = mf.read()
    compile(msrc, 'master_orchestrator.py', 'exec')
    assert '_feed_degraded_counts' in msrc, '_feed_degraded_counts missing from orchestrator'
    assert '_degraded_syms' in msrc, '_degraded_syms missing from orchestrator'
    assert 'degraded_symbols=_degraded_syms' in msrc, 'check_all call not wired'
    assert 'FEED_DEGRADED_ESCALATION' in msrc, 'escalation log missing'
    print('[OK] master_orchestrator: compiles, degraded wiring, escalation OK')
except Exception as e:
    errors.append(f'master_orchestrator: {e}')

if errors:
    print('\nFAILURES:')
    for e in errors:
        print(' -', e)
    sys.exit(1)
else:
    print('\nALL 4 PATCHES VALIDATED SUCCESSFULLY')
