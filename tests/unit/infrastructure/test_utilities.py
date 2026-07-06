"""
tests/unit/infrastructure/test_utilities.py
===========================================
Tests for retry, rate_limiter, circuit_breaker, security, database, messaging.
"""

from __future__ import annotations

import time
import threading
import tempfile
import pytest

from iios.infrastructure.utilities import retry, RetryConfig, RateLimiter, RateLimitExceeded, CircuitBreaker, CircuitBreakerOpen
from iios.infrastructure.security import TokenManager, SymmetricEncryption, generate_key
from iios.infrastructure.infrastructure_exceptions import SecurityError
from iios.infrastructure.database import SQLiteBackend, QueryBuilder
from iios.infrastructure.messaging import Message, MessageQueue, MessageBroker, get_message_broker, reset_message_broker


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

class TestRetry:
    def test_succeeds_first_try(self):
        calls = []

        @retry(max_attempts=3)
        def fn():
            calls.append(1)
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 1

    def test_retries_on_failure(self):
        calls = []

        @retry(max_attempts=3, backoff_base=0.0, jitter=False)
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("fail")
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 3

    def test_raises_after_max_attempts(self):
        @retry(max_attempts=3, backoff_base=0.0, jitter=False)
        def fn():
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            fn()

    def test_specific_exception_type(self):
        calls = []

        @retry(max_attempts=3, backoff_base=0.0, jitter=False, exceptions=(IOError,))
        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise IOError("io fail")
            return "ok"

        assert fn() == "ok"

    def test_retry_config_backoff(self):
        config = RetryConfig(max_attempts=3, backoff_base=1.0, backoff_multiplier=2.0, jitter=False)
        assert config.backoff_for(0) == 1.0
        assert config.backoff_for(1) == 2.0
        assert config.backoff_for(2) == 4.0

    def test_retry_config_backoff_max(self):
        config = RetryConfig(max_attempts=5, backoff_base=1.0, backoff_max=3.0, jitter=False)
        assert config.backoff_for(10) == 3.0


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter(limit=10, window=1.0)
        for _ in range(10):
            assert limiter.try_acquire()

    def test_blocks_over_limit(self):
        limiter = RateLimiter(limit=3, window=1.0)
        for _ in range(3):
            limiter.try_acquire()
        assert not limiter.try_acquire()

    def test_current_count(self):
        limiter = RateLimiter(limit=100, window=1.0)
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.current_count == 2

    def test_acquire_blocks_then_allows(self):
        limiter = RateLimiter(limit=2, window=0.1)
        limiter.try_acquire()
        limiter.try_acquire()
        # Third acquire should block until window expires
        t0 = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.05  # at least some wait

    def test_acquire_timeout_raises(self):
        limiter = RateLimiter(limit=1, window=10.0)
        limiter.try_acquire()
        with pytest.raises(RateLimitExceeded):
            limiter.acquire(timeout=0.05)


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_closed_by_default(self):
        cb = CircuitBreaker(threshold=3)
        assert cb.is_closed

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=3, reset_timeout=60.0)
        for _ in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass
        assert cb.is_open

    def test_rejects_when_open(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=60.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        with pytest.raises(CircuitBreakerOpen):
            cb.call(lambda: None)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=0.05)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        time.sleep(0.1)
        assert cb.is_half_open

    def test_resets_on_success(self):
        cb = CircuitBreaker(threshold=3)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        cb.call(lambda: None)  # success resets
        assert cb.is_closed

    def test_decorator_usage(self):
        cb = CircuitBreaker(threshold=5)
        calls = []

        @cb
        def fn():
            calls.append(1)
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 1

    def test_reset(self):
        cb = CircuitBreaker(threshold=1, reset_timeout=60.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError()))
        except RuntimeError:
            pass
        cb.reset()
        assert cb.is_closed


# ---------------------------------------------------------------------------
# TokenManager
# ---------------------------------------------------------------------------

class TestTokenManager:
    def test_generate_and_validate(self):
        tm = TokenManager(secret="test-secret")
        token = tm.generate({"user": "bot"})
        claims = tm.validate(token)
        assert claims["user"] == "bot"

    def test_expired_token_raises(self):
        tm = TokenManager(secret="secret", ttl=1)
        token = tm.generate({"u": "x"})
        # Patch claims to be already expired
        import base64, json, time as _time
        parts = token.split(".")
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        claims["exp"] = int(_time.time()) - 10  # 10 seconds in the past
        new_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()
        # Re-sign with the correct secret
        signing_input = f"{parts[0]}.{new_payload_b64}"
        import hmac as _hmac, hashlib
        sig = _hmac.new(b"secret", signing_input.encode(), "sha256")
        sig_b64 = base64.urlsafe_b64encode(sig.digest()).rstrip(b"=").decode()
        expired_token = f"{signing_input}.{sig_b64}"
        with pytest.raises(SecurityError, match="expired"):
            tm.validate(expired_token)

    def test_invalid_signature_raises(self):
        tm = TokenManager(secret="secret1")
        token = tm.generate({"u": "x"})
        tm2 = TokenManager(secret="different_secret")
        with pytest.raises(SecurityError):
            tm2.validate(token)

    def test_is_valid(self):
        tm = TokenManager(secret="secret")
        token = tm.generate({"u": "x"})
        assert tm.is_valid(token)

    def test_malformed_token(self):
        tm = TokenManager(secret="secret")
        with pytest.raises(SecurityError, match="Malformed"):
            tm.validate("not.a.valid.token.with.too.many.parts")

    def test_empty_secret_raises(self):
        with pytest.raises(SecurityError):
            TokenManager(secret="")


# ---------------------------------------------------------------------------
# SymmetricEncryption
# ---------------------------------------------------------------------------

