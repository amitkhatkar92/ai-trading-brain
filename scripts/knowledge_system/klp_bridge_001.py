"""
scripts/knowledge_system/klp_bridge_001.py
===========================================
KLP Data Bridge  —  VPS → Local transfer  (KLP-001)

Copies KLP observation files (KNOWLEDGE_OBSERVATION + STRATEGY_ANNOTATION
records) from the live VPS to the local knowledge pipeline.  The bridge is
one-way and append-only, using a byte-offset watermark to avoid duplicating
already-transferred records.

OUTPUT
------
  data/klp/*.jsonl              — merged KLP records (local)
  data/klp_bridge/state.json   — watermark {date: {bytes_transferred, ...}}

USAGE
-----
  from scripts.knowledge_system.klp_bridge_001 import KLPBridge
  bridge = KLPBridge()
  result = bridge.transfer_today()
  # {"records_transferred": N, "date": "YYYY-MM-DD", "error": None}

  # Transfer a specific date:
  result = bridge.transfer("2026-08-20")

  # Inspect watermark:
  state = bridge.get_bridge_state()

CONTRACT
--------
• Never raises — all public methods swallow every exception.
• Append-only: never overwrites or truncates local files.
• Idempotent: re-running the same date never duplicates records.
• Validates no_lookahead assertion; rejects records missing it.
• Requires SSH key auth: ~/.ssh/trading_vps → root@178.18.252.24
• Designed to run locally; gracefully returns error on VPS (scp not needed).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]

# ── Defaults ──────────────────────────────────────────────────────────────────
_VPS_HOST       = "root@178.18.252.24"
_VPS_KLP_PATH   = "/root/ai-trading-brain/data/klp"
_SSH_KEY        = Path.home() / ".ssh" / "trading_vps"
_LOCAL_KLP_DIR  = ROOT / "data" / "klp"
_STATE_PATH     = ROOT / "data" / "klp_bridge" / "state.json"

# ── Timeout for scp ───────────────────────────────────────────────────────────
_SCP_TIMEOUT_SEC = 30


class KLPBridge:
    """
    Transfers KLP JSONL files from VPS to the local knowledge pipeline.

    The bridge is designed to be called once per day (e.g., from the EOD
    learning loop) or on demand from the CLI.

    For unit tests, inject a ``_download_fn`` callable to replace the scp
    subprocess call:
        bridge = KLPBridge(_download_fn=my_mock_downloader)

    The _download_fn signature:
        def fn(remote: str, local: Path) -> Optional[str]:
            # Returns None on success, or an error string on failure.
    """

    def __init__(
        self,
        vps_host: str = _VPS_HOST,
        vps_klp_path: str = _VPS_KLP_PATH,
        ssh_key: Optional[Path] = None,
        local_klp_dir: Optional[Path] = None,
        state_path: Optional[Path] = None,
        _download_fn: Optional[Callable] = None,
    ) -> None:
        self._vps_host      = vps_host
        self._vps_klp_path  = vps_klp_path
        self._ssh_key       = ssh_key or _SSH_KEY
        self._local_klp_dir = Path(local_klp_dir) if local_klp_dir else _LOCAL_KLP_DIR
        self._state_path    = Path(state_path) if state_path else _STATE_PATH
        self._download_fn   = _download_fn or self._scp_download

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def transfer_today(self) -> Dict[str, Any]:
        """Transfer KLP records for today from the VPS.  Never raises."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.transfer(date_str)

    def transfer(self, date_str: str) -> Dict[str, Any]:
        """
        Transfer KLP records for a specific date from the VPS.  Never raises.

        Returns
        -------
        dict with keys:
          records_transferred : int   — new records appended locally
          date                : str   — YYYY-MM-DD
          error               : str|None
        """
        try:
            return self._transfer_impl(date_str)
        except Exception as exc:
            return {"records_transferred": 0, "date": date_str, "error": str(exc)}

    def get_bridge_state(self) -> Dict[str, Any]:
        """Return the current watermark state dict.  Never raises."""
        try:
            if self._state_path.exists():
                return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Transfer implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _transfer_impl(self, date_str: str) -> Dict[str, Any]:
        remote_file = f"{self._vps_klp_path}/KLP_{date_str}.jsonl"
        local_file  = self._local_klp_dir / f"KLP_{date_str}.jsonl"

        # Load byte-offset watermark for this date
        state                = self.get_bridge_state()
        already_transferred  = int(state.get(date_str, {}).get("bytes_transferred", 0))

        # Download remote file to a temp location
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            err = self._download_fn(remote_file, tmp_path)
            if err is not None:
                return {"records_transferred": 0, "date": date_str, "error": err}

            raw = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

        # Only process bytes after the watermark
        new_bytes = raw[already_transferred:]
        if not new_bytes:
            return {"records_transferred": 0, "date": date_str, "error": None}

        # Parse, validate, and collect new records
        new_records = _parse_and_validate(new_bytes)

        if not new_records:
            return {"records_transferred": 0, "date": date_str, "error": None}

        # Append to local KLP file (append-only)
        self._local_klp_dir.mkdir(parents=True, exist_ok=True)
        with local_file.open("a", encoding="utf-8") as fh:
            for rec in new_records:
                fh.write(json.dumps(rec, ensure_ascii=False))
                fh.write("\n")

        # Update watermark
        date_state = state.get(date_str, {})
        prev_rec   = int(date_state.get("records_transferred", 0))
        state[date_str] = {
            "bytes_transferred":    already_transferred + len(new_bytes),
            "records_transferred":  prev_rec + len(new_records),
            "last_transfer_ts":     datetime.now(timezone.utc).isoformat(),
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        return {"records_transferred": len(new_records), "date": date_str, "error": None}

    # ─────────────────────────────────────────────────────────────────────────
    # Default downloader (scp subprocess)
    # ─────────────────────────────────────────────────────────────────────────

    def _scp_download(self, remote: str, local: Path) -> Optional[str]:
        """
        Download remote file via scp.
        Returns None on success, or an error string on failure.
        """
        scp_cmd = [
            "scp",
            "-i", str(self._ssh_key),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"{self._vps_host}:{remote}",
            str(local),
        ]
        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                timeout=_SCP_TIMEOUT_SEC,
            )
            if result.returncode != 0:
                return f"scp_failed: {result.stderr.decode(errors='replace')[:200]}"
            return None
        except subprocess.TimeoutExpired:
            return "scp_timeout"
        except FileNotFoundError:
            return "scp_binary_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_and_validate(raw: bytes) -> List[Dict[str, Any]]:
    """
    Parse new_bytes as JSONL, validate each record, and return valid records.

    Validation rules:
      1. Must be a JSON object (dict)
      2. Must have no_lookahead == True
      3. Must have event_type in ALLOWED_EVENT_TYPES
      4. Must have a non-empty obs_id
    """
    ALLOWED_EVENT_TYPES = {"KNOWLEDGE_OBSERVATION", "STRATEGY_ANNOTATION", "OUTCOME_UPDATE"}
    records: List[Dict[str, Any]] = []

    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue   # malformed JSON — skip
        if not isinstance(rec, dict):
            continue
        if rec.get("no_lookahead") is not True:
            continue   # safety gate: must assert no look-ahead
        if rec.get("event_type") not in ALLOWED_EVENT_TYPES:
            continue   # unknown event type — skip
        if not rec.get("obs_id"):
            continue   # record without obs_id cannot be linked
        records.append(rec)

    return records
