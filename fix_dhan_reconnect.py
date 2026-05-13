"""Add reconnect() to DhanFeed after _connect()."""
import sys

DHAN = "/app/data_feeds/dhan_feed.py"

with open(DHAN, "r") as f:
    src = f.read()

if "def reconnect" in src:
    print("Already present")
    sys.exit(0)

OLD = '    def _load_instrument_list(self) -> None:'
NEW = '''    def reconnect(self) -> None:
        """Re-initialise dhanhq client with the current DHAN_ACCESS_TOKEN env var.
        Called by the Telegram /token command after updating os.environ."""
        self._dhan = None
        self._context = None
        self._live = False
        self._connect()
        if self._live:
            import logging; logging.getLogger(__name__).info("[DhanFeed] Reconnected successfully with new token.")
        else:
            import logging; logging.getLogger(__name__).warning("[DhanFeed] Reconnect failed — still in simulation mode.")

    def _load_instrument_list(self) -> None:'''

if OLD not in src:
    print("ERROR: anchor not found")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(DHAN, "w") as f:
    f.write(src)
print("OK: DhanFeed.reconnect() added")
