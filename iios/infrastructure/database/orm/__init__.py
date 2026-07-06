"""
iios/infrastructure/database/orm/__init__.py
"""
from __future__ import annotations

from .specification import (
    Specification,
    Eq, Ne, Gt, Ge, Lt, Le,
    Like, ILike, In, NotIn,
    IsNull, IsNotNull,
    Between,
    And, Or, Not,
    Always, Never,
)
from .entity_mapper import EntityMapper
from .base_model import BaseModel
from .model_registry import ModelRegistry, get_model_registry, reset_model_registry
from .query_builder import OrmQueryBuilder
from .query_executor import QueryExecutor

__all__ = [
    # Specifications
    "Specification",
    "Eq", "Ne", "Gt", "Ge", "Lt", "Le",
    "Like", "ILike", "In", "NotIn",
    "IsNull", "IsNotNull",
    "Between",
    "And", "Or", "Not",
    "Always", "Never",
    # ORM
    "EntityMapper",
    "BaseModel",
    "ModelRegistry", "get_model_registry", "reset_model_registry",
    "OrmQueryBuilder",
    "QueryExecutor",
]
