from pathlib import Path
p = Path('/tmp/angel_current.py')
text = p.read_text(encoding='utf-8')
BAD  = 'from utils.symbol_utils import normalize_symbol as _normalize_symbol, OptionsChain, OptionsContract, PriceBar, TickerQuote'
GOOD = ('from .base_feed import BaseFeed, OptionsChain, OptionsContract, PriceBar, TickerQuote\n'
        'from utils.symbol_utils import normalize_symbol as _normalize_symbol')
if BAD in text:
    fixed = text.replace(BAD, GOOD, 1)
    p.write_text(fixed, encoding='utf-8')
    print('OK')
else:
    print('BAD NOT FOUND')
