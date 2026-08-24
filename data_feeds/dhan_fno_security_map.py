"""
Dhan F&O Security Map
======================
Resolves NSE F&O options contracts to Dhan security IDs.
Used by OptionsOrderManager for live order routing.

Lookup key: (underlying, expiry_date "YYYY-MM-DD", strike (int), option_type "CE"/"PE")
Returns:     Dhan security_id string  (e.g. "35000")

Source: Dhan instrument master CSV — attempted daily refresh via dhanhq SDK,
        falls back to local security_id_list.csv in the workspace root.

No security IDs are hard-coded here.  All IDs come from the instrument master.

Singleton access: get_fno_security_map()
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import date
from typing import Dict, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── Local paths ────────────────────────────────────────────────────────────
_WORKSPACE_CSV  = "security_id_list.csv"          # repo-root fallback
_CACHE_DIR      = "data"
_CACHE_PREFIX   = "dhan_fno_master_"              # daily cache: data/dhan_fno_master_YYYY-MM-DD.csv

# ── NSE options exchange segment for broker order calls ────────────────────
NSE_FNO_SEGMENT = "NSE_FNO"

# Index key tuple type
_IndexKey = Tuple[str, str, int, str]  # (underlying, expiry_YYYY-MM-DD, strike_int, CE/PE)


class DhanFnOSecurityMap:
    """
    In-process cache of NSE F&O contract → Dhan security_id mappings.

    Thread-safe.  Attempts a daily refresh (once per calendar day).
    If the SDK download fails, falls back to the repo-root CSV.
    """

    def __init__(self) -> None:
        self._index:       Dict[_IndexKey, str] = {}
        self._loaded_date: Optional[date]        = None
        self._lock         = threading.Lock()
        self._load()

    # ── Public API ─────────────────────────────────────────────────────

    def lookup(
        self,
        underlying:      str,
        expiry_date_str: str,   # "YYYY-MM-DD"
        strike:          float,
        option_type:     str,   # "CE" | "PE"
    ) -> Optional[str]:
        """
        Return Dhan security_id for the given NSE options contract.

        Parameters
        ----------
        underlying      : "NIFTY" | "BANKNIFTY" (case-insensitive)
        expiry_date_str : ISO date string "YYYY-MM-DD"
        strike          : strike price as float (e.g. 24500.0)
        option_type     : "CE" or "PE" (case-insensitive)

        Returns
        -------
        security_id string, or None if the contract is not found.
        A None result causes safe rejection — no order is placed.
        """
        with self._lock:
            if self._loaded_date != date.today():
                self._load()

        key: _IndexKey = (
            underlying.upper(),
            expiry_date_str,
            int(round(float(strike))),
            option_type.upper(),
        )
        return self._index.get(key)

    def index_size(self) -> int:
        """Return number of indexed contracts (for diagnostics)."""
        return len(self._index)

    # ── Internal ───────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load (or refresh) the instrument master index — called under self._lock."""
        today_str  = date.today().isoformat()
        cache_path = os.path.join(_CACHE_DIR, f"{_CACHE_PREFIX}{today_str}.csv")

        # 1. Use today's cached download if it already exists
        if os.path.exists(cache_path):
            rows = self._read_csv(cache_path)
            if rows:
                self._build_index(rows)
                self._loaded_date = date.today()
                log.info(
                    "[DhanFnOSecurityMap] Loaded %d F&O contracts from daily cache %s.",
                    len(self._index), cache_path,
                )
                return

        # 2. Attempt fresh download via dhanhq SDK
        if self._download_to(cache_path):
            rows = self._read_csv(cache_path)
            if rows:
                self._build_index(rows)
                self._loaded_date = date.today()
                log.info(
                    "[DhanFnOSecurityMap] Downloaded fresh instrument master: %d F&O contracts.",
                    len(self._index),
                )
                return

        # 3. Fall back to workspace-root CSV (may be stale for near-term weekly options)
        if os.path.exists(_WORKSPACE_CSV):
            rows = self._read_csv(_WORKSPACE_CSV)
            if rows:
                self._build_index(rows)
                self._loaded_date = date.today()
                log.warning(
                    "[DhanFnOSecurityMap] Using local %s — may be stale. "
                    "Indexed %d F&O contracts. Near-term weekly contracts may be missing; "
                    "lookup will return None for those and live execution will be blocked.",
                    _WORKSPACE_CSV, len(self._index),
                )
                return

        log.error(
            "[DhanFnOSecurityMap] No instrument master available. "
            "All security_id lookups will return None — live options execution blocked."
        )

    def _read_csv(self, path: str) -> list:
        """Read CSV rows; return empty list on failure."""
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as fh:
                return list(csv.DictReader(fh))
        except Exception as exc:
            log.warning("[DhanFnOSecurityMap] CSV read failed (%s): %s", path, exc)
            return []

    def _build_index(self, rows: list) -> None:
        """
        Build lookup index from instrument master rows.

        Only NSE options (OPTIDX for index, OPTSTK for stock) are indexed.
        SM_SYMBOL_NAME is EMPTY for OPTIDX rows; the underlying name is
        parsed from SEM_TRADING_SYMBOL prefix:
            "BANKNIFTY-Sep2026-49000-CE" → underlying = "BANKNIFTY"
        """
        idx: Dict[_IndexKey, str] = {}
        skipped = 0
        for row in rows:
            exch     = (row.get("SEM_EXM_EXCH_ID") or "").strip()
            iname    = (row.get("SEM_INSTRUMENT_NAME") or "").strip()
            opt_type = (row.get("SEM_OPTION_TYPE") or "").strip().upper()

            if exch != "NSE":
                continue
            if iname not in ("OPTIDX", "OPTSTK"):
                continue
            if opt_type not in ("CE", "PE"):
                continue

            sid     = (row.get("SEM_SMST_SECURITY_ID") or "").strip()
            trading = (row.get("SEM_TRADING_SYMBOL") or "").strip()
            expiry  = (row.get("SEM_EXPIRY_DATE") or "").strip()
            strike  = (row.get("SEM_STRIKE_PRICE") or "").strip()

            if not (sid and trading and expiry and strike):
                skipped += 1
                continue

            # Underlying from SEM_TRADING_SYMBOL prefix  (SM_SYMBOL_NAME is empty for OPTIDX)
            # Format: "BANKNIFTY-Sep2026-74300-CE"  →  "BANKNIFTY"
            underlying = trading.split("-")[0].upper()
            if not underlying:
                skipped += 1
                continue

            expiry_date = expiry[:10]   # "2026-09-24 14:30:00" → "2026-09-24"

            try:
                strike_int = int(round(float(strike)))
            except (ValueError, TypeError):
                skipped += 1
                continue

            key: _IndexKey = (underlying, expiry_date, strike_int, opt_type)
            idx[key] = sid

        self._index = idx
        if skipped:
            log.debug("[DhanFnOSecurityMap] Skipped %d malformed rows during index build.", skipped)

    def _download_to(self, dest_path: str) -> bool:
        """
        Attempt to download a fresh instrument master from Dhan via the SDK.
        Returns True on success (dest_path written), False on any failure.
        """
        try:
            from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN
            client_id    = str(DHAN_CLIENT_ID or "").strip()
            access_token = str(DHAN_ACCESS_TOKEN or "").strip()
            if not client_id or not access_token:
                log.debug("[DhanFnOSecurityMap] Credentials not set — skipping fresh download.")
                return False

            os.makedirs(_CACHE_DIR, exist_ok=True)

            from dhanhq import dhanhq as _DhanHQ
            try:
                from dhanhq import DhanContext
                ctx  = DhanContext(client_id, access_token)
                dhan = _DhanHQ(ctx)
            except ImportError:
                dhan = _DhanHQ(client_id, access_token)

            result = dhan.fetch_security_list("compact")
            rows   = list(result) if result else []
            if not rows:
                log.warning("[DhanFnOSecurityMap] fetch_security_list returned no data.")
                return False

            fieldnames = list(rows[0].keys())
            with open(dest_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            log.info("[DhanFnOSecurityMap] Saved fresh instrument master: %d rows → %s.",
                     len(rows), dest_path)
            return True

        except Exception as exc:
            log.warning("[DhanFnOSecurityMap] Download failed: %s", exc)
            # Remove partial download to avoid leaving a corrupt cache
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass
            return False


# ── Module-level singleton ─────────────────────────────────────────────────

_MAP_INSTANCE: Optional[DhanFnOSecurityMap] = None
_MAP_LOCK = threading.Lock()


def get_fno_security_map() -> DhanFnOSecurityMap:
    """Return the process-wide DhanFnOSecurityMap singleton."""
    global _MAP_INSTANCE
    with _MAP_LOCK:
        if _MAP_INSTANCE is None:
            _MAP_INSTANCE = DhanFnOSecurityMap()
    return _MAP_INSTANCE
