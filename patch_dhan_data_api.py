"""
Patch dhan_feed.py and data_feed_manager.py:
1. Add reconnect() to DhanFeed (reinitializes dhanhq client with current env token)
2. Add reconnect() to DataFeedManager (calls dhan.reconnect())
3. Fix _nearest_expiry() — try multiple Thursdays, skip NSE holidays
4. Fix get_options_chain() — retry with next expiry if invalid
5. Remove :ro from .env mount in docker-compose.yml
"""
import shutil, sys, os

DHAN = "/app/data_feeds/dhan_feed.py"
FM   = "/app/data_feeds/data_feed_manager.py"
DC   = "/root/ai-trading-brain/docker-compose.yml"

for f in [DHAN, FM]:
    shutil.copy2(f, f + ".bak_dataapi")
print("Backups created.")

# ── 1. Patch dhan_feed.py ─────────────────────────────────────────────────────
with open(DHAN, "r") as f:
    src = f.read()

# 1a. Add reconnect() method after _connect()
OLD_CONNECT_END = (
    "        except Exception as exc:\n"
    "            log.error(\"[DhanFeed] Connection failed: %s — falling back to simulation.\", exc)\n"
    "\n"
    "    def _load_instrument_list(self)"
)
NEW_CONNECT_END = (
    "        except Exception as exc:\n"
    "            log.error(\"[DhanFeed] Connection failed: %s — falling back to simulation.\", exc)\n"
    "\n"
    "    def reconnect(self) -> None:\n"
    "        \"\"\"Re-initialise dhanhq client with the current DHAN_ACCESS_TOKEN env var.\n"
    "        Call this after updating the token via /token Telegram command.\"\"\"\n"
    "        self._dhan   = None\n"
    "        self._context = None\n"
    "        self._live   = False\n"
    "        self._connect()\n"
    "        if self._live:\n"
    "            log.info(\"[DhanFeed] Reconnected successfully with new token.\")\n"
    "        else:\n"
    "            log.warning(\"[DhanFeed] Reconnect failed — still in simulation mode.\")\n"
    "\n"
    "    def _load_instrument_list(self)"
)
if OLD_CONNECT_END not in src:
    print("ERROR: reconnect patch anchor not found"); sys.exit(1)
src = src.replace(OLD_CONNECT_END, NEW_CONNECT_END, 1)
print("1a. reconnect() added to DhanFeed.")

