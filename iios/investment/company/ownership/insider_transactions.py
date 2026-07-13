"""iios/investment/company/ownership/insider_transactions.py
Insider transaction data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InsiderTransaction:
    """A single reported insider transaction."""
    insider_role:     str               # "CEO" | "CFO" | "Director" | etc.
    transaction_type: str               # "buy" | "sell"
    shares:           int = 0
    value:            Optional[float] = None    # transaction value in currency
    date_reported:    Optional[str]  = None     # ISO date string

    @property
    def is_buy(self) -> bool:
        return self.transaction_type.lower() in ("buy", "purchase", "acquisition")

    @property
    def is_sell(self) -> bool:
        return self.transaction_type.lower() in ("sell", "sale", "disposal")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insider_role":     self.insider_role,
            "transaction_type": self.transaction_type,
            "shares":           self.shares,
            "value":            self.value,
            "date_reported":    self.date_reported,
        }


@dataclass
class InsiderTransactionLog:
    """Aggregated view of all recent insider transactions."""
    transactions: List[InsiderTransaction] = field(default_factory=list)

    @property
    def buy_count(self) -> int:
        return sum(1 for t in self.transactions if t.is_buy)

    @property
    def sell_count(self) -> int:
        return sum(1 for t in self.transactions if t.is_sell)

    @property
    def total_count(self) -> int:
        return len(self.transactions)

    @property
    def net_shares(self) -> int:
        """Net shares bought (negative = net selling)."""
        net = 0
        for t in self.transactions:
            if t.is_buy:
                net += t.shares
            elif t.is_sell:
                net -= t.shares
        return net

    @property
    def net_buy_ratio(self) -> float:
        """Fraction of transactions that are buys (0-1)."""
        if not self.transactions:
            return 0.5
        return self.buy_count / len(self.transactions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buy_count":     self.buy_count,
            "sell_count":    self.sell_count,
            "total_count":   self.total_count,
            "net_shares":    self.net_shares,
            "net_buy_ratio": round(self.net_buy_ratio, 3),
        }


def build_transaction_log(raw_transactions: Optional[List[Dict]]) -> InsiderTransactionLog:
    """Build an InsiderTransactionLog from a list of raw transaction dicts."""
    log = InsiderTransactionLog()
    if not raw_transactions:
        return log
    for t in raw_transactions:
        tx = InsiderTransaction(
            insider_role=str(t.get("role") or t.get("insider_role") or "Unknown"),
            transaction_type=str(t.get("type") or t.get("transaction_type") or "sell"),
            shares=int(t.get("shares") or 0),
            value=t.get("value"),
            date_reported=t.get("date") or t.get("date_reported"),
        )
        log.transactions.append(tx)
    return log
