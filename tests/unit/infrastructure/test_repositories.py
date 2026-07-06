"""
tests/unit/infrastructure/test_repositories.py
===============================================
Tests for the iios.infrastructure.repositories subpackage.
"""

from __future__ import annotations

import pytest

from iios.infrastructure.repositories import (
    BaseRepository, InMemoryRepository,
    InMemoryUnitOfWork,
    TransactionManager,
    RepositoryRegistry, get_repository_registry, reset_repository_registry,
    RepositoryFactory,
    RepositoryManager, get_repository_manager, reset_repository_manager,
)
from iios.infrastructure.infrastructure_exceptions import (
    RepositoryError, TransactionError, UnitOfWorkError,
)


# ---------------------------------------------------------------------------
# InMemoryRepository
# ---------------------------------------------------------------------------

class Entity:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class TestInMemoryRepository:
    def _repo(self):
        return InMemoryRepository(key_fn=lambda e: e.id)

    def test_save_and_get(self):
        repo = self._repo()
        e = Entity(1, "RELIANCE")
        repo.save(e)
        assert repo.get(1) is e

    def test_get_missing_returns_none(self):
        repo = self._repo()
        assert repo.get(999) is None

    def test_get_all(self):
        repo = self._repo()
        repo.save(Entity(1, "A"))
        repo.save(Entity(2, "B"))
        assert len(repo.get_all()) == 2

    def test_save_all(self):
        repo = self._repo()
        repo.save_all([Entity(1, "A"), Entity(2, "B")])
        assert repo.count() == 2

    def test_delete(self):
        repo = self._repo()
        repo.save(Entity(1, "A"))
        assert repo.delete(1)
        assert repo.get(1) is None

    def test_delete_missing(self):
        repo = self._repo()
        assert not repo.delete(999)

    def test_delete_all(self):
        repo = self._repo()
        repo.save(Entity(1, "A"))
        repo.save(Entity(2, "B"))
        assert repo.delete_all() == 2
        assert repo.count() == 0

    def test_exists(self):
        repo = self._repo()
        repo.save(Entity(1, "A"))
        assert repo.exists(1)
        assert not repo.exists(999)

    def test_count(self):
        repo = self._repo()
        repo.save(Entity(1, "A"))
        repo.save(Entity(2, "B"))
        assert repo.count() == 2

    def test_find(self):
        repo = self._repo()
        repo.save(Entity(1, "RELIANCE"))
        repo.save(Entity(2, "TATA"))
        results = repo.find(name="RELIANCE")
        assert len(results) == 1 and results[0].id == 1

    def test_auto_key_from_id(self):
        repo: InMemoryRepository = InMemoryRepository()  # no key_fn; uses .id
        e = Entity(10, "X")
        repo.save(e)
        assert repo.get(10) is e

    def test_update(self):
        repo = self._repo()
        e = Entity(1, "OLD")
        repo.save(e)
        e2 = Entity(1, "NEW")
        repo.save(e2)
        assert repo.get(1).name == "NEW"


# ---------------------------------------------------------------------------
# InMemoryUnitOfWork
# ---------------------------------------------------------------------------

class TestInMemoryUnitOfWork:
    def test_commit(self):
        committed = []
        uow = InMemoryUnitOfWork()
        with uow.begin():
            uow.on_commit(lambda: committed.append(True))
        assert committed == [True]

    def test_rollback_on_exception(self):
        rolled = []
        uow = InMemoryUnitOfWork()
        with pytest.raises(UnitOfWorkError):
            with uow.begin():
                uow.on_rollback(lambda: rolled.append(True))
                raise ValueError("simulated error")
        assert rolled == [True]

    def test_is_active(self):
        uow = InMemoryUnitOfWork()
        active_during = []
        with uow.begin():
            active_during.append(uow.is_active)
        assert active_during == [True]

    def test_record(self):
        uow = InMemoryUnitOfWork()
        with uow.begin():
            uow.record({"op": "INSERT", "entity": "trade"})
            assert len(uow.pending_operations) == 1

    def test_nested_raises(self):
        uow = InMemoryUnitOfWork()
        with pytest.raises(UnitOfWorkError):
            with uow.begin():
                with uow.begin():
                    pass


# ---------------------------------------------------------------------------
# TransactionManager
# ---------------------------------------------------------------------------

class TestTransactionManager:
    def test_commit_increments_count(self):
        tm = TransactionManager()
        with tm.transaction():
            pass
        assert tm.committed_count == 1

    def test_rollback_on_exception(self):
        tm = TransactionManager()
        with pytest.raises(TransactionError):
            with tm.transaction():
                raise ValueError("fail")
        assert tm.rolled_back_count == 1

    def test_active_transactions(self):
        tm = TransactionManager()
        active = []
        with tm.transaction():
            active.append(len(tm.active_transactions()))
        assert active == [1]
        assert len(tm.active_transactions()) == 0


# ---------------------------------------------------------------------------
# RepositoryRegistry
# ---------------------------------------------------------------------------

class TestRepositoryRegistry:
    def setup_method(self):
        reset_repository_registry()

    def teardown_method(self):
        reset_repository_registry()

    def test_register_and_get(self):
        reg = get_repository_registry()
        repo = InMemoryRepository()
        reg.register("trades", repo)
        assert reg.get("trades") is repo

    def test_register_duplicate_raises(self):
        reg = get_repository_registry()
        reg.register("trades", InMemoryRepository())
        with pytest.raises(RepositoryError):
            reg.register("trades", InMemoryRepository())

    def test_register_override(self):
        reg = get_repository_registry()
        r1 = InMemoryRepository()
        r2 = InMemoryRepository()
        reg.register("trades", r1)
        reg.register("trades", r2, allow_override=True)
        assert reg.get("trades") is r2

    def test_has(self):
        reg = get_repository_registry()
        reg.register("x", InMemoryRepository())
        assert reg.has("x")
        assert not reg.has("y")

    def test_names(self):
        reg = get_repository_registry()
        reg.register("a", InMemoryRepository())
        reg.register("b", InMemoryRepository())
        assert "a" in reg.names() and "b" in reg.names()

    def test_unregister(self):
        reg = get_repository_registry()
        reg.register("a", InMemoryRepository())
        reg.unregister("a")
        assert not reg.has("a")


# ---------------------------------------------------------------------------
# RepositoryFactory
# ---------------------------------------------------------------------------

class TestRepositoryFactory:
    def test_register_and_create(self):
        factory = RepositoryFactory()
        factory.register("trades", lambda: InMemoryRepository())
        repo = factory.create("trades")
        assert isinstance(repo, InMemoryRepository)

    def test_create_missing_raises(self):
        factory = RepositoryFactory()
        with pytest.raises(RepositoryError):
            factory.create("nonexistent")

    def test_register_class(self):
        factory = RepositoryFactory()
        factory.register_class("trades", InMemoryRepository)
        repo = factory.create("trades")
        assert isinstance(repo, InMemoryRepository)


# ---------------------------------------------------------------------------
# RepositoryManager
# ---------------------------------------------------------------------------

class TestRepositoryManager:
    def setup_method(self):
        reset_repository_manager()

    def teardown_method(self):
        reset_repository_manager()

    def test_singleton(self):
        m1 = get_repository_manager()
        m2 = get_repository_manager()
        assert m1 is m2

    def test_unit_of_work_context(self):
        mgr = get_repository_manager()
        with mgr.unit_of_work() as uow:
            assert uow.is_active
