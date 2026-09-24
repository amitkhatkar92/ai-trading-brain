"""
learning_system/corporate_event_evidence_log.py
===================================================
Self-learning module #32 (ACQUISITION) -- Event Intelligence evidence
log.

Records, for every closed trade where a real corporate_event_score was
available at signal time, the (score, outcome) pair. Called once per
trade from OrderManager.close_position(), only when
`rec.corporate_event_score is not None`.

Zero effect on any live decision. Read-only accessors are consumed by
corporate_event_refinement_engine.py for the evidence-gated,
shadow-then-live cohort validation.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "learning_system",
)
_EVIDENCE_FILE = os.path.join(_DATA_DIR, "corporate_event_evidence.jsonl")


def record_corporate_event_outcome(
    order_id: str,
    symbol: str,
    strategy: str,
    corporate_event_score: float,
    r_multiple: float,
    won: bool,
) -> None:
    """Append one resolved (score, outcome) record. Fail-open."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        record = {
            "timestamp":              datetime.now().isoformat(),
            "order_id":               order_id,
            "symbol":                 symbol,
            "strategy":               strategy,
            "corporate_event_score":  round(float(corporate_event_score), 4),
            "r_multiple":             round(float(r_multiple), 4),
            "won":                    bool(won),
        }
        with open(_EVIDENCE_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as exc:
        log.debug("[CorporateEventEvidence] record failed (non-critical): %s", exc)


def get_records(n: Optional[int] = None) -> List[Dict]:
    """Return all (or last n) resolved records, oldest-first. Fail-open."""
    if not os.path.exists(_EVIDENCE_FILE):
        return []
    records: List[Dict] = []
    try:
        with open(_EVIDENCE_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        log.debug("[CorporateEventEvidence] read failed (non-critical): %s", exc)
        return []
    if n is not None:
        records = records[-n:]
    return records
