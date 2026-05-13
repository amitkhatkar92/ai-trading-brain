"""Add reconnect() to DataFeedManager only."""
import sys

FM = "/app/data_feeds/data_feed_manager.py"

with open(FM, "r") as f:
    fm_src = f.read()

if "def reconnect" in fm_src:
    print("Already present.")
    sys.exit(0)

OLD_FM = (
    "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
    "\n"
    "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
)
NEW_FM = (
    "    # ── Reconnect (after /token refresh) ────────────────────────────────────\n"
    "\n"
    "    def reconnect(self) -> None:\n"
    "        \"\"\"Reinitialise DhanFeed client with latest DHAN_ACCESS_TOKEN.\"\"\"\n"
    "        self.dhan.reconnect()\n"
    "\n"
    "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
    "\n"
    "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
)

if OLD_FM not in fm_src:
    print("ERROR: anchor not found")
    sys.exit(1)

fm_src = fm_src.replace(OLD_FM, NEW_FM, 1)
with open(FM, "w") as f:
    f.write(fm_src)
print("OK: reconnect() added to DataFeedManager")
