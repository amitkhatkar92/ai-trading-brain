import sys
sys.path.insert(0, '/app')
from utils.symbol_utils import normalize_symbol, get_normalization_health
r = normalize_symbol('JSWSTEEL   ')
print(repr(r), '== JSWSTEEL:', r == 'JSWSTEEL')
h = get_normalization_health()
print('health:', h)
