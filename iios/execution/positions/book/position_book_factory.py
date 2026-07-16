"""iios/execution/positions/book/position_book_factory.py
==================================================
BookFactory — creates BookEntry objects from Position instances.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

from iios.execution.positions.lifecycle import Position

from .constants import ACTOR_BOOK, FACTORY_SYSTEM_ID
from .exceptions import PositionBookValidationError
from .position_entry import BookEntry


class BookFactory:
    """
    Creates ``BookEntry`` objects from live ``Position`` instances.

    Validates that the position meets minimum identity requirements
    before wrapping it in a BookEntry.

    Non-responsibilities
    --------------------
    * No state machine logic.
    * No index management.
    * No registry interaction.
    """

    def create(
        self,
        position: Position,
        added_by: str = ACTOR_BOOK,
    ) -> BookEntry:
        """
        Create a ``BookEntry`` wrapping *position*.

        Raises
        ------
        PositionBookValidationError
            If the position fails minimum identity requirements.
        """
        self._validate(position)
        return BookEntry(position=position, added_by=added_by)

    # ── Private validation ────────────────────────────────────────────────────

    def _validate(self, position: Position) -> None:
        errors = []
        if not position.position_id:
            errors.append("position_id must not be empty")
        if not position.instrument:
            errors.append("instrument must not be empty")
        if not position.exchange:
            errors.append("exchange must not be empty")
        if position.product is None:
            errors.append("product must not be None")
        if position.direction is None:
            errors.append("direction must not be None")
        if position.quantity <= 0:
            errors.append("quantity must be positive")
        if errors:
            raise PositionBookValidationError(
                f"Cannot add position to book: {'; '.join(errors)}",
                errors=tuple(errors),
            )
