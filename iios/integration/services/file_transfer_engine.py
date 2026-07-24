"""
file_transfer_engine.py — iios.integration.services
-----------------------------------------------------
FileTransferEngine — provider-independent file transfer interface.

Supports upload and download operations. Actual implementation (FTP, SFTP,
S3, GCS, Azure Blob) is injected at deployment time.

MUST NOT import: boto3, paramiko, ftplib, or any file-transfer library.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .connector_request import ConnectorRequest
from .connector_response import ConnectorResponse

_log = get_logger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Data objects
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TransferRecord:
    """Immutable record of a completed file transfer."""
    transfer_id:   str
    operation:     str           # "upload" | "download"
    source_path:   str
    dest_path:     str
    bytes_transferred: int
    success:       bool
    latency_ms:    float
    created_at:    str


# ════════════════════════════════════════════════════════════════════════
# Abstract Interface
# ════════════════════════════════════════════════════════════════════════


class BaseFileTransferAdapter(ABC):
    """Abstract file transfer adapter — implementors inject the transport."""

    @abstractmethod
    def upload(
        self,
        source_path: str,
        dest_path:   str,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> TransferRecord:
        """Upload a file from source_path to dest_path on the remote."""

    @abstractmethod
    def download(
        self,
        source_path: str,
        dest_path:   str,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> TransferRecord:
        """Download a file from source_path on the remote to dest_path."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the transfer endpoint is reachable."""


class SimulatedFileTransferAdapter(BaseFileTransferAdapter):
    """In-process file transfer simulation — no I/O."""

    def upload(
        self,
        source_path: str,
        dest_path:   str,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> TransferRecord:
        return TransferRecord(
            transfer_id=f"txfr-{uuid.uuid4().hex[:10]}",
            operation="upload",
            source_path=source_path,
            dest_path=dest_path,
            bytes_transferred=1024,
            success=True,
            latency_ms=1.0,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def download(
        self,
        source_path: str,
        dest_path:   str,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> TransferRecord:
        return TransferRecord(
            transfer_id=f"txfr-{uuid.uuid4().hex[:10]}",
            operation="download",
            source_path=source_path,
            dest_path=dest_path,
            bytes_transferred=1024,
            success=True,
            latency_ms=1.0,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def health_check(self) -> bool:
        return True


# ════════════════════════════════════════════════════════════════════════
# Engine
# ════════════════════════════════════════════════════════════════════════


class FileTransferEngine:
    """
    Executes upload/download requests through registered transfer adapters.
    """

    def __init__(self, adapter: Optional[BaseFileTransferAdapter] = None) -> None:
        self._lock     = threading.Lock()
        self._adapter  = adapter or SimulatedFileTransferAdapter()
        self._uploads  = 0
        self._downloads = 0
        self._errors   = 0

    def execute(self, request: ConnectorRequest) -> ConnectorResponse:
        start = time.perf_counter_ns()
        try:
            cfg       = request.connector_config
            operation = cfg.get("transfer_operation", "upload").lower()
            src       = cfg.get("transfer_source_path", "/tmp/source")
            dest      = cfg.get("transfer_dest_path",   "/tmp/dest")
            if operation == "download":
                record = self._adapter.download(src, dest, metadata=request.metadata)
                with self._lock:
                    self._downloads += 1
            else:
                record = self._adapter.upload(src, dest, metadata=request.metadata)
                with self._lock:
                    self._uploads += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.success(
                request.request_id,
                data={
                    "transfer_id":       record.transfer_id,
                    "bytes_transferred": record.bytes_transferred,
                    "operation":         record.operation,
                },
                latency_ms   = latency_ms,
                adapter_id   = "file-transfer-engine",
                transport    = "file_system",
            )
        except Exception as exc:
            with self._lock:
                self._errors += 1
            latency_ms = (time.perf_counter_ns() - start) / 1_000_000
            return ConnectorResponse.failure(
                request.request_id, error_message=str(exc), latency_ms=latency_ms,
                adapter_id="file-transfer-engine", transport="file_system",
            )

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"uploads": self._uploads, "downloads": self._downloads,
                    "errors": self._errors}
