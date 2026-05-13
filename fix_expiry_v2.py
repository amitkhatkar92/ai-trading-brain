"""Fix _nearest_expiry: NIFTY weekly expiry is on Tuesdays (confirmed May 2026)."""
import re, shutil

DHAN = "/app/data_feeds/dhan_feed.py"
HOST = "/root/ai-trading-brain/data_feeds/dhan_feed.py"

with open(DHAN, "r") as f:
    src = f.read()

# Replace the entire _nearest_expiry function (handles both @staticmethod and self variants)
old_pattern = r'    (?:@staticmethod\n    )?def _nearest_expiry\(.*?\) -> str:.*?(?=\n    # ── yfinance fallback)'
new_func = (
    "    @staticmethod\n"
    "    def _nearest_expiry() -> str:\n"
    '        """Return the nearest NSE NIFTY weekly expiry date.\n'
    "        NIFTY weekly options expire on Tuesdays (confirmed via Dhan API, May 2026).\n"
    "        If Tuesday is a holiday, get_options_chain() retry logic auto-tries Mon/Wed.\"\"\"\n"
    "        today = date.today()\n"
    "        # 1 = Tuesday in Python weekday() (Mon=0)\n"
    "        days_to_tue = (1 - today.weekday()) % 7\n"
    "        if days_to_tue == 0:\n"
    "            days_to_tue = 7  # already Tuesday → use next week\n"
    "        return (today + timedelta(days=days_to_tue)).strftime(\"%Y-%m-%d\")\n"
)

new_src = re.sub(old_pattern, new_func, src, flags=re.DOTALL)
if new_src == src:
    print("ERROR: pattern not matched — printing what's near _nearest_expiry:")
    idx = src.find("def _nearest_expiry")
    print(repr(src[idx-20:idx+300]))
    import sys; sys.exit(1)

with open(DHAN, "w") as f:
    f.write(new_src)
# Sync to host
shutil.copy2(DHAN, HOST)
print("OK: _nearest_expiry → nearest Tuesday. Synced to host.")

# Quick verify
idx = new_src.find("def _nearest_expiry")
print("New function:")
print(new_src[idx-20:idx+400])
