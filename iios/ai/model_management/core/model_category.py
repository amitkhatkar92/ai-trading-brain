"""
model_category.py -- iios.ai.model_management.core
=====================================================
:class:`ModelCategory` — broad classification of AI model types.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from enum import Enum


class ModelCategory(str, Enum):
    """Broad category of an AI model."""
    LANGUAGE_MODEL    = "language_model"
    EMBEDDING         = "embedding"
    VISION            = "vision"
    AUDIO             = "audio"
    MULTIMODAL        = "multimodal"
    SPECIALIZED       = "specialized"
    CUSTOM            = "custom"
