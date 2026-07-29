"""
iios.ai.model_management
===========================
A2 – Model Management Platform for the IIOS AI Platform.

Six-layer architecture:

    M1  Lifecycle          reuses AILifecycleAwareMixin from A1 AI Foundation
    M2  Engine             registry/ · router/ · health/ · configuration/
    M3  Policy Framework   policy/
    M4  Core Framework     core/ · capabilities/ · events/ · exceptions/
    M5  Snapshot           snapshot/
    M6  Gateway            gateway/  (single public entry point)

    container/  — ModelManagementContainer (DI composition root)

Public API::

    from iios.ai.model_management.gateway import ModelManagementGateway

A2 Model Management — Phase 3, Module 2
Version: 1.0.0
"""
from __future__ import annotations

VERSION = "1.0.0"
