"""iios/execution/orders/order_exceptions.py

OR-xxx  Order Management System exception hierarchy.
"""
from __future__ import annotations


class OMSError(Exception):
    """Root exception for every OMS error."""
    code: str = "OR-000"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ── Order creation / lookup ────────────────────────────────────────────────────

class OrderNotFoundError(OMSError):
    code = "OR-001"

    def __init__(self, message: str = "", *, order_id: str = "") -> None:
        super().__init__(message or f"Order not found: {order_id!r}")
        self.order_id = order_id


class OrderAlreadyExistsError(OMSError):
    code = "OR-002"

    def __init__(self, message: str = "", *, order_id: str = "") -> None:
        super().__init__(message or f"Order already exists: {order_id!r}")
        self.order_id = order_id


class OrderCreationError(OMSError):
    code = "OR-003"

    def __init__(self, message: str = "", *, reason: str = "") -> None:
        super().__init__(message)
        self.reason = reason


# ── Lifecycle / state machine ─────────────────────────────────────────────────

class InvalidOrderStatusError(OMSError):
    code = "OR-010"

    def __init__(self, message: str = "", *, order_id: str = "", from_status: str = "", to_status: str = "") -> None:
        super().__init__(message or f"Invalid transition {from_status!r} → {to_status!r} for {order_id!r}")
        self.order_id   = order_id
        self.from_status = from_status
        self.to_status  = to_status


class OrderTerminalError(OMSError):
    """Attempted to modify an order that is in a terminal state."""
    code = "OR-011"

    def __init__(self, message: str = "", *, order_id: str = "", status: str = "") -> None:
        super().__init__(message or f"Order {order_id!r} is terminal (status={status!r})")
        self.order_id = order_id
        self.status   = status


# ── Validation ────────────────────────────────────────────────────────────────

class OrderValidationError(OMSError):
    code = "OR-020"

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []


class OrderConstraintViolationError(OMSError):
    code = "OR-021"

    def __init__(self, message: str = "", *, field: str = "", constraint: str = "") -> None:
        super().__init__(message)
        self.field      = field
        self.constraint = constraint


# ── Fill ─────────────────────────────────────────────────────────────────────

class OrderFillError(OMSError):
    code = "OR-030"

    def __init__(self, message: str = "", *, order_id: str = "", fill_qty: float = 0.0) -> None:
        super().__init__(message)
        self.order_id = order_id
        self.fill_qty = fill_qty


class OverfillError(OMSError):
    code = "OR-031"

    def __init__(self, message: str = "", *, order_id: str = "", requested: float = 0.0, remaining: float = 0.0) -> None:
        super().__init__(message or f"Overfill: requested {requested} but remaining {remaining}")
        self.order_id  = order_id
        self.requested = requested
        self.remaining = remaining


# ── Queue ─────────────────────────────────────────────────────────────────────

class QueueFullError(OMSError):
    code = "OR-040"

    def __init__(self, message: str = "", *, queue_name: str = "", capacity: int = 0) -> None:
        super().__init__(message or f"Queue {queue_name!r} is full (capacity={capacity})")
        self.queue_name = queue_name
        self.capacity   = capacity


class QueueNotFoundError(OMSError):
    code = "OR-041"

    def __init__(self, message: str = "", *, queue_name: str = "") -> None:
        super().__init__(message or f"Queue not found: {queue_name!r}")
        self.queue_name = queue_name


# ── OMS engine ────────────────────────────────────────────────────────────────

class OMSNotInitializedError(OMSError):
    code = "OR-050"


class OMSCapacityError(OMSError):
    code = "OR-051"

    def __init__(self, message: str = "", *, max_orders: int = 0) -> None:
        super().__init__(message or f"OMS capacity exceeded (max={max_orders})")
        self.max_orders = max_orders


class OMSShutdownError(OMSError):
    code = "OR-052"


# ── Routing ───────────────────────────────────────────────────────────────────

class OrderRoutingError(OMSError):
    code = "OR-060"

    def __init__(self, message: str = "", *, order_id: str = "", reason: str = "") -> None:
        super().__init__(message)
        self.order_id = order_id
        self.reason   = reason


class NoRouteFoundError(OMSError):
    code = "OR-061"

    def __init__(self, message: str = "", *, order_id: str = "", asset_id: str = "") -> None:
        super().__init__(message or f"No route found for order {order_id!r} (asset={asset_id!r})")
        self.order_id  = order_id
        self.asset_id  = asset_id


# ── Modification ─────────────────────────────────────────────────────────────

class OrderModificationError(OMSError):
    code = "OR-070"

    def __init__(self, message: str = "", *, order_id: str = "") -> None:
        super().__init__(message)
        self.order_id = order_id


class OrderSplitError(OMSError):
    code = "OR-071"

    def __init__(self, message: str = "", *, order_id: str = "") -> None:
        super().__init__(message)
        self.order_id = order_id


class OrderMergeError(OMSError):
    code = "OR-072"

    def __init__(self, message: str = "", *, order_ids: list[str] | None = None) -> None:
        super().__init__(message)
        self.order_ids = order_ids or []
