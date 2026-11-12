"""Prospective full-universe evidence and bounded, research-only challengers.

Features/membership are frozen at T close, before T+1 is known. Outcomes
and explanatory associations are appended separately; neither store is
read by a trading/risk gate. Existing pool fingerprint statistics stay separate.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from config import is_nse_holiday
from opportunity_engine.mover_discovery_v3 import _rank_pct
from scripts.knowledge_system.selection_characteristic_analyzer_001 import (
    COMBINATIONS, FEATURES, _band_of, _build_band_thresholds,
)

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "universe_selection_learning"
DB_PATH = ROOT / "data" / "market_behavior.db"
IST = timezone(timedelta(hours=5, minutes=30))
VERSION = "universe-v1"
MAX_RESOLVE_DATES = 5
EXPERIMENT_DATES = 30
MIN_TRAINING_DATES = 10
MIN_MATCHES = 15
MAX_RESEARCH_WEIGHT = 0.15
MAX_MISSING_OUTCOME_DAYS = 7
RESEARCH_NOTIONAL = 10_000.0


def _now() -> datetime:
    return datetime.now(IST)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def capture_universe_snapshot(
    conn: sqlite3.Connection, trade_date: str, symbols: list[str],
    scored: list[dict[str, Any]], store: Path | None = None,
) -> dict[str, Any]:
    """Only capture today's completed session; never backdate a PIT claim."""
    now = _now()
    if (trade_date != now.date().isoformat() or now.time() < time(15, 30)
            or is_nse_holiday(now.date())):
        return {"status": "SKIPPED_NOT_PROSPECTIVE"}
    destination = (store or STORE) / "snapshots" / f"{trade_date}.json"
    if destination.exists():
        return {"status": "ALREADY_CAPTURED"}
    exact = {r[0] for r in conn.execute(
        "SELECT symbol FROM ohlcv_daily WHERE trade_date = ?", (trade_date,)
    )}
    by_symbol = {r["symbol"]: r for r in scored}
    rows = []
    for symbol in sorted(set(symbols)):
        features = by_symbol.get(symbol)
        usable = symbol in exact and features is not None and all(
            isinstance(features.get(f), (int, float))
            and math.isfinite(features[f]) for f in FEATURES + ["v3_up_score", "v3_down_score"]
        )
        rows.append({
            "symbol": symbol,
            "exclusion": None if usable else (
                "MISSING_EXACT_DATE_BAR" if symbol not in exact else "FEATURE_QUALITY_GATE"
            ),
            **({k: features.get(k) for k in FEATURES + ["v3_up_score", "v3_down_score"]}
               if usable else {}),
        })
    payload = {
        "version": VERSION, "trade_date": trade_date, "captured_at": now.isoformat(),
        "membership_source": "active_universe_at_capture_not_official_index",
        "membership_hash": hashlib.sha256("\n".join(sorted(set(symbols))).encode()).hexdigest(),
        "eligible_count": len(rows), "feature_count": sum(r["exclusion"] is None for r in rows),
        "rows": rows,
    }
    _write_json(destination, payload)
    return {"status": "CAPTURED", "eligible_count": len(rows),
            "feature_count": payload["feature_count"]}


