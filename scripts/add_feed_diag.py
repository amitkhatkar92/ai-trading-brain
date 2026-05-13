"""Add get_feed_diagnostics to yahoo_feed.py"""
path = '/app/data_feeds/yahoo_feed.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

if 'get_feed_diagnostics' not in src:
    marker = '\n    _SIM_BASE: Dict[str, float] = {'
    diag = (
        '\n'
        '    def get_feed_diagnostics(self):\n'
        '        """Per-symbol feed degradation diagnostics."""\n'
        '        from datetime import datetime as _dtnow\n'
        '        out = {}\n'
        '        for sym, entry in YahooFeed._ltp_cache.items():\n'
        '            ltp, ts = entry\n'
        '            age_s = (_dtnow.now() - ts).total_seconds()\n'
        '            fails = YahooFeed._consec_failures.get(sym, 0)\n'
        '            out[sym] = dict(\n'
        '                last_valid_ltp=round(ltp, 2),\n'
        '                last_valid_ltp_ts=ts.strftime("%H:%M:%S"),\n'
        '                age_seconds=round(age_s),\n'
        '                consecutive_failures=fails,\n'
        '                feed_degraded=(fails > 0),\n'
        '            )\n'
        '        return out\n'
    )
    if marker in src:
        src = src.replace(marker, diag + marker, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        print('get_feed_diagnostics inserted OK')
    else:
        print('ERROR: _SIM_BASE marker not found')
else:
    print('already present')
