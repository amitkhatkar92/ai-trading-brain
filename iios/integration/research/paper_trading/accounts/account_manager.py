"""accounts/account_manager.py — Multi-account management for the Paper Trading Framework."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    AccountStatus,
    DEFAULT_BUYING_POWER_MULTIPLIER,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_ACCOUNTS,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    AccountError,
    AccountNotFoundError,
    AccountSuspendedError,
)
from iios.integration.research.paper_trading.core.paper_account import PaperAccount


class AccountManager:
    """
    Creates and manages multiple paper trading accounts.

    Thread-safe via a single RLock.
    """

    def __init__(self, max_accounts: int = DEFAULT_MAX_ACCOUNTS) -> None:
        self._accounts:    dict[str, PaperAccount] = {}
        self._max          = max_accounts
        self._lock         = threading.RLock()
        self._total_created = 0

    # ── Factory ───────────────────────────────────────────────────────────────

    def create_account(
        self,
        name:            str,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        *,
        account_id:      Optional[str] = None,
        leverage:        float          = DEFAULT_BUYING_POWER_MULTIPLIER,
        metadata:        Optional[dict] = None,
    ) -> PaperAccount:
        with self._lock:
            if len(self._accounts) >= self._max:
                raise AccountError(f"Account limit ({self._max}) reached")
            account = PaperAccount.create(
                name            = name,
                initial_capital = initial_capital,
                account_id      = account_id,
                leverage        = leverage,
                metadata        = metadata,
            )
            self._accounts[account.account_id] = account
            self._total_created += 1
        return account

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_account(self, account_id: str) -> PaperAccount:
        with self._lock:
            account = self._accounts.get(account_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id!r} not found")
        return account

    def update_account(self, account: PaperAccount) -> None:
        with self._lock:
            if account.account_id not in self._accounts:
                raise AccountNotFoundError(
                    f"Account {account.account_id!r} not found"
                )
            self._accounts[account.account_id] = account

    def has_account(self, account_id: str) -> bool:
        with self._lock:
            return account_id in self._accounts

    # ── Status changes ────────────────────────────────────────────────────────

    def suspend_account(self, account_id: str, reason: str) -> None:
        account = self.get_account(account_id)
        if account.status == AccountStatus.CLOSED:
            raise AccountError(f"Cannot suspend closed account {account_id!r}")
        account.status = AccountStatus.SUSPENDED
        account.metadata["suspend_reason"] = reason
        account.touch()
        with self._lock:
            self._accounts[account_id] = account

    def close_account(self, account_id: str) -> None:
        account = self.get_account(account_id)
        account.status = AccountStatus.CLOSED
        account.touch()
        with self._lock:
            self._accounts[account_id] = account

    def reactivate_account(self, account_id: str) -> None:
        account = self.get_account(account_id)
        if account.status == AccountStatus.CLOSED:
            raise AccountError(f"Cannot reactivate closed account {account_id!r}")
        account.status = AccountStatus.ACTIVE
        account.touch()
        with self._lock:
            self._accounts[account_id] = account

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_accounts(self) -> list[PaperAccount]:
        with self._lock:
            return list(self._accounts.values())

    def active_accounts(self) -> list[PaperAccount]:
        with self._lock:
            return [a for a in self._accounts.values() if a.status == AccountStatus.ACTIVE]

    def count(self) -> int:
        with self._lock:
            return len(self._accounts)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for a in self._accounts.values():
                by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
            return {
                "total_accounts":   len(self._accounts),
                "total_created":    self._total_created,
                "capacity":         self._max,
                "by_status":        by_status,
            }
