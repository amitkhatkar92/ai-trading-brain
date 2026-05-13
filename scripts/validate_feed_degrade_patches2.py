"""Full validation of all 4 patched files (corrected assertion)."""
import sys
sys.path.insert(0, '/app')

errors = []

# 1. base_feed
try:
    import dataclasses
    from data_feeds.base_feed import TickerQuote
    fields = {f.name for f in dataclasses.fields(TickerQuote)}
    assert 'feed_degraded' in fields
    assert 'consecutive_failures' in fields
    tq = TickerQuote(
        symbol='X', timestamp=__import__('datetime').datetime.now(),
        ltp=100.0, open=100.0, high=100.0, low=100.0, close=100.0,
        change=0.0, change_pct=0.0, volume=0.0,
        feed_degraded=True, consecutive_failures=5
    )
    assert tq.feed_degraded is True and tq.consecutive_failures == 5
    print('[OK] base_feed.TickerQuote: feed_degraded + consecutive_failures')
except Exception as e:
    errors.append(f'base_feed: {e}')

# 2. yahoo_feed
try:
    import inspect
    from data_feeds.yahoo_feed import YahooFeed
    f = YahooFeed()
    assert hasattr(YahooFeed, '_ltp_cache')
    assert hasattr(YahooFeed, '_consec_failures')
    assert hasattr(f, 'get_feed_diagnostics')

    # Key assertion: in the get_multiple_quotes retry path (when _available=True
    # but individual symbol fails), there must be NO _sim_quote call.
    # The only remaining _sim_quote calls should be in the 'not self._available' guard.
    src = inspect.getsource(f.get_multiple_quotes)

    # The retry block (comes after "retrying individually" log line) must not call _sim_quote
    retry_idx = src.find('retrying individually')
    assert retry_idx >= 0, 'retry block not found'
    retry_section = src[retry_idx:]
    assert '_sim_quote' not in retry_section, (
        '_sim_quote still called in retry failure path:\n' + retry_section[:500]
    )
    # The "not self._available" guard at the top may still use _sim_quote - that's OK
    not_avail_idx = src.find('not self._available')
    if not_avail_idx >= 0:
        not_avail_section = src[not_avail_idx:not_avail_idx+200]
        print(f'  (note: _sim_quote in not-available guard at top is expected/OK)')

    # Confirm FEED_DEGRADED TickerQuote is constructed on failure
    assert 'feed_degraded=True' in retry_section, 'feed_degraded=True not set in retry failure'
    print('[OK] yahoo_feed: no sim injection in retry path, feed_degraded=True on failure')
except Exception as e:
    errors.append(f'yahoo_feed: {e}')

# 3. trade_monitor
try:
    import inspect
    from trade_monitoring.trade_monitor import TradeMonitor
    tm = TradeMonitor()
    assert hasattr(tm, '_feed_degraded_cycles')
    assert hasattr(tm, 'get_feed_degraded_summary')
    sig = inspect.signature(tm.check_all)
    assert 'degraded_symbols' in sig.parameters
    src = inspect.getsource(tm.check_all)
    assert '_sym_degraded' in src
    assert 'not _sym_degraded' in src, 'adaptive suppression guard missing'
    assert 'FEED_DEGRADED' in src, 'FEED_DEGRADED warning log missing'
    print('[OK] trade_monitor: degraded guard + adaptive suppression')
except Exception as e:
    errors.append(f'trade_monitor: {e}')

# 4. master_orchestrator
try:
    with open('/app/orchestrator/master_orchestrator.py', encoding='utf-8') as mf:
        msrc = mf.read()
    compile(msrc, 'master_orchestrator.py', 'exec')
    assert '_feed_degraded_counts' in msrc
    assert '_degraded_syms' in msrc
    assert 'degraded_symbols=_degraded_syms' in msrc
    assert 'FEED_DEGRADED_ESCALATION' in msrc
    assert 'FEED_DEGRADED_ALERT_CYCLES' in msrc
    print('[OK] master_orchestrator: compiles, escalation wired')
except Exception as e:
    errors.append(f'master_orchestrator: {e}')

if errors:
    print('\nFAILURES:')
    for e in errors:
        print(' -', e)
    sys.exit(1)
else:
    print('\nALL 4 PATCHES VALIDATED SUCCESSFULLY')
    print('Ready to restart container.')
