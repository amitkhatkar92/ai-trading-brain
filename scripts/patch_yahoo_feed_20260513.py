"""
Patch yahoo_feed.py:
  - Add LTP cache (last-known-good per symbol)
  - Stop synthetic random injection on feed failure
  - Return TickerQuote(feed_degraded=True, ltp=cached_ltp) instead
  - Cache successful batch + individual fetches
  - Add get_feed_diagnostics() method
"""
import sys

path = '/app/data_feeds/yahoo_feed.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

steps_ok = 0

# ── 1. Typing imports ────────────────────────────────────────────────────────
old = 'from typing import Dict, List, Optional'
new = 'from typing import Dict, List, Optional, Set, Tuple'
if old in src:
    src = src.replace(old, new, 1)
    steps_ok += 1
    print('1. imports updated')
else:
    print('WARN 1: import line not found (already patched?)')

# ── 2. Class-level LTP cache + failure tracking ──────────────────────────────
marker = '    def __init__(self) -> None:'
if '_ltp_cache' not in src:
    class_vars = (
        '    # Feed degradation tracking: last-known-good LTP cache per symbol\n'
        '    _ltp_cache:       Dict[str, Tuple[float, object]] = {}\n'
        '    _consec_failures: Dict[str, int]                  = {}\n'
        '    FEED_DEGRADED_WARN_CYCLES: int = 3\n'
        '\n'
        '    def __init__(self) -> None:'
    )
    if marker in src:
        src = src.replace(marker, class_vars, 1)
        steps_ok += 1
        print('2. class vars added')
    else:
        print('ERROR 2: __init__ marker not found'); sys.exit(1)
else:
    steps_ok += 1
    print('2. class vars already present')

# ── 3. Retry block: replace _sim_quote with cached LTP ──────────────────────
old_sim_warn = (
    '                        log.warning("[YahooFeed] %s unavailable after retry \u2014 using SIM", sym)\n'
    '                        results[sym] = self._sim_quote(sym)'
)
new_cached = (
    '                        cached = YahooFeed._ltp_cache.get(tkr) or YahooFeed._ltp_cache.get(sym)\n'
    '                        fails  = YahooFeed._consec_failures.get(tkr, 0) + 1\n'
    '                        YahooFeed._consec_failures[tkr] = fails\n'
    '                        if cached:\n'
    '                            cached_ltp, cached_ts = cached\n'
    '                            age_s = (datetime.now() - cached_ts).total_seconds()\n'
    '                            log.warning(\n'
    '                                "[YahooFeed] FEED_DEGRADED %s -- fails=%d"\n'
    '                                "  last_valid_ltp=%.2f  age=%.0fs",\n'
    '                                sym, fails, cached_ltp, age_s,\n'
    '                            )\n'
    '                            results[sym] = TickerQuote(\n'
    '                                symbol=sym, timestamp=datetime.now(),\n'
    '                                ltp=cached_ltp, open=cached_ltp,\n'
    '                                high=cached_ltp, low=cached_ltp, close=cached_ltp,\n'
    '                                change=0.0, change_pct=0.0, volume=0.0,\n'
    '                                feed_degraded=True,\n'
    '                                consecutive_failures=fails,\n'
    '                            )\n'
    '                        else:\n'
    '                            log.warning(\n'
    '                                "[YahooFeed] FEED_DEGRADED %s -- fails=%d"\n'
    '                                "  no cached LTP -- symbol excluded from price_feed",\n'
    '                                sym, fails,\n'
    '                            )\n'
    '                            # Excluded: orchestrator treats missing key as skip'
)
if old_sim_warn in src:
    src = src.replace(old_sim_warn, new_cached, 1)
    steps_ok += 1
    print('3. retry sim fallback replaced with cache fallback')
else:
    print('ERROR 3: retry sim warn string not found'); sys.exit(1)

# ── 4. _live_quote: return None on failure; cache on success ────────────────
old_hist_empty_sim = '            if hist.empty:\n                return self._sim_quote(alias)'
new_hist_empty_none = '            if hist.empty:\n                return None'
if old_hist_empty_sim in src:
    src = src.replace(old_hist_empty_sim, new_hist_empty_none, 1)
    print('4a. hist.empty sim replaced with None')
elif 'return None  # propagate' in src:
    print('4a. already patched')

