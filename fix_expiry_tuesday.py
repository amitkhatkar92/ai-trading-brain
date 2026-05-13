"""Fix _nearest_expiry to target Tuesday (NSE NIFTY weekly expiry day)."""
import shutil, sys

DHAN = "/app/data_feeds/dhan_feed.py"
HOST = "/root/ai-trading-brain/data_feeds/dhan_feed.py"

with open(DHAN, "r") as f:
    src = f.read()

# Replace the _nearest_expiry probe logic — it was probing API on every call
# which is too slow and hits rate limits.
# NIFTY weekly expiry is on Tuesday (as confirmed by Dhan probe: May 12, May 19)
# If Tuesday is a holiday, fall back to Monday.
OLD = (
    "    def _nearest_expiry(self) -> str:\n"
    "        \"\"\"Return the nearest valid NSE weekly expiry (Thu or prev trading day if holiday).\n"
    "        Tries up to 4 candidate Thursdays via the Dhan API; falls back to next Thu.\"\"\"\n"
    "        today = date.today()\n"
    "        # Build list of next 4 candidate Thursdays\n"
    "        candidates = []\n"
    "        days_to_thu = (3 - today.weekday()) % 7\n"
    "        if days_to_thu == 0:\n"
    "            days_to_thu = 7  # skip today if today is Thursday; use next week\n"
    "        for w in range(4):\n"
    "            thu = today + timedelta(days=days_to_thu + w * 7)\n"
    "            candidates.append(thu)\n"
    "            # Also try Wednesday (day before — holiday fallback)\n"
    "            candidates.append(thu - timedelta(days=1))\n"
    "        candidates.sort()\n"
    "        # Remove past dates\n"
    "        candidates = [d for d in candidates if d >= today]\n"
    "        # If we have a live connection, probe the API for valid expiry\n"
    "        if self._live and self._dhan:\n"
    "            from data_feeds.dhan_feed import DHAN_SECURITY_MAP\n"
    "            nifty_meta = DHAN_SECURITY_MAP.get(\"NIFTY\", {})\n"
    "            for d in candidates:\n"
    "                try:\n"
    "                    r = self._dhan.option_chain(\n"
    "                        under_security_id=int(nifty_meta.get(\"security_id\", 13)),\n"
    "                        under_exchange_segment=\"IDX_I\",\n"
    "                        expiry=d.strftime(\"%Y-%m-%d\"),\n"
    "                    )\n"
    "                    data = (r or {}).get(\"data\", {})\n"
    "                    # If Dhan returns option strikes it's valid\n"
    "                    if r and r.get(\"status\") == \"success\":\n"
    "                        return d.strftime(\"%Y-%m-%d\")\n"
    "                except Exception:\n"
    "                    pass\n"
    "        # Fallback: return earliest candidate Thursday\n"
    "        for d in candidates:\n"
    "            if d.weekday() == 3:  # Thursday\n"
    "                return d.strftime(\"%Y-%m-%d\")\n"
    "        return candidates[0].strftime(\"%Y-%m-%d\")"
)
NEW = (
    "    @staticmethod\n"
    "    def _nearest_expiry() -> str:\n"
    "        \"\"\"Return the nearest NSE weekly expiry as YYYY-MM-DD.\n"
    "        NIFTY weekly options expire on Tuesday (confirmed May 2026).\n"
    "        If Tuesday is a holiday the get_options_chain retry logic\n"
    "        will automatically try Mon/Wed/+1w candidates.\"\"\"\n"
    "        today = date.today()\n"
    "        # days_to_tuesday: 0=Mon,1=Tue,2=Wed,3=Thu,4=Fri,5=Sat,6=Sun\n"
    "        days_to_tue = (1 - today.weekday()) % 7  # 1 = Tuesday\n"
    "        if days_to_tue == 0:\n"
    "            days_to_tue = 7  # already Tuesday → use next Tuesday\n"
    "        return (today + timedelta(days=days_to_tue)).strftime(\"%Y-%m-%d\")"
)

if OLD not in src:
    print("ERROR: _nearest_expiry patch anchor not found")
    sys.exit(1)
src = src.replace(OLD, NEW, 1)
print("Fixed _nearest_expiry() → nearest Tuesday.")

with open(DHAN, "w") as f:
    f.write(src)
# Sync to host
import shutil
shutil.copy2(DHAN, HOST)
print("Synced to host:", HOST)
print("Done — no restart needed (fix is stateless).")
