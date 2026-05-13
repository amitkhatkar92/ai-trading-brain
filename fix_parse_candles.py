"""Fix _parse_candles (nested data key) and add reconnect() to DataFeedManager."""
import sys, shutil

DHAN = "/app/data_feeds/dhan_feed.py"
FM   = "/app/data_feeds/data_feed_manager.py"
HOST_DHAN = "/root/ai-trading-brain/data_feeds/dhan_feed.py"
HOST_FM   = "/root/ai-trading-brain/data_feeds/data_feed_manager.py"

# ── Fix 1: _parse_candles — extract from resp["data"] ──────────────────────
with open(DHAN, "r") as f:
    src = f.read()

OLD = (
    '    def _parse_candles(symbol: str, resp: Any, interval: str) -> List[PriceBar]:\n'
    '        """Parse Dhan historical/intraday response \u2192 List[PriceBar]."""\n'
    '        if not resp:\n'
    '            return []\n'
    '        # Dhan returns {"open": [...], "high": [...], "low": [...],\n'
    '        #               "close": [...], "volume": [...], "start_Time": [...]}\n'
    '        try:\n'
    '            data  = resp if isinstance(resp, dict) else {}\n'
    '            opens  = data.get("open",       [])\n'
)
NEW = (
    '    def _parse_candles(symbol: str, resp: Any, interval: str) -> List[PriceBar]:\n'
    '        """Parse Dhan historical/intraday response \u2192 List[PriceBar]."""\n'
    '        if not resp:\n'
    '            return []\n'
    '        # Dhan wraps candle arrays under resp["data"]:\n'
    '        # {"status":"success","data":{"open":[...],"high":[...],...,"timestamp":[...]}}\n'
    '        try:\n'
    '            raw   = resp if isinstance(resp, dict) else {}\n'
    '            # Extract nested "data" key if present\n'
    '            data  = raw.get("data", raw) if isinstance(raw.get("data"), dict) else raw\n'
    '            opens  = data.get("open",       [])\n'
)

if OLD not in src:
    print("ERROR: _parse_candles anchor not found")
    # Show what's there
    idx = src.find("def _parse_candles")
    print(repr(src[idx:idx+300]))
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
print("Fix 1: _parse_candles — extracts nested data dict")

with open(DHAN, "w") as f:
    f.write(src)
shutil.copy2(DHAN, HOST_DHAN)
print("  Synced dhan_feed.py to host")

# ── Fix 2: DataFeedManager.reconnect() ─────────────────────────────────────
with open(FM, "r") as f:
    fm_src = f.read()

if "def reconnect" in fm_src:
    print("Fix 2: reconnect() already in DataFeedManager")
else:
    OLD_FM = (
        "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
        "\n"
        "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
    )
    NEW_FM = (
        "    # ── Reconnect (after /token refresh) ────────────────────────────────────\n"
        "\n"
        "    def reconnect(self) -> None:\n"
        '        """Reinitialise the DhanFeed client with the latest DHAN_ACCESS_TOKEN.\n'
        "        Called by the Telegram /token command after updating os.environ.\"\"\"\n"
        "        self.dhan.reconnect()\n"
        "\n"
        "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
        "\n"
        "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
    )
    if OLD_FM not in fm_src:
        print("ERROR: DataFeedManager patch anchor not found")
        sys.exit(1)
    fm_src = fm_src.replace(OLD_FM, NEW_FM, 1)
    with open(FM, "w") as f:
        f.write(fm_src)
    shutil.copy2(FM, HOST_FM)
    print("Fix 2: reconnect() added to DataFeedManager. Synced to host.")

print("\nAll fixes applied.")
