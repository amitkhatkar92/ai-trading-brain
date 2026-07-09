"""iios/investment/models/investment_session.py
InvestmentSession — groups related requests and results.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.investment.investment_constants import SessionStatus
from iios.investment.models.investment_request import InvestmentRequest
from iios.investment.models.investment_result import InvestmentResult


@dataclass
class InvestmentSession:
    """Tracks the lifecycle of a group of related investment analyses."""

    session_id:  str                    = field(default_factory=lambda: str(uuid.uuid4()))
    name:        str                    = ""
    source_id:   str                    = ""
    status:      SessionStatus          = SessionStatus.ACTIVE
    requests:    list[InvestmentRequest] = field(default_factory=list)
    results:     list[InvestmentResult]  = field(default_factory=list)
    metadata:    dict                   = field(default_factory=dict)
    created_at:  float                  = field(default_factory=time.time)
    closed_at:   float | None           = None

    def add_request(self, request: InvestmentRequest) -> None:
        self.requests.append(request)

    def add_result(self, result: InvestmentResult) -> None:
        self.results.append(result)

    def close(self) -> None:
        self.status    = SessionStatus.CLOSED
        self.closed_at = time.time()

    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE

    def to_dict(self) -> dict:
        return {
            "session_id":    self.session_id,
            "name":          self.name,
            "source_id":     self.source_id,
            "status":        self.status.value,
            "request_count": len(self.requests),
            "result_count":  len(self.results),
            "created_at":    self.created_at,
            "closed_at":     self.closed_at,
        }
