"""
knowledge_authority/kda_ledger.py
===================================
KDA-002 — Append-only KDA decision ledger.

Writes KDADecisionRecord JSON lines to:
  data/klp/kda/kda_decisions_YYYY-MM-DD.jsonl

Guarantees:
  - Duplicate decision_id is rejected (returns False)
  - Atomic line-level append (whole JSON line or nothing)
  - Corrupt lines skipped on read (never crash)
  - Directory created on first write

Safety contract:
  broker_calls = 0, orders = 0, no_lookahead = True, PAPER_TRADING unchanged
"""
from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from .kda_models import KDADecisionRecord


_LEDGER_DIR = Path("data/klp/kda")


class KDALedger:
    """
    Thread-safe, append-only ledger for KDA shadow decisions.
    One JSONL file per calendar date.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else _LEDGER_DIR
        self._lock = threading.Lock()
        self._seen_ids: Set[str] = set()
        self._seen_ids_loaded = False

    # ── public ───────────────────────────────────────────────────────────────

    def record(self, kda_record: KDADecisionRecord) -> bool:
        """
        Append one KDA decision to the daily ledger file.
        Returns True on success, False if decision_id is a duplicate.
        Never raises.
        """
        with self._lock:
            self._ensure_ids_loaded()
            if kda_record.decision_id in self._seen_ids:
                return False
            try:
                self._base_dir.mkdir(parents=True, exist_ok=True)
                path = self._daily_path()
                line = json.dumps(kda_record.as_dict(), default=str) + "\n"
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                self._seen_ids.add(kda_record.decision_id)
                return True
            except Exception:
                return False

    def load_decisions(self, trading_date: Optional[str] = None) -> List[Dict]:
        """Load all decisions for a given date (ISO 'YYYY-MM-DD'). Returns [] on missing file."""
        if trading_date is None:
            trading_date = date.today().isoformat()
        path = self._base_dir / f"kda_decisions_{trading_date}.jsonl"
        return self._read_jsonl(path)

    def load_all_decisions(self) -> List[Dict]:
        """Load all decisions across all date files in the ledger directory."""
        if not self._base_dir.exists():
            return []
        records: List[Dict] = []
        for p in sorted(self._base_dir.glob("kda_decisions_*.jsonl")):
            records.extend(self._read_jsonl(p))
        return records

    def is_duplicate(self, decision_id: str) -> bool:
        with self._lock:
            self._ensure_ids_loaded()
            return decision_id in self._seen_ids

    # ── internal ─────────────────────────────────────────────────────────────

    def _daily_path(self, trading_date: Optional[str] = None) -> Path:
        d = trading_date or date.today().isoformat()
        return self._base_dir / f"kda_decisions_{d}.jsonl"

    def _ensure_ids_loaded(self) -> None:
        """Populate _seen_ids from disk on first call (warm-up)."""
        if self._seen_ids_loaded:
            return
        for record in self.load_all_decisions():
            did = record.get("decision_id")
            if did:
                self._seen_ids.add(did)
        self._seen_ids_loaded = True

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict]:
        if not path.exists():
            return []
        records: List[Dict] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass  # skip corrupt line
        except OSError:
            pass
        return records