# 1b. Fix _nearest_expiry() — holiday-aware, tries up to 4 weeks out
OLD_EXPIRY = (
    "    @staticmethod\n"
    "    def _nearest_expiry() -> str:\n"
    "        \"\"\"Return the nearest Thursday (NSE weekly expiry) as YYYY-MM-DD.\"\"\"\n"
    "        today = date.today()\n"
    "        days_until_thursday = (3 - today.weekday()) % 7   # 0=Mon \u2026 3=Thu\n"
    "        if days_until_thursday == 0 and today.weekday() == 3:\n"
    "            pass   # today IS thursday\n"
    "        next_thu = today + timedelta(days=days_until_thursday)\n"
    "        return next_thu.strftime(\"%Y-%m-%d\")"
)
NEW_EXPIRY = (
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
if OLD_EXPIRY not in src:
    print("ERROR: _nearest_expiry patch anchor not found"); sys.exit(1)
src = src.replace(OLD_EXPIRY, NEW_EXPIRY, 1)
print("1b. _nearest_expiry() fixed (holiday-aware).")

# 1c. Fix get_options_chain to try multiple expiries on 'Invalid Expiry Date'
OLD_OC = (
    "        try:\n"
    "            resp = self._dhan.option_chain(\n"
    "                under_security_id     = int(meta[\"security_id\"]),\n"
    "                under_exchange_segment= \"IDX_I\",\n"
    "                expiry                = expiry,\n"
    "            )\n"
    "            return self._parse_option_chain(symbol, resp, expiry)\n"
    "        except Exception as exc:\n"
    "            log.debug(\"[DhanFeed] get_options_chain(%s) error: %s\", symbol, exc)\n"
    "            return None"
)
NEW_OC = (
    "        # Try the requested expiry; if invalid, walk forward up to 4 candidates\n"
    "        def _try_expiry(exp_str: str):\n"
    "            try:\n"
    "                resp = self._dhan.option_chain(\n"
    "                    under_security_id     = int(meta[\"security_id\"]),\n"
    "                    under_exchange_segment= \"IDX_I\",\n"
    "                    expiry                = exp_str,\n"
    "                )\n"
    "                if not resp:\n"
    "                    return None\n"
    "                # Dhan returns {status: failure, data: {data: {'811': 'Invalid Expiry Date'}}}\n"
    "                inner = (resp.get(\"data\") or {})\n"
    "                inner_data = inner.get(\"data\") or inner\n"
    "                if isinstance(inner_data, dict) and \"811\" in inner_data:\n"
    "                    return \"invalid\"\n"
    "                if resp.get(\"status\") == \"failure\":\n"
    "                    return None\n"
    "                return self._parse_option_chain(symbol, resp, exp_str)\n"
    "            except Exception as exc:\n"
    "                log.debug(\"[DhanFeed] option_chain(%s, %s) error: %s\", symbol, exp_str, exc)\n"
    "                return None\n"
    "\n"
    "        result = _try_expiry(expiry)\n"
    "        if result == \"invalid\" or result is None:\n"
    "            # Try candidate dates around the requested expiry\n"
    "            req_d = date.fromisoformat(expiry)\n"
    "            for delta in [-1, -2, 1, 7, 6, 5, 14, 13]:\n"
    "                alt = (req_d + timedelta(days=delta)).strftime(\"%Y-%m-%d\")\n"
    "                r2 = _try_expiry(alt)\n"
    "                if r2 and r2 != \"invalid\":\n"
    "                    log.info(\"[DhanFeed] Options chain: used expiry %s (requested %s was invalid).\", alt, expiry)\n"
    "                    return r2\n"
    "        return result if result != \"invalid\" else None"
)
if OLD_OC not in src:
    print("ERROR: get_options_chain patch anchor not found"); sys.exit(1)
src = src.replace(OLD_OC, NEW_OC, 1)
print("1c. get_options_chain() retry logic added.")

with open(DHAN, "w") as f:
    f.write(src)
print("dhan_feed.py saved.")

# ── 2. Patch data_feed_manager.py — add reconnect() ──────────────────────────
with open(FM, "r") as f:
    fm_src = f.read()

OLD_FM = (
    "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
    "\n"
    "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
)
NEW_FM = (
    "    # ── Reconnect (after token refresh) ────────────────────────────────────\n"
    "\n"
    "    def reconnect(self) -> None:\n"
    "        \"\"\"Reinitialise the DhanFeed client with the latest DHAN_ACCESS_TOKEN.\n"
    "        Called by the Telegram /token command after updating os.environ.\"\"\"\n"
    "        self.dhan.reconnect()\n"
    "\n"
    "    # ── Quotes ─────────────────────────────────────────────────────────────\n"
    "\n"
    "    def get_quote(self, symbol: str) -> Optional[TickerQuote]:"
)
if OLD_FM not in fm_src:
    print("ERROR: DataFeedManager reconnect patch anchor not found"); sys.exit(1)
fm_src = fm_src.replace(OLD_FM, NEW_FM, 1)
with open(FM, "w") as f:
    f.write(fm_src)
print("2. reconnect() added to DataFeedManager.")

# ── 3. Remove :ro from .env mount in docker-compose.yml ─────────────────────
with open(DC, "r") as f:
    dc_src = f.read()

if "- .env:/app/.env:ro" in dc_src:
    dc_src = dc_src.replace("- .env:/app/.env:ro", "- .env:/app/.env", 1)
    with open(DC, "w") as f:
        f.write(dc_src)
    print("3. docker-compose.yml: removed :ro from .env mount.")
else:
    print("3. SKIP: :ro not found (already removed or different format).")

print("\nAll patches applied. Restart container to load new docker-compose .env mount.")
