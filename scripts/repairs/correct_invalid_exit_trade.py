"""Remove one invalid trade outcome from the learning aggregates.

Use when a recorded trade is known to be wrong (for example an exit booked at a
price the market never traded) and has already been folded into the aggregates
that cannot be recomputed from the order journal. The raw journal and analytics
records are left untouched as the historical record.

Dry run by default. Run with the application stopped, because the performance
tracker keeps its state in memory and would overwrite an edit made underneath
it. Every changed file is backed up first, writes are atomic, the correction is
idempotent per order id, and each applied correction is appended to
``data/learning_system/trade_corrections.jsonl``.

    python scripts/repairs/correct_invalid_exit_trade.py --data-dir data \
        --order-id 221261001665703 --strategy KDA_AUTHORITY \
        --r-multiple -5.9198216457235615 --reason "exit booked at 819.05" [--apply]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

TOLERANCE = 1e-9
INVARIANT_TOLERANCE = 1e-6
PERFORMANCE_FILE = "strategy_performance.json"
SIZING_FILE = os.path.join("risk_control", "sizing_calibration", "evidence.jsonl")
AUDIT_FILE = os.path.join("learning_system", "trade_corrections.jsonl")


class CorrectionError(Exception):
    """The data does not match what the correction expects; nothing is written."""


def _same(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) < TOLERANCE


def _check_invariants(entry: Dict[str, Any], label: str) -> None:
    if entry["wins"] + entry["losses"] != entry["total_trades"]:
        raise CorrectionError(f"{label}: wins + losses != total_trades")
    if abs(entry["total_r"] - (entry["win_r"] - entry["loss_r"])) > INVARIANT_TOLERANCE:
        raise CorrectionError(f"{label}: total_r != win_r - loss_r")


def correct_strategy_performance(
    performance: Dict[str, Any], strategy: str, r_multiple: float,
) -> Dict[str, Any]:
    """Return a corrected copy with one trade of ``r_multiple`` removed.

    Only a losing trade can be removed here; the recorded invalid trade is a
    loss, and removing a win would need the symmetric bookkeeping.
    """
    if strategy not in performance:
        raise CorrectionError(f"strategy {strategy!r} not found")
    if r_multiple >= 0:
        raise CorrectionError("only a losing trade (negative R) can be removed")
    corrected = copy.deepcopy(performance)
    entry = corrected[strategy]
    _check_invariants(entry, "before")
    matches = [i for i, value in enumerate(entry["last_trades"]) if _same(value, r_multiple)]
    if not matches:
        raise CorrectionError("R multiple not found in the strategy's recent trades")
    if entry["losses"] < 1 or entry["total_trades"] < 1:
        raise CorrectionError("no losing trade to remove")
    del entry["last_trades"][matches[0]]
    entry["total_trades"] -= 1
    entry["losses"] -= 1
    entry["total_r"] += abs(r_multiple)
    entry["loss_r"] -= abs(r_multiple)
    for key in ("official_trades", "prepared_universe_trades"):
        if key in entry and entry[key] > 0:
            entry[key] -= 1
    _check_invariants(entry, "after")
    return corrected


def filter_sizing_evidence(
    lines: List[str], strategy: str, r_multiple: float,
) -> Tuple[List[str], int]:
    """Drop the single evidence record for this trade; refuse unless exactly one matches."""
    kept: List[str] = []
    removed = 0
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            record = json.loads(text)
        except ValueError:
            kept.append(text)
            continue
        if record.get("strategy") == strategy and _same(record.get("r_multiple", 1e9), r_multiple):
            removed += 1
        else:
            kept.append(text)
    if removed != 1:
        raise CorrectionError(f"expected exactly one sizing evidence record, found {removed}")
    return kept, removed


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _atomic_write(path: str, content: str) -> None:
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(temp, path)


def _already_applied(data_dir: str, order_id: str) -> bool:
    path = os.path.join(data_dir, AUDIT_FILE)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                if json.loads(line).get("order_id") == order_id:
                    return True
            except ValueError:
                continue
    return False


def run(data_dir: str, order_id: str, strategy: str, r_multiple: float,
        reason: str, apply: bool) -> Dict[str, Any]:
    if _already_applied(data_dir, order_id):
        return {"status": "ALREADY_APPLIED", "order_id": order_id}

    performance_path = os.path.join(data_dir, PERFORMANCE_FILE)
    sizing_path = os.path.join(data_dir, SIZING_FILE)
    original = _read_json(performance_path)
    corrected = correct_strategy_performance(original, strategy, r_multiple)
    sizing_lines: Optional[List[str]] = None
    sizing_kept: List[str] = []
    if os.path.exists(sizing_path):
        with open(sizing_path, "r", encoding="utf-8") as handle:
            sizing_lines = handle.read().splitlines()
        sizing_kept, _ = filter_sizing_evidence(sizing_lines, strategy, r_multiple)

    before, after = original[strategy], corrected[strategy]
    summary: Dict[str, Any] = {
        "status": "APPLIED" if apply else "DRY_RUN",
        "order_id": order_id, "strategy": strategy, "r_multiple": r_multiple,
        "total_trades": [before["total_trades"], after["total_trades"]],
        "losses": [before["losses"], after["losses"]],
        "total_r": [round(before["total_r"], 6), round(after["total_r"], 6)],
        "sizing_records": [len(sizing_lines or []), len(sizing_kept)],
    }
    if not apply:
        return summary

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backups = []
    for path in (performance_path, sizing_path):
        if os.path.exists(path):
            backup = f"{path}.pre_correction_{stamp}"
            with open(path, "rb") as source, open(backup, "wb") as target:
                target.write(source.read())
            backups.append(backup)
    _atomic_write(performance_path, json.dumps(corrected, indent=2))
    if sizing_lines is not None:
        _atomic_write(sizing_path, "\n".join(sizing_kept) + "\n")
    audit_path = os.path.join(data_dir, AUDIT_FILE)
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            **summary, "reason": reason, "backups": backups,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }) + "\n")
    summary["backups"] = backups
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--r-multiple", type=float, required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.data_dir, args.order_id, args.strategy,
                     args.r_multiple, args.reason, args.apply)
    except CorrectionError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