def _research_rules(
    prior: list[dict[str, Any]], direction: str, epoch_complete: bool = False,
) -> list[dict[str, Any]]:
    """Reuse pre-specified combinations; chronological train/OOS, no shuffle."""
    dates = sorted({r["trade_date"] for r in prior})
    epoch = max(0, (len(dates) - 1) // EXPERIMENT_DATES)
    dates = dates[epoch * EXPERIMENT_DATES:]
    current = [r for r in prior if r["trade_date"] in set(dates)]
    split = max(1, int(len(dates) * 0.7))
    train = [r for r in current if r["trade_date"] in set(dates[:split])]
    oos = [r for r in current if r["trade_date"] in set(dates[split:])]
    thresholds = _build_band_thresholds([{**r, "direction": direction} for r in train], direction)
    results = []
    for combo in COMBINATIONS:
        def matches(row):
            bands = {f: _band_of(f, row[f], direction, thresholds) for f in FEATURES}
            return bool(combo["rule"](bands))

        def effect(records):
            positive = [r for r in records if matches(r)]
            controls = [r for r in records if not matches(r)]
            def rate(group):
                sign = 1 if direction == "UP" else -1
                return sum(sign * r["t1_ret_pct"] >= 2.0 for r in group) / len(group)
            if min(len(positive), len(controls)) < MIN_MATCHES:
                return None
            return rate(positive) - rate(controls)

        train_effect, oos_effect = effect(train), effect(oos)
        net_key = "net_up_ret_pct" if direction == "UP" else "net_down_ret_pct"
        def net_effect(records):
            positive = [r[net_key] for r in records if matches(r) and net_key in r]
            controls = [r[net_key] for r in records if not matches(r) and net_key in r]
            if min(len(positive), len(controls)) < MIN_MATCHES:
                return None
            return sum(positive) / len(positive) - sum(controls) / len(controls)
        oos_net_lift = net_effect(oos)
        valid = (len(dates) >= MIN_TRAINING_DATES and train_effect is not None
                 and oos_effect is not None and min(train_effect, oos_effect) >= 0.02
                 and oos_net_lift is not None and oos_net_lift > 0)
        status = ("VALIDATED_RESEARCH_ONLY" if valid else
                  "INSUFFICIENT_DATA_AT_DEADLINE" if epoch_complete and
                  (train_effect is None or oos_effect is None) else
                  "REJECTED" if epoch_complete or len(dates) >= EXPERIMENT_DATES else "COLLECTING")
        results.append({
            "name": combo["name"], "direction": direction,
            "experiment_id": f"{VERSION}:{direction}:{combo['name']}:{dates[0] if dates else 'pending'}",
            "status": status, "evidence_days": len(dates),
            "deadline_evidence_days": EXPERIMENT_DATES,
            "remaining_evidence_days": 0 if epoch_complete else max(0, EXPERIMENT_DATES - len(dates)),
            "train_lift": train_effect, "oos_lift": oos_effect,
            "oos_net_return_lift_pct": oos_net_lift,
            "weight": min(MAX_RESEARCH_WEIGHT, max(0.0, oos_effect or 0)) if valid else 0.0,
            "thresholds": thresholds,
        })
    return results


def _evaluate_snapshot(snapshot, outcome_rows, prior, epoch_complete=False):
    results = []
    combos = {c["name"]: c for c in COMBINATIONS}
    current = [r for r in outcome_rows if r.get("exclusion") is None]
    for direction, score_key, sign in (("UP", "v3_up_score", 1), ("DOWN", "v3_down_score", -1)):
        rules = _research_rules(prior, direction, epoch_complete)
        base_ranks = _rank_pct([r[score_key] for r in current])
        scored = []
        for row, rank in zip(current, base_ranks):
            nudge = 0.0
            associations = []
            for rule in rules:
                if rule["evidence_days"] == 0:
                    continue
                bands = {f: _band_of(f, row[f], direction, rule["thresholds"]) for f in FEATURES}
                if combos[rule["name"]]["rule"](bands):
                    associations.append(rule["name"])
                    nudge = max(nudge, rule["weight"])
            scored.append({**row, "research_score": rank + nudge, "research_nudge": nudge,
                           "technical_associations": associations})
        baseline = sorted(scored, key=lambda r: (-r[score_key], r["symbol"]))[:20]
        challenger = sorted(scored, key=lambda r: (-r["research_score"], r["symbol"]))[:20]
        # Gap ranking is computed at the opening window, never from that day's close.
        def final_five(pool, adjusted):
            gap_ranks = _rank_pct([sign * r["gap_pct"] for r in pool])
            v3_ranks = _rank_pct([r[score_key] for r in pool])
            ranked = [(gap + (r["research_nudge"] * v3 if adjusted else 0), r)
                      for gap, v3, r in zip(gap_ranks, v3_ranks, pool)]
            return [r for _, r in sorted(ranked, key=lambda p: (-p[0], p[1]["symbol"]))[:5]]
        winners = sorted(outcome_rows, key=lambda r: (-sign * r["t1_ret_pct"], r["symbol"]))[:20]
        top = {r["symbol"] for r in winners}
        def metrics(pool):
            return {"symbols": [r["symbol"] for r in pool], "n": len(pool),
                    "top20_hits": sum(r["symbol"] in top for r in pool),
                    "directional_mean_return_pct": (
                        sum(sign * r["t1_ret_pct"] for r in pool) / len(pool) if pool else None),
                    "estimated_net_mean_return_pct": (
                        sum(r["net_up_ret_pct" if sign == 1 else "net_down_ret_pct"] for r in pool)
                        / len(pool) if pool else None)}
        results.append({
            "direction": direction, "experiments": rules,
            "baseline20": metrics(baseline), "challenger20": metrics(challenger),
            "baseline5": metrics(final_five(baseline, False)),
            "challenger5": metrics(final_five(challenger, True)),
            "reason_cards": [{
                "symbol": r["symbol"], "return_pct": r["t1_ret_pct"],
                "in_baseline20": r["symbol"] in {x["symbol"] for x in baseline},
                "technical_associations": next(
                    (x["technical_associations"] for x in scored if x["symbol"] == r["symbol"]), []
                ),
                "feature_exclusion": r.get("exclusion"),
                "pre_move_features": {f: r.get(f) for f in FEATURES},
                "features_available_at": snapshot["captured_at"],
                "verified_event_cause": None, "cause_status": "UNKNOWN_NOT_VERIFIED",
                "explanation_type": "TECHNICAL_ASSOCIATION_NOT_CAUSATION",
            } for r in winners],
        })
    return results


def run_universe_learning(
    db_path: Path | None = None, store: Path | None = None,
    max_dates: int = MAX_RESOLVE_DATES,
) -> dict[str, Any]:
    """Resolve a bounded backlog without network calls or trading side effects."""
    directory = store or STORE
    summary: dict[str, Any] = {
        "resolved_dates": 0, "examined_dates": 0, "status": "OK", "research_only": True,
    }
    try:
        from models.transaction_costs import InstrumentType, TransactionCostModel
        costs = TransactionCostModel()
        now = _now()
        snapshots = sorted((directory / "snapshots").glob("*.json"))
        with sqlite3.connect(f"{(db_path or DB_PATH).resolve().as_uri()}?mode=ro", uri=True) as conn:
            for file in snapshots:
                snapshot = json.loads(file.read_text(encoding="utf-8"))
                td = snapshot["trade_date"]
                destination = directory / "resolved" / file.name
                if destination.exists():
                    continue
                if summary["examined_dates"] >= max(0, max_dates):
                    break
                summary["examined_dates"] += 1
                later_dates = conn.execute(
                    "SELECT DISTINCT trade_date FROM ohlcv_daily "
                    "WHERE trade_date > ? AND symbol NOT LIKE '^%' "
                    "ORDER BY trade_date LIMIT 10", (td,)
                ).fetchall()
                next_date = next((r[0] for r in later_dates
                                  if not is_nse_holiday(date.fromisoformat(r[0]))), None)
                if not next_date or next_date > now.date().isoformat() or (
                    next_date == now.date().isoformat() and now.time() < time(15, 30)
                ):
                    continue
                prices = {r[0]: r[1:] for r in conn.execute(
                    "SELECT symbol, open, close FROM ohlcv_daily WHERE trade_date = ?", (next_date,)
                )}
                previous = dict(conn.execute(
                    "SELECT symbol, close FROM ohlcv_daily WHERE trade_date = ?", (td,)
                ))
                rows = []
                missing = []
                for row in snapshot["rows"]:
                    bar, close = prices.get(row["symbol"]), previous.get(row["symbol"])
                    if (not bar or not close or close <= 0 or any(
                        not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0
                        for v in bar
                    )):
                        missing.append(row["symbol"])
                        continue
                    gross = (bar[1] / bar[0] - 1) * 100
                    qty = max(1, int(RESEARCH_NOTIONAL / bar[0]))
                    long_cost = costs.compute(
                        row["symbol"], qty, bar[0], bar[1], InstrumentType.EQUITY_DELIVERY
                    ).total_cost
                    short_cost = costs.compute(
                        row["symbol"], qty, bar[1], bar[0], InstrumentType.EQUITY_INTRADAY
                    ).total_cost
                    rows.append({**row, "trade_date": td, "outcome_date": next_date,
                                 "t1_ret_pct": gross, "gap_pct": (bar[0] / close - 1) * 100,
                                 "net_up_ret_pct": gross - long_cost / (bar[0] * qty) * 100,
                                 "net_down_ret_pct": -gross - short_cost / (bar[0] * qty) * 100,
                                 "simulated_quantity": qty})
                # Incomplete cohorts are retried; never freeze a biased partial leaderboard.
                if missing:
                    summary.setdefault("missing_outcomes", {})[td] = missing
                    if (now.date() - date.fromisoformat(next_date)).days < MAX_MISSING_OUTCOME_DAYS:
                        summary["status"] = "WAITING_FOR_PRICES"
                        continue
                    _write_json(destination, {
                        "version": VERSION, "trade_date": td, "outcome_date": next_date,
                        "cohort_complete": False, "status": "DATA_INCOMPLETE",
                        "missing_outcomes": missing, "rows": [], "comparisons": [],
                        "research_only": True, "generated_at": now.isoformat(),
                    })
                    summary["resolved_dates"] += 1
                    continue
                history_files = sorted(
                    f for f in (directory / "resolved").glob("*.json") if f.stem < td
                )
                epoch = max(0, (len(history_files) - 1) // EXPERIMENT_DATES)
                epoch_files = history_files[epoch * EXPERIMENT_DATES:]
                training = []
                for history_file in epoch_files:
                    history = json.loads(history_file.read_text(encoding="utf-8"))
                    if history.get("cohort_complete", True):
                        training.extend(r for r in history["rows"] if
                                        r.get("exclusion") is None and r["outcome_date"] <= td)
                report = {
                    "version": VERSION, "trade_date": td, "outcome_date": next_date,
                    "cohort_complete": True,
                    "captured_at": snapshot["captured_at"], "rows": rows,
                    "eligible_count": snapshot["eligible_count"], "evaluated_count": len(rows),
                    "feature_count": snapshot["feature_count"],
                    "excluded": [r for r in snapshot["rows"] if r["exclusion"]],
                    "comparisons": _evaluate_snapshot(
                        snapshot, rows, training, len(epoch_files) >= EXPERIMENT_DATES
                    ),
                    "research_only": True, "costs_included": True,
                    "cost_assumption": {
                        "reference_notional": RESEARCH_NOTIONAL,
                        "model": "TransactionCostModel_default_slippage",
                        "up_product": "EQUITY_DELIVERY", "down_product": "EQUITY_INTRADAY",
                        "not_actual_fills": True,
                    },
                    "generated_at": now.isoformat(),
                }
                _write_json(destination, report)
                summary["resolved_dates"] += 1
        summary["pending_dates"] = sum(
            not (directory / "resolved" / f.name).exists() for f in snapshots
        )
        _write_json(directory / "health.json", {**summary, "checked_at": now.isoformat()})
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        log.warning("[UniverseLearning] Evidence processing failed: %s", exc, exc_info=True)
        summary.update(status="ERROR", error=str(exc))
    return summary


def get_learning_status(store: Path | None = None) -> dict[str, Any]:
    """Read-only health surface; counts evidence, never claims profit improvement."""
    directory = store or STORE
    try:
        snapshots = sorted((directory / "snapshots").glob("*.json"))
        resolved = sorted((directory / "resolved").glob("*.json"))
        health_file = directory / "health.json"
        health = json.loads(health_file.read_text(encoding="utf-8")) if health_file.exists() else {}
        latest = json.loads(resolved[-1].read_text(encoding="utf-8")) if resolved else {}
        snapshot = json.loads(snapshots[-1].read_text(encoding="utf-8")) if snapshots else {}
        reviews_file = directory / "fingerprint_reviews.json"
        reviews = json.loads(reviews_file.read_text(encoding="utf-8")) if reviews_file.exists() else []
        return {
            **health, "status": health.get("status", "COLLECTING"),
            "snapshot_dates": len(snapshots), "outcome_dates": len(resolved),
            "latest_capture": snapshot.get("captured_at"),
            "latest_outcome": latest.get("outcome_date"),
            "eligible_count": snapshot.get("eligible_count", 0),
            "feature_count": snapshot.get("feature_count", 0),
            "experiments": [e for c in latest.get("comparisons", []) for e in c["experiments"]],
            "consumer": "same_size_universe_research_challenger_not_live_orders",
            "fingerprint_reviews": reviews,
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("[UniverseLearning] Status read failed: %s", exc)
        return {"status": "ERROR", "error": str(exc), "snapshot_dates": 0, "outcome_dates": 0}