class TestSymmetricEncryption:
    def test_encrypt_decrypt(self):
        enc = SymmetricEncryption()
        plaintext = b"secret trading data"
        ciphertext = enc.encrypt(plaintext)
        assert ciphertext != plaintext
        assert enc.decrypt(ciphertext) == plaintext

    def test_encrypt_decrypt_text(self):
        enc = SymmetricEncryption()
        token = enc.encrypt_text("hello world")
        assert enc.decrypt_text(token) == "hello world"

    def test_different_keys_fail(self):
        enc1 = SymmetricEncryption(key=generate_key())
        enc2 = SymmetricEncryption(key=generate_key())
        ciphertext = enc1.encrypt(b"data")
        with pytest.raises(SecurityError):
            enc2.decrypt(ciphertext)

    def test_generate_key(self):
        k = generate_key()
        assert len(k) > 20


# ---------------------------------------------------------------------------
# SQLiteBackend + QueryBuilder
# ---------------------------------------------------------------------------

class TestSQLiteBackend:
    @pytest.fixture
    def db(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "test.db"))
        yield backend
        backend.close()

    def test_execute_and_query(self, db):
        db.execute("CREATE TABLE t (id INTEGER, name TEXT)")
        db.execute("INSERT INTO t VALUES (?,?)", (1, "RELIANCE"))
        rows = db.query("SELECT * FROM t")
        assert len(rows) == 1
        assert rows[0]["name"] == "RELIANCE"

    def test_query_one(self, db):
        db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO t VALUES (?,?)", (1, "TATA"))
        row = db.query_one("SELECT * FROM t WHERE id=?", (1,))
        assert row is not None
        assert row["name"] == "TATA"

    def test_query_one_missing(self, db):
        db.execute("CREATE TABLE t (id INTEGER)")
        row = db.query_one("SELECT * FROM t WHERE id=?", (999,))
        assert row is None

    def test_transaction_commit(self, db):
        db.execute("CREATE TABLE t (id INTEGER)")
        with db.transaction():
            db.execute("INSERT INTO t VALUES (?)", (1,))
        assert len(db.query("SELECT * FROM t")) == 1

    def test_transaction_rollback_on_error(self, db):
        db.execute("CREATE TABLE t (id INTEGER)")
        with pytest.raises(Exception):
            with db.transaction():
                db.execute("INSERT INTO t VALUES (?)", (1,))
                raise RuntimeError("abort")
        assert len(db.query("SELECT * FROM t")) == 0


class TestQueryBuilder:
    def test_simple_select(self):
        q = QueryBuilder("trades")
        sql, params = q.select("id", "symbol").build()
        assert "SELECT id, symbol FROM trades" in sql
        assert params == ()

    def test_where(self):
        q = QueryBuilder("trades")
        sql, params = q.select().where("status = ?", "CLOSED").build()
        assert "WHERE" in sql
        assert params == ("CLOSED",)

    def test_order_by(self):
        q = QueryBuilder("trades")
        sql, _ = q.order_by("ts DESC").build()
        assert "ORDER BY ts DESC" in sql

    def test_limit_offset(self):
        q = QueryBuilder("trades")
        sql, _ = q.limit(10).offset(20).build()
        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql

    def test_insert(self):
        q = QueryBuilder("trades")
        sql, params = q.insert(id=1, symbol="RELIANCE")
        assert "INSERT INTO trades" in sql
        assert 1 in params

    def test_update(self):
        q = QueryBuilder("trades")
        sql, params = q.update("id", 1, status="CLOSED")
        assert "UPDATE trades SET" in sql
        assert "CLOSED" in params

    def test_delete(self):
        q = QueryBuilder("trades")
        sql, params = q.delete("id", 1)
        assert "DELETE FROM trades" in sql
        assert 1 in params


# ---------------------------------------------------------------------------
# MessageBroker
# ---------------------------------------------------------------------------

class TestMessageBroker:
    def setup_method(self):
        reset_message_broker()

    def teardown_method(self):
        reset_message_broker()

    def test_publish_and_subscribe(self):
        broker = get_message_broker()
        received = []
        broker.subscribe("orders", lambda m: received.append(m.body))
        broker.publish("orders", {"qty": 10})
        assert received == [{"qty": 10}]

    def test_unsubscribe(self):
        broker = get_message_broker()
        received = []
        handler = lambda m: received.append(1)
        broker.subscribe("orders", handler)
        broker.unsubscribe("orders", handler)
        broker.publish("orders", None)
        assert received == []

    def test_multiple_subscribers(self):
        broker = get_message_broker()
        a, b = [], []
        broker.subscribe("x", lambda m: a.append(1))
        broker.subscribe("x", lambda m: b.append(1))
        broker.publish("x", None)
        assert a == [1] and b == [1]

    def test_singleton(self):
        b1 = get_message_broker()
        b2 = get_message_broker()
        assert b1 is b2


class TestMessageQueue:
    def test_publish_consume(self):
        mq = MessageQueue()
        msg = Message(topic="orders", body={"qty": 5})
        mq.publish("orders", msg)
        out = mq.consume("orders")
        assert out is not None
        assert out.body == {"qty": 5}

    def test_consume_empty_returns_none(self):
        mq = MessageQueue()
        assert mq.consume("empty_topic", timeout=0.01) is None

    def test_pending(self):
        mq = MessageQueue()
        mq.publish("x", Message(topic="x", body=None))
        mq.publish("x", Message(topic="x", body=None))
        assert mq.pending("x") == 2

    def test_topics(self):
        mq = MessageQueue()
        mq.publish("a", Message(topic="a", body=None))
        mq.publish("b", Message(topic="b", body=None))
        assert "a" in mq.topics() and "b" in mq.topics()
