"""
learning_system/cle_fingerprint_evidence_log.py — ACQUISITION.

DTA-RESEARCH-QUALITY-001: append-only evidence log recording which
combination fingerprint (cle_research.py's _select_best_fingerprint) was
used to create each CLE-001 DNA candidate. This is the raw material the
refinement engine (cle_fingerprint_refinement_engine.py) validates over
time against each candidate's real, later IDR lifecycle outcome.

Never touches live trading; purely observational bookkeeping.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import List, Optional

log = logging.getLogger(__name__)

_STORE_DIR  = os.path.join("data", "learning_system")
_STORE_PATH = os.path.join(_STORE_DIR, "cle_fingerprint_evidence.jsonl")
_LOCK = threading.Lock()


def record_fingerprint_used(
    dna_id: str,
    symbol: str,
    direction: str,
    fingerprint_name: str,
    created_date: str,
) -> None:
    """Append one record. Never raises -- fails open on any I/O error."""
    try:
        os.makedirs(_STORE_DIR, exist_ok=True)
        row = {
            "dna_id": dna_id,
            "symbol": symbol,
            "direction": direction,
            "fingerprint_name": fingerprint_name,
            "created_date": created_date,
        }
        with _LOCK:
            with open(_STORE_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
    except Exception as exc:
        log.debug("[CLEFingerprintEvidence] record failed: %s", exc)


def get_records(n: Optional[int] = None) -> List[dict]:
    """Return records oldest-first. Never raises -- returns [] on failure."""
    try:
        if not os.path.exists(_STORE_PATH):
            return []
        rows: List[dict] = []
        with open(_STORE_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-n:] if n else rows
    except Exception as exc:
        log.debug("[CLEFingerprintEvidence] read failed: %s", exc)
        return []