old_live_return = (
    '            return TickerQuote(\n'
    '                symbol     = alias,\n'
    '                timestamp  = datetime.now(),\n'
    '                ltp        = ltp,\n'
    '                open       = float(row["Open"]),\n'
    '                high       = float(row["High"]),\n'
    '                low        = float(row["Low"]),\n'
    '                close      = float(prev),\n'
    '                change     = round(change, 4),\n'
    '                change_pct = round(change / prev * 100, 4) if prev else 0.0,\n'
    '                volume     = float(row.get("Volume", 0)),\n'
    '            )\n'
    '        except Exception as exc:\n'
    '            log.debug("[YahooFeed] live_quote %s failed: %s \u2014 using sim", ticker, exc)\n'
    '            return self._sim_quote(alias)'
)
new_live_return = (
    '            quote = TickerQuote(\n'
    '                symbol     = alias,\n'
    '                timestamp  = datetime.now(),\n'
    '                ltp        = ltp,\n'
    '                open       = float(row["Open"]),\n'
    '                high       = float(row["High"]),\n'
    '                low        = float(row["Low"]),\n'
    '                close      = float(prev),\n'
    '                change     = round(change, 4),\n'
    '                change_pct = round(change / prev * 100, 4) if prev else 0.0,\n'
    '                volume     = float(row.get("Volume", 0)),\n'
    '            )\n'
    '            YahooFeed._ltp_cache[ticker]       = (ltp, datetime.now())\n'
    '            YahooFeed._ltp_cache[alias]        = (ltp, datetime.now())\n'
    '            YahooFeed._consec_failures[ticker] = 0\n'
    '            return quote\n'
    '        except Exception as exc:\n'
    '            log.debug("[YahooFeed] live_quote %s failed: %s", ticker, exc)\n'
    '            return None'
)
if old_live_return in src:
    src = src.replace(old_live_return, new_live_return, 1)
    steps_ok += 1
    print('4b. _live_quote cache + None-return updated')
else:
    print('ERROR 4b: _live_quote return block not found'); sys.exit(1)

# ── 5. _parse_batch_row: cache on success ───────────────────────────────────
old_parse_return = (
    '            return TickerQuote(\n'
    '                symbol=alias, timestamp=datetime.now(),\n'
    '                ltp=ltp, open=float(row["Open"]),\n'
    '                high=float(row["High"]), low=float(row["Low"]),\n'
    '                close=float(prev), change=round(chg, 4),\n'
    '                change_pct=round(chg / prev * 100, 4) if prev else 0.0,\n'
    '                volume=float(row.get("Volume", 0)),\n'
    '            )\n'
    '        except Exception:\n'
    '            return None'
)
new_parse_return = (
    '            quote = TickerQuote(\n'
    '                symbol=alias, timestamp=datetime.now(),\n'
    '                ltp=ltp, open=float(row["Open"]),\n'
    '                high=float(row["High"]), low=float(row["Low"]),\n'
    '                close=float(prev), change=round(chg, 4),\n'
    '                change_pct=round(chg / prev * 100, 4) if prev else 0.0,\n'
    '                volume=float(row.get("Volume", 0)),\n'
    '            )\n'
    '            YahooFeed._ltp_cache[ticker] = (ltp, datetime.now())\n'
    '            YahooFeed._ltp_cache[alias]  = (ltp, datetime.now())\n'
    '            YahooFeed._consec_failures[ticker] = 0\n'
    '            return quote\n'
    '        except Exception:\n'
    '            return None'
)
if old_parse_return in src:
    src = src.replace(old_parse_return, new_parse_return, 1)
    steps_ok += 1
    print('5. _parse_batch_row cache updated')
else:
    print('ERROR 5: _parse_batch_row return block not found'); sys.exit(1)

# ── 6. Add get_feed_diagnostics() method ────────────────────────────────────
sim_section = '    # \u2500\u2500 Simulation fallback \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500'
diag_block = (
    '    def get_feed_diagnostics(self) -> Dict[str, dict]:\n'
    '        """Return per-symbol feed quality diagnostics (degradation state)."""\n'
    '        out = {}\n'
    '        for sym, (ltp, ts) in YahooFeed._ltp_cache.items():\n'
    '            from datetime import datetime as _dtnow\n'
    '            age_s = (_dtnow.now() - ts).total_seconds()\n'
    '            fails = YahooFeed._consec_failures.get(sym, 0)\n'
    '            out[sym] = {\n'
    '                "last_valid_ltp":        round(ltp, 2),\n'
    '                "last_valid_ltp_ts":     ts.strftime("%H:%M:%S"),\n'
    '                "age_seconds":           round(age_s),\n'
    '                "consecutive_failures":  fails,\n'
    '                "feed_degraded":         fails > 0,\n'
    '            }\n'
    '        return out\n'
    '\n'
    '    # \u2500\u2500 Simulation fallback \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500'
)
if sim_section in src and 'get_feed_diagnostics' not in src:
    src = src.replace(sim_section, diag_block, 1)
    steps_ok += 1
    print('6. get_feed_diagnostics() added')
elif 'get_feed_diagnostics' in src:
    steps_ok += 1
    print('6. get_feed_diagnostics already present')
else:
    print('WARN 6: sim section marker not found (box chars may differ)')

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'\nyahoo_feed.py patched OK  ({steps_ok} steps applied)')
