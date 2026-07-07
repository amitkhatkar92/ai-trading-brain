"""
iios/knowledge/repositories/__init__.py
"""
from __future__ import annotations
from .knowledge_repository import (
    KnowledgeRepository, get_knowledge_repository, reset_knowledge_repository,
)
__all__ = ["KnowledgeRepository", "get_knowledge_repository", "reset_knowledge_repository"]
