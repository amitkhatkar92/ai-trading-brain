"""Isolated stock/option comparisons and rejected-structure virtual P/L.

No outcomes from this module are consumed by trading or knowledge promotion.
Quotes are executable-side snapshots, not fills. Missing prices stay unpriced.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from utils import get_logger

log = get_logger(__name__)
STATE_PATH = Path("data/option_research/observations.json")
MAX_QUOTE_AGE_SECONDS = 300
MAX_EVENT_DELAY_SECONDS = 60
REFRESH_SECONDS = 300
MAX_REFRESH_ITEMS = 20


def _now() -> datetime:
    return datetime.now().astimezone()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone()


def _positive(value: object) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("non-positive or non-finite price/quantity")
    return number


def _quote(bid: float, ask: float) -> tuple[float, float]:
    bid, ask = _positive(bid), _positive(ask)
    if ask < bid:
        raise ValueError("crossed option quote")
    return bid, ask


def _quantity(value: object) -> int:
    number = _positive(value)
    if not number.is_integer():
        raise ValueError("fractional contract quantity")
    return int(number)


def _fresh(timestamp: str, event_at: str) -> None:
    age = (_now() - _time(timestamp)).total_seconds()
    event_age = (_now() - _time(event_at)).total_seconds()
    if not -5 <= age <= MAX_QUOTE_AGE_SECONDS:
        raise ValueError("stale or future option quote")
    if not -5 <= event_age <= MAX_EVENT_DELAY_SECONDS:
        raise ValueError("event quote window missed; no retrospective pricing")
    if abs((_time(timestamp) - _time(event_at)).total_seconds()) > MAX_QUOTE_AGE_SECONDS:
        raise ValueError("quote does not match event window")


def _chain(symbol: str, expiry: str = ""):
    from data_feeds.options_feed import get_options_feed
    target = max(1, (date.fromisoformat(expiry) - _now().date()).days) if expiry else 20
    chain = get_options_feed().get_chain(symbol, dte_target=target)
    if chain is None or not chain.is_live:
        raise ValueError("live option chain unavailable")
    if expiry and chain.expiry.isoformat() != expiry:
        raise ValueError("exact expiry unavailable; refusing another contract")
    return chain


class OptionResearchObserver:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cursor = 0
        self.rows: dict[str, dict] = {}
        if path.exists():
            # Do not replace corrupt evidence with an empty success-shaped store.
            self.rows = json.loads(path.read_text(encoding="utf-8"))["records"]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"records": self.rows}, allow_nan=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="OptionResearch", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        next_refresh = 0.0
        import time
        while not self._stop.is_set():
            try:
                self.process_events()
                if time.monotonic() >= next_refresh:
                    self.refresh()
                    next_refresh = time.monotonic() + REFRESH_SECONDS
            except Exception:
                log.warning("[OptionResearch] Background cycle failed", exc_info=True)
            self._wake.wait(timeout=1)
            self._wake.clear()

    def record_equity_entry(self, record) -> None:
        if record.fill_status not in ("FILLED", "PARTIALLY_FILLED"):
            return
        if not record.order_id:
            raise ValueError("equity research requires an order id")
        key = f"equity:{record.order_id}"
        with self._lock:
            if key in self.rows:
                return
            now = _now().isoformat()
            recent = abs((_now() - record.placed_at.astimezone()).total_seconds()) <= 900
            self.rows[key] = {
                "kind": "EQUITY_COMPARISON", "order_id": record.order_id,
                "symbol": record.symbol, "direction": record.direction,
                "stock_entry": _positive(record.actual_fill_price),
                "stock_quantity": _quantity(record.filled_quantity),
                "entry_at": now, "legs": [],
                "status": "ENTRY_PENDING" if recent else "ENTRY_UNAVAILABLE",
                "error": "" if recent else "historical equity entry cannot be repriced",
                "research_only": True, "actual_fill": False,
            }
            self._save()
        self._wake.set()

    def record_equity_exit(self, record, exit_price: float, reason: str) -> None:
        with self._lock:
            row = self.rows.get(f"equity:{record.order_id}")
            if row is None:
                log.warning("[OptionResearch] No entry observation for equity close %s", record.order_id)
                return
            if row.get("exit_at"):
                return
            row.update(stock_exit=_positive(exit_price), exit_at=_now().isoformat(),
                       stock_close_reason=reason)
            sign = 1 if row["direction"].upper() == "BUY" else -1
            row["stock_return_pct"] = sign * (exit_price / row["stock_entry"] - 1) * 100
            row["stock_gross_pnl"] = sign * (exit_price - row["stock_entry"]) * row["stock_quantity"]
            if row["status"] == "OPEN":
                row["status"] = "EXIT_PENDING"
            self._save()
        self._wake.set()

    def record_rejection(self, signal, reason: str) -> None:
        meta = json.loads(signal.notes or "{}")
        contract = meta.get("_research_contract", {})
        expiry = str(contract.get("expiry", ""))
        raw_legs = meta.get("legs", [])
        # Quote changes must not turn the same rejected structure into new trials.
        identity = [(leg.get("type"), leg.get("strike"), leg.get("direction"),
                     leg.get("ratio", 1), leg.get("quantity")) for leg in raw_legs]
        signature = json.dumps([_now().date().isoformat(), signal.symbol,
                                signal.strategy_name, expiry, identity], sort_keys=True)
        key = "rejected:" + hashlib.sha256(signature.encode()).hexdigest()[:24]
        with self._lock:
            if key in self.rows and self.rows[key]["status"] == "ENTRY_UNAVAILABLE":
                # A later real proposal may have quotes the first attempt lacked.
                # Keep the unpriced attempt; never retrofit its missing entry.
                attempt = str(contract.get("fetched_at", ""))
                priced = next((prior_key for prior_key, prior in self.rows.items()
                               if prior_key.startswith(key + ":")
                               and prior["status"] != "ENTRY_UNAVAILABLE"), None)
                key = priced or key + ":" + hashlib.sha256(attempt.encode()).hexdigest()[:12]
            if key in self.rows:
                row = self.rows[key]
                if reason not in row["rejection_reasons"]:
                    row["rejection_reasons"].append(reason)
                    self._save()
                return
            row = {
                "kind": "REJECTED_STRUCTURE", "symbol": signal.symbol,
                "strategy": signal.strategy_name, "opportunity_id": meta.get("opportunity_id", ""),
                "entry_at": _now().isoformat(), "expiry": expiry,
                "rejection_reasons": [reason], "status": "ENTRY_UNAVAILABLE",
                "stop_premium": signal.stop_loss, "target_premium": signal.target_price,
                "legs": [], "research_only": True, "actual_fill": False,
                "raw_legs": deepcopy(raw_legs),
            }
            try:
                if not contract.get("is_live") or not expiry:
                    raise ValueError("no live exact-expiry entry snapshot")
                _fresh(contract["fetched_at"], row["entry_at"])
                if date.fromisoformat(expiry) < _now().date() or not raw_legs:
                    raise ValueError("expired or empty structure")
                units = _quantity(meta.get("lots", 1)) * _quantity(meta.get("lot_size"))
                for leg in raw_legs:
                    bid, ask = _quote(leg.get("bid"), leg.get("ask"))
                    direction, option_type = leg.get("direction"), leg.get("type")
                    if direction not in ("BUY", "SELL") or option_type not in ("CE", "PE"):
                        raise ValueError("invalid option leg")
                    quantity = _quantity(leg.get("quantity", units * _positive(leg.get("ratio", 1))))
                    row["legs"].append({
                        "type": option_type, "strike": _positive(leg.get("strike")),
                        "direction": direction, "quantity": quantity,
                        "entry_price": ask if direction == "BUY" else bid,
                        "entry_bid": bid, "entry_ask": ask,
                    })
                row.update(status="OPEN", entry_quote_at=contract["fetched_at"],
                           source=contract.get("source", ""), base_quantity=units)
                row["is_credit"] = sum(
                    (1 if leg["direction"] == "SELL" else -1) * leg["entry_price"] * leg["quantity"]
                    for leg in row["legs"]) > 0
            except (ValueError, TypeError, KeyError) as exc:
                row["error"] = str(exc)
                row["legs"] = []
                log.warning("[OptionResearch] Unpriced rejected structure %s: %s", signal.symbol, exc)
            self.rows[key] = row
            self._save()
        self._wake.set()

    def process_events(self) -> None:
        with self._lock:
            pending = [(key, deepcopy(row)) for key, row in self.rows.items()
                       if row["kind"] == "EQUITY_COMPARISON"
                       and row["status"] in ("ENTRY_PENDING", "EXIT_PENDING")]
        for key, row in pending[:MAX_REFRESH_ITEMS]:
            entering = row["status"] == "ENTRY_PENDING"
            try:
                if entering:
                    chain = _chain(row["symbol"])
                    _fresh(chain.fetched_at.isoformat(), row["entry_at"])
                    leg = chain.atm_call() if row["direction"].upper() == "BUY" else chain.atm_put()
                    if leg is None or not leg.is_live or leg.expiry != chain.expiry:
                        raise ValueError("live ATM contract unavailable")
                    bid, ask = _quote(leg.bid, leg.ask)
                    from data_feeds.dhan_fno_security_map import get_fno_security_map
                    units = _quantity(get_fno_security_map().get_lot_size(row["symbol"]))
                    row.update(expiry=chain.expiry.isoformat(), entry_quote_at=chain.fetched_at.isoformat(),
                               source=chain.data_source, status="OPEN", base_quantity=units)
                    row["legs"] = [{"type": leg.option_type, "strike": leg.strike,
                                    "direction": "BUY", "quantity": units,
                                    "entry_price": ask, "entry_bid": bid, "entry_ask": ask}]
                else:
                    self._mark(row, row["exit_at"])
                    row["option_return_pct"] = (row["legs"][0]["exit_price"] / row["legs"][0]["entry_price"] - 1) * 100
                    row["status"] = "CLOSED"
                    row["close_reason"] = "MATCHED_STOCK_EXIT"
                    log.info("[OptionResearch] Equity comparison closed %s: stock=%.2f%% option=%.2f%% net=%.2f",
                             row["order_id"], row["stock_return_pct"], row["option_return_pct"], row["net_pnl"])
            except Exception as exc:
                row["status"] = "ENTRY_UNAVAILABLE" if entering else "EXIT_UNAVAILABLE"
                row["error"] = str(exc)
                log.warning("[OptionResearch] %s: %s", key, exc)
            with self._lock:
                # A stock may close while its entry quote is being fetched.
                current = self.rows[key]
                for field in ("exit_at", "stock_exit", "stock_return_pct", "stock_gross_pnl", "stock_close_reason"):
                    if field in current:
                        row[field] = current[field]
                if entering and row["status"] == "OPEN" and row.get("exit_at"):
                    row["status"] = "EXIT_PENDING"
                self.rows[key] = row
                self._save()

    def _mark(self, row: dict, event_at: str) -> None:
        chain = _chain(row["symbol"], row["expiry"])
        _fresh(chain.fetched_at.isoformat(), event_at)
        from models.transaction_costs import InstrumentType, get_cost_model
        gross = costs = liquidation = 0.0
        for leg in row["legs"]:
            contracts = chain.calls if leg["type"] == "CE" else chain.puts
            contract = next((c for c in contracts if abs(c.strike - leg["strike"]) < 0.01
                             and c.expiry.isoformat() == row["expiry"]), None)
            if contract is None or not contract.is_live:
                raise ValueError("original contract unavailable")
            bid, ask = _quote(contract.bid, contract.ask)
            buy = leg["direction"] == "BUY"
            exit_price = bid if buy else ask
            entry_price, quantity = leg["entry_price"], leg["quantity"]
            leg_gross = (exit_price - entry_price) * quantity * (1 if buy else -1)
            cost = get_cost_model().compute(
                symbol=row["symbol"], quantity=quantity,
                entry_price=entry_price if buy else exit_price,
                exit_price=exit_price if buy else entry_price,
                instrument_type=InstrumentType.OPTIONS,
            ).total_cost
            leg.update(exit_price=exit_price, gross_pnl=round(leg_gross, 2),
                       estimated_cost=round(cost, 2), net_pnl=round(leg_gross - cost, 2))
            gross += leg_gross
            costs += cost
            liquidation += exit_price * quantity * (1 if buy else -1)
        row.update(gross_pnl=round(gross, 2), estimated_cost=round(costs, 2),
                   net_pnl=round(gross - costs, 2), exit_quote_at=chain.fetched_at.isoformat(),
                   marked_at=_now().isoformat(), liquidation_premium=abs(liquidation) / row["base_quantity"],
                   pnl_method="LIVE_BID_ASK_WITH_ESTIMATED_COSTS")

    def refresh(self) -> None:
        from execution_engine.options_order_manager import DTE_EXIT_DAYS
        with self._lock:
            keys = [key for key, row in self.rows.items()
                    if row["kind"] == "REJECTED_STRUCTURE" and row["status"] == "OPEN"]
        if not keys:
            return
        start = self._cursor % len(keys)
        selected = (keys[start:] + keys[:start])[:MAX_REFRESH_ITEMS]
        self._cursor = start + len(selected)
        for key in selected:
            with self._lock:
                row = deepcopy(self.rows[key])
            try:
                if date.fromisoformat(row["expiry"]) < _now().date():
                    raise ValueError("expired without a verified closing quote")
                self._mark(row, _now().isoformat())
                value = row["liquidation_premium"]
                stop, target = row["stop_premium"], row["target_premium"]
                credit = row["is_credit"]
                reason = ""
                if stop > 0 and (value >= stop if credit else value <= stop):
                    reason = "STOP_LOSS"
                elif target > 0 and (value <= target if credit else value >= target):
                    reason = "TARGET_HIT"
                elif (date.fromisoformat(row["expiry"]) - _now().date()).days <= DTE_EXIT_DAYS:
                    reason = "DTE_EXIT"
                if reason:
                    row.update(status="CLOSED", close_reason=reason, exit_at=_now().isoformat(),
                               grade="GOOD" if row["net_pnl"] > 0 else "BAD" if row["net_pnl"] < 0 else "AVERAGE")
                    log.info("[OptionResearch] Virtual structure closed %s: %s net=%.2f",
                             key, reason, row["net_pnl"])
                row.pop("error", None)
            except Exception as exc:
                # Preserve the last mark as a mark, never turn it into a close.
                row["error"] = str(exc)
                if date.fromisoformat(row["expiry"]) < _now().date():
                    row["status"] = "EXIT_UNAVAILABLE"
                log.warning("[OptionResearch] Mark unavailable %s: %s", key, exc)
            with self._lock:
                row["rejection_reasons"] = self.rows[key]["rejection_reasons"]
                self.rows[key] = row
                self._save()

    def snapshot(self) -> dict:
        with self._lock:
            return deepcopy(self.rows)


_instance: OptionResearchObserver | None = None
_instance_lock = threading.Lock()


def get_option_research_observer() -> OptionResearchObserver:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = OptionResearchObserver()
        return _instance


def start_option_research() -> None:
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        get_option_research_observer().start()


def stop_option_research() -> None:
    if _instance is not None:
        _instance.stop()


def observe_equity_entry(record) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        get_option_research_observer().record_equity_entry(record)
    except Exception:
        log.warning("[OptionResearch] Equity entry recording failed", exc_info=True)


def observe_equity_exit(record, exit_price: float, reason: str) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        get_option_research_observer().record_equity_exit(record, exit_price, reason)
    except Exception:
        log.warning("[OptionResearch] Equity exit recording failed", exc_info=True)


def observe_rejection(signal, reason: str) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    try:
        get_option_research_observer().record_rejection(signal, reason)
    except Exception:
        log.warning("[OptionResearch] Rejected structure recording failed", exc_info=True)
