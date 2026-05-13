"""Reduce global_sentiment breadth multiplier from 0.15 → 0.05."""
import sys

REGIME_AI = "/app/market_intelligence/market_regime_ai.py"
HOST_PATH = "/root/ai-trading-brain/market_intelligence/market_regime_ai.py"

with open(REGIME_AI, "r") as f:
    src = f.read()

OLD = (
    "        # Global context nudges: strong global signal can flip a borderline regime\n"
    "        # A strong bullish global sentiment (+0.40) adds +0.6% to nifty_chg perception\n"
    "        # A strong bearish signal (\u22120.40) subtracts the same\n"
    "        adjusted_chg = nifty_chg + global_sentiment_score * 1.5\n"
    "        adjusted_breadth = min(1.0, max(0.0, breadth + global_sentiment_score * 0.15))\n"
)
NEW = (
    "        # Global context nudges: strong global signal can flip a borderline regime\n"
    "        # A strong bullish global sentiment (+0.40) adds +0.6% to nifty_chg perception\n"
    "        # A strong bearish signal (\u22120.40) subtracts the same\n"
    "        adjusted_chg = nifty_chg + global_sentiment_score * 1.5\n"
    "        # Breadth multiplier reduced 0.15 \u2192 0.05: domestic internals should dominate;\n"
    "        # global sentiment is contextual only, not a dominant regime override.\n"
    "        adjusted_breadth = min(1.0, max(0.0, breadth + global_sentiment_score * 0.05))\n"
)

if OLD not in src:
    print("ERROR: anchor not found")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(REGIME_AI, "w") as f:
    f.write(src)
print("OK: breadth multiplier 0.15 → 0.05")

import shutil
shutil.copy2(REGIME_AI, HOST_PATH)
print("Synced to host")
