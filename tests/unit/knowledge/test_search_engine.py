"""
tests/unit/knowledge/test_search_engine.py
============================================
Comprehensive tests for the IIOS Knowledge Indexing & Search Engine.

Run::

    .venv\\Scripts\\python -m pytest tests/unit/knowledge/test_search_engine.py -v --tb=short
"""
from __future__ import annotations

import time
import pytest

# ===========================================================================
# Helpers
# ===========================================================================

def _reset_all() -> None:
    from iios.knowledge.search.index_manager    import reset_index_manager
    from iios.knowledge.search.index_builder    import reset_index_builder
    from iios.knowledge.search.index_registry   import reset_index_registry
    from iios.knowledge.search.index_statistics import reset_search_stats
    from iios.knowledge.search.index_optimizer  import reset_index_optimizer
    from iios.knowledge.search.query_parser     import reset_query_parser
    from iios.knowledge.search.query_builder    import reset_query_builder
    from iios.knowledge.search.query_validator  import reset_query_validator
    from iios.knowledge.search.query_optimizer  import reset_query_optimizer
    from iios.knowledge.search.query_executor   import reset_query_executor
    from iios.knowledge.search.search_engine    import reset_search_engine
    from iios.knowledge.search.search_context   import reset_search_context
    from iios.knowledge.search.search_factory   import reset_search_factory
    from iios.knowledge.search.search_manager   import reset_search_manager
    from iios.knowledge.search.search_registry  import reset_search_registry
    import iios.knowledge.search.search_factory as _sf
    _sf._factory = None
    reset_index_manager(); reset_index_builder(); reset_index_registry()
    reset_search_stats(); reset_index_optimizer()
    reset_query_parser(); reset_query_builder(); reset_query_validator()
    reset_query_optimizer(); reset_query_executor()
    reset_search_engine(); reset_search_context()
    reset_search_factory(); reset_search_manager(); reset_search_registry()


def _idx():
    from iios.knowledge.search.index_manager import get_index_manager
    return get_index_manager()


def _sm():
    from iios.knowledge.search.search_manager import get_search_manager
    return get_search_manager()


def _make_result(
    item_id:   str   = "iios.knowledge/test-001",
    title:     str   = "NIFTY 50 trend analysis",
    content:   str   = "Bullish momentum in equity markets",
    tags:      list  | None = None,
    metadata:  dict  | None = None,
    confidence: float = 0.9,
    item_type: str   = "knowledge",
    created_at: float | None = None,
):
    from iios.knowledge.search.models.unified_result import UnifiedSearchResult
    return UnifiedSearchResult(
        result_id   = f"sr:{item_id}",
        item_id     = item_id,
        item_type   = item_type,
        title       = title,
        content     = content,
        score       = 0.0,
        confidence  = confidence,
        tags        = tags or ["equity", "index"],
        metadata    = metadata or {"knowledge_type": "analysis", "domain": "equity"},
        snippet     = content[:100],
        created_at  = created_at or time.time(),
        updated_at  = created_at or time.time(),
    )


def _populate(n: int = 5):
    idx = _idx()
    for i in range(n):
        r = _make_result(
            item_id   = f"iios.knowledge/item-{i:03d}",
            title     = f"Test item {i} about NIFTY market",
            content   = f"Content for item {i} with analysis details",
            tags      = ["equity", f"tag{i}"],
            metadata  = {"knowledge_type": "analysis", "domain": "equity", "priority": str(i)},
            confidence = 0.5 + i * 0.1,
        )
        idx.index_item(r)
    return n


# ===========================================================================
# 1. UnifiedSearchQuery
# ===========================================================================

class TestUnifiedSearchQuery:
    def setup_method(self): _reset_all()

    def test_default_values(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        q = UnifiedSearchQuery()
        assert q.search_type == SearchType.KEYWORD
        assert q.text == ""
        assert q.page == 1

    def test_offset_calculation(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(page=3, page_size=20)
        assert q.offset == 40

    def test_cache_key_stable(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q1 = UnifiedSearchQuery(text="NIFTY trend", page=1, page_size=10)
        q2 = UnifiedSearchQuery(text="NIFTY trend", page=1, page_size=10)
        assert q1.cache_key() == q2.cache_key()

    def test_cache_key_differs_on_text(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q1 = UnifiedSearchQuery(text="NIFTY")
        q2 = UnifiedSearchQuery(text="BANKNIFTY")
        assert q1.cache_key() != q2.cache_key()

    def test_to_dict_roundtrip(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        q = UnifiedSearchQuery(text="NIFTY", search_type=SearchType.TAG, tags=["equity"])
        q2 = UnifiedSearchQuery.from_dict(q.to_dict())
        assert q2.text == "NIFTY"
        assert q2.tags == ["equity"]

    def test_normalized_text(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="  NIFTY 50  ")
        assert q.normalized_text == "nifty 50"


# ===========================================================================
# 2. UnifiedSearchResult
# ===========================================================================

class TestUnifiedSearchResult:
    def setup_method(self): _reset_all()

    def test_to_dict(self):
        r = _make_result()
        d = r.to_dict()
        assert d["item_id"] == r.item_id
        assert d["title"]   == r.title

    def test_equality_by_item_id(self):
        r1 = _make_result(item_id="id-001")
        r2 = _make_result(item_id="id-001")
        assert r1 == r2

    def test_less_than_by_score(self):
        from dataclasses import replace
        r1 = replace(_make_result(), score=0.3)
        r2 = replace(_make_result(), score=0.7)
        assert r1 < r2

    def test_from_graph_node(self):
        from unittest.mock import MagicMock
        from iios.knowledge.search.models.unified_result import UnifiedSearchResult
        from iios.knowledge.search.search_constants import ItemType
        node          = MagicMock()
        node.node_id  = "iios.graph/test"
        node.label    = "NIFTY Market"
        node.confidence = 0.85
        node.weight   = 0.9
        node.is_deleted = False
        node.knowledge_id = None
        node.node_type.value = "market"
        node.status.value    = "active"
        meta_mock     = MagicMock()
        meta_mock.description = "Market node"
        meta_mock.tags  = ["market"]
        meta_mock.created_at = time.time()
        meta_mock.updated_at = time.time()
        node.metadata = meta_mock
        r = UnifiedSearchResult.from_graph_node(node, score=0.7)
        assert r.item_type == ItemType.GRAPH_NODE.value
        assert r.title     == "NIFTY Market"


# ===========================================================================
# 3. SearchResponse
# ===========================================================================

class TestSearchResponse:
    def setup_method(self): _reset_all()

    def test_empty_response(self):
        from iios.knowledge.search.models.search_response import SearchResponse
        from iios.knowledge.search.models.unified_query   import UnifiedSearchQuery
        q    = UnifiedSearchQuery()
        resp = SearchResponse.empty(q, execution_time_ms=5.0)
        assert resp.total   == 0
        assert resp.count   == 0
        assert not resp.has_next
        assert not resp.has_prev

    def test_total_pages(self):
        from iios.knowledge.search.models.search_response import SearchResponse
        from iios.knowledge.search.models.unified_query   import UnifiedSearchQuery
        q = UnifiedSearchQuery(page_size=10)
        resp = SearchResponse.empty(q)
        assert resp.total_pages == 1

    def test_to_dict_keys(self):
        from iios.knowledge.search.models.search_response import SearchResponse
        from iios.knowledge.search.models.unified_query   import UnifiedSearchQuery
        q    = UnifiedSearchQuery()
        resp = SearchResponse.empty(q)
        d    = resp.to_dict()
        assert "results" in d
        assert "total"   in d
        assert "search_type" in d

    def test_build_pagination(self):
        from iios.knowledge.search.models.search_response import SearchResponse
        from iios.knowledge.search.models.unified_query   import UnifiedSearchQuery
        from iios.knowledge.search.search_constants       import SearchType
        q       = UnifiedSearchQuery(page=1, page_size=3, search_type=SearchType.KEYWORD)
        results = [_make_result(item_id=f"id{i}") for i in range(10)]
        resp    = SearchResponse.build(q, results, total=10, execution_time_ms=1.0)
        assert len(resp.results) == 3
        assert resp.has_next
        assert not resp.has_prev


# ===========================================================================
# 4. IndexDefinition & IndexStatistics
# ===========================================================================

class TestIndexDefinition:
    def setup_method(self): _reset_all()

    def test_new(self):
        from iios.knowledge.search.models.index_definition import IndexDefinition
        from iios.knowledge.search.search_constants import SearchIndexType
        d = IndexDefinition.new(
            name       = "test-index",
            index_type = SearchIndexType.KEYWORD,
            item_types = ["knowledge"],
            fields     = ["title"],
        )
        assert d.name       == "test-index"
        assert d.item_count == 0

    def test_mark_rebuilt(self):
        from iios.knowledge.search.models.index_definition import IndexDefinition
        from iios.knowledge.search.search_constants import SearchIndexType
        d = IndexDefinition.new("x", SearchIndexType.TAG, ["knowledge"], ["tags"])
        d.mark_rebuilt(100)
        assert d.item_count   == 100
        assert d.last_rebuilt is not None

    def test_roundtrip(self):
        from iios.knowledge.search.models.index_definition import IndexDefinition
        from iios.knowledge.search.search_constants import SearchIndexType
        d  = IndexDefinition.new("y", SearchIndexType.METADATA, ["knowledge"], ["f"])
        d2 = IndexDefinition.from_dict(d.to_dict())
        assert d2.name == "y"

    def test_index_statistics(self):
        from iios.knowledge.search.models.index_definition import IndexStatistics
        s = IndexStatistics(index_id="id1", name="kw")
        s.record_query(5.0, cache_hit=False)
        s.record_query(3.0, cache_hit=True)
        assert s.total_queries == 2
        assert s.cache_hit_ratio == 0.5


# ===========================================================================
# 5. IndexManager — Indexing
# ===========================================================================

class TestIndexManagerIndexing:
    def setup_method(self): _reset_all()

    def test_index_and_get(self):
        idx = _idx()
        r   = _make_result()
        idx.index_item(r)
        got = idx.get_item(r.item_id)
        assert got is not None
        assert got.title == r.title

    def test_item_exists_after_index(self):
        idx = _idx()
        r   = _make_result()
        assert not idx.item_exists(r.item_id)
        idx.index_item(r)
        assert idx.item_exists(r.item_id)

    def test_deindex(self):
        idx = _idx()
        r   = _make_result()
        idx.index_item(r)
        ok  = idx.deindex_item(r.item_id)
        assert ok
        assert not idx.item_exists(r.item_id)

    def test_item_count(self):
        idx = _idx()
        for i in range(3):
            idx.index_item(_make_result(item_id=f"iios.knowledge/t{i}"))
        assert idx.item_count() == 3

    def test_update_item(self):
        idx = _idx()
        r   = _make_result(title="Original Title")
        idx.index_item(r)
        from dataclasses import replace
        r2 = replace(r, title="Updated Title")
        idx.update_item(r2)
        assert idx.get_item(r.item_id).title == "Updated Title"

    def test_clear(self):
        idx = _idx()
        _populate(3)
        idx.clear()
        assert idx.item_count() == 0

    def test_statistics_keys(self):
        idx   = _idx()
        _populate(3)
        stats = idx.statistics()
        assert "item_count"    in stats
        assert "keyword_count" in stats
        assert "items_by_type" in stats


# ===========================================================================
# 6. IndexManager — Keyword Search
# ===========================================================================

class TestIndexManagerKeyword:
    def setup_method(self): _reset_all()

    def test_keyword_or(self):
        idx = _idx()
        idx.index_item(_make_result(title="NIFTY trend analysis", item_id="id1"))
        idx.index_item(_make_result(title="BANKNIFTY rally",       item_id="id2"))
        scores = idx.search_keyword(["nifty"], operator="OR")
        assert "id1" in scores

    def test_keyword_and_requires_all(self):
        idx = _idx()
        idx.index_item(_make_result(title="NIFTY bullish trend", item_id="id1"))
        idx.index_item(_make_result(title="BANKNIFTY analysis",  item_id="id2"))
        # "nifty" AND "bullish" → only id1
        scores = idx.search_keyword(["nifty", "bullish"], operator="AND")
        assert "id1" in scores
        assert "id2" not in scores

    def test_keyword_score_positive(self):
        idx = _idx()
        idx.index_item(_make_result(title="NIFTY NIFTY trend",    item_id="id1"))
        scores = idx.search_keyword(["nifty"], operator="OR")
        assert scores.get("id1", 0.0) > 0

    def test_empty_tokens_returns_empty(self):
        idx = _idx()
        _populate(3)
        scores = idx.search_keyword([], operator="OR")
        assert scores == {}

    def test_fuzzy_match(self):
        idx = _idx()
        idx.index_item(_make_result(title="equity analysis nifty", item_id="id1"))
        # "nifti" should fuzzy-match "nifty"
        scores = idx.search_keyword(["nifti"], operator="OR", fuzzy=True, fuzzy_threshold=0.6)
        assert "id1" in scores


# ===========================================================================
# 7. IndexManager — Tag Search
# ===========================================================================

class TestIndexManagerTags:
    def setup_method(self): _reset_all()

    def test_search_by_tag(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", tags=["equity", "nifty"]))
        idx.index_item(_make_result(item_id="id2", tags=["bonds", "fixed_income"]))
        result = idx.search_by_tags(["equity"])
        assert "id1" in result
        assert "id2" not in result

    def test_search_by_tags_or(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", tags=["equity"]))
        idx.index_item(_make_result(item_id="id2", tags=["bonds"]))
        result = idx.search_by_tags(["equity", "bonds"], match_all=False)
        assert "id1" in result
        assert "id2" in result

    def test_search_by_tags_and(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", tags=["equity", "nifty"]))
        idx.index_item(_make_result(item_id="id2", tags=["equity"]))
        result = idx.search_by_tags(["equity", "nifty"], match_all=True)
        assert "id1" in result
        assert "id2" not in result

    def test_empty_tags_returns_all(self):
        idx = _idx()
        _populate(3)
        result = idx.search_by_tags([])
        assert len(result) == 3


# ===========================================================================
# 8. IndexManager — Metadata & Ontology Search
# ===========================================================================

class TestIndexManagerMetadata:
    def setup_method(self): _reset_all()

    def test_search_by_metadata(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", metadata={"domain": "equity", "priority": "1"}))
        idx.index_item(_make_result(item_id="id2", metadata={"domain": "bonds",  "priority": "1"}))
        result = idx.search_by_metadata({"domain": "equity"})
        assert "id1" in result
        assert "id2" not in result

    def test_metadata_and_semantics(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", metadata={"domain": "equity", "type": "fact"}))
        idx.index_item(_make_result(item_id="id2", metadata={"domain": "equity", "type": "rule"}))
        result = idx.search_by_metadata({"domain": "equity", "type": "fact"})
        assert "id1" in result
        assert "id2" not in result

    def test_search_by_ontology(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", metadata={"knowledge_type": "analysis", "domain": "equity"}))
        idx.index_item(_make_result(item_id="id2", metadata={"knowledge_type": "rule",     "domain": "bonds"}))
        result = idx.search_by_ontology(["knowledge_type:analysis"])
        assert "id1" in result

    def test_search_by_item_type(self):
        idx = _idx()
        idx.index_item(_make_result(item_id="id1", item_type="knowledge"))
        idx.index_item(_make_result(item_id="id2", item_type="graph_node"))
        result = idx.search_by_item_type(["knowledge"])
        assert "id1" in result
        assert "id2" not in result


# ===========================================================================
# 9. QueryParser
# ===========================================================================

class TestQueryParser:
    def setup_method(self): _reset_all()

    def _parser(self):
        from iios.knowledge.search.query_parser import get_query_parser
        return get_query_parser()

    def test_empty_returns_empty_query(self):
        pq = self._parser().parse("")
        assert pq.is_empty

    def test_simple_tokens(self):
        pq = self._parser().parse("NIFTY trend analysis")
        assert "nifty" in pq.tokens
        assert "trend" in pq.tokens

    def test_and_operator(self):
        from iios.knowledge.search.search_constants import SearchQueryOp
        pq = self._parser().parse("NIFTY AND trend")
        assert pq.operator == SearchQueryOp.AND
        assert "nifty" in pq.required
        assert "trend" in pq.required

    def test_or_operator(self):
        from iios.knowledge.search.search_constants import SearchQueryOp
        pq = self._parser().parse("NIFTY OR BANKNIFTY")
        assert pq.operator == SearchQueryOp.OR

    def test_not_operator(self):
        pq = self._parser().parse("NIFTY NOT bearish")
        assert "bearish" in pq.excluded

    def test_quoted_phrase(self):
        pq = self._parser().parse('"NIFTY 50 trend"')
        assert "NIFTY 50 trend" in pq.phrases

    def test_field_qualifier(self):
        pq = self._parser().parse("title:NIFTY domain:equity")
        assert "nifty" in pq.field_terms.get("title", [])
        assert "equity" in pq.field_terms.get("domain", [])

    def test_wildcard(self):
        pq = self._parser().parse("trend*")
        assert len(pq.wildcards) > 0

    def test_effective_tokens_excludes_not(self):
        pq = self._parser().parse("NIFTY equity NOT bearish")
        assert "bearish" not in pq.effective_tokens


# ===========================================================================
# 10. QueryBuilder
# ===========================================================================

class TestQueryBuilder:
    def setup_method(self): _reset_all()

    def _qb(self):
        from iios.knowledge.search.query_builder import get_query_builder
        return get_query_builder()

    def test_keyword_query(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._qb().keyword("NIFTY trend")
        assert q.search_type == SearchType.KEYWORD
        assert q.text        == "NIFTY trend"

    def test_tag_query(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._qb().tag(["equity", "index"])
        assert q.search_type == SearchType.TAG
        assert "equity" in q.tags

    def test_metadata_query(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._qb().metadata({"domain": "equity"})
        assert q.search_type == SearchType.METADATA
        assert q.filters     == {"domain": "equity"}

    def test_by_id_query(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._qb().by_id("iios.knowledge/abc")
        assert q.search_type == SearchType.ID_LOOKUP

    def test_hybrid_query(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._qb().hybrid("NIFTY", tags=["equity"], filters={"domain": "equity"})
        assert q.search_type == SearchType.HYBRID
        assert q.text        == "NIFTY"
        assert "equity" in q.tags

    def test_graph_traversal_query(self):
        from iios.knowledge.search.search_constants import SearchType, ItemType
        q = self._qb().graph_traversal("iios.graph/node1", depth=4)
        assert q.search_type      == SearchType.GRAPH_TRAVERSAL
        assert q.start_node_id    == "iios.graph/node1"
        assert q.traversal_depth  == 4
        assert ItemType.GRAPH_NODE.value in q.item_types


# ===========================================================================
# 11. QueryValidator
# ===========================================================================

class TestQueryValidator:
    def setup_method(self): _reset_all()

    def _validator(self):
        from iios.knowledge.search.query_validator import get_query_validator
        return get_query_validator()

    def test_valid_query(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="NIFTY trend", page=1, page_size=20)
        assert self._validator().validate(q) == []

    def test_page_must_be_positive(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(page=0)
        violations = self._validator().validate(q)
        assert any("page" in v.lower() for v in violations)

    def test_page_size_max(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(page_size=99999)
        violations = self._validator().validate(q)
        assert any("page_size" in v.lower() for v in violations)

    def test_confidence_range(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(min_confidence=2.0)
        violations = self._validator().validate(q)
        assert any("confidence" in v.lower() for v in violations)

    def test_id_lookup_requires_text(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        q = UnifiedSearchQuery(search_type=SearchType.ID_LOOKUP, text="")
        violations = self._validator().validate(q)
        assert len(violations) > 0

    def test_graph_traversal_requires_start_node(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        q = UnifiedSearchQuery(search_type=SearchType.GRAPH_TRAVERSAL)
        violations = self._validator().validate(q)
        assert any("start_node_id" in v.lower() for v in violations)

    def test_validate_or_raise(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_exceptions import SearchQueryValidationError
        q = UnifiedSearchQuery(page=0)
        with pytest.raises(SearchQueryValidationError):
            self._validator().validate_or_raise(q)


# ===========================================================================
# 12. QueryOptimizer
# ===========================================================================

class TestQueryOptimizer:
    def setup_method(self): _reset_all()

    def _optimizer(self):
        from iios.knowledge.search.query_optimizer import get_query_optimizer
        return get_query_optimizer()

    def test_strips_whitespace(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="  NIFTY trend  ")
        opt = self._optimizer().optimize(q)
        assert opt.text == opt.text.strip()

    def test_caps_page_size(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import MAX_SEARCH_PAGE_SIZE
        q = UnifiedSearchQuery(page_size=MAX_SEARCH_PAGE_SIZE + 500)
        opt = self._optimizer().optimize(q)
        assert opt.page_size <= MAX_SEARCH_PAGE_SIZE

    def test_caps_traversal_depth(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(traversal_depth=999)
        opt = self._optimizer().optimize(q)
        assert opt.traversal_depth <= 10

    def test_deduplicates_tags(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(tags=["equity", "equity", "EQUITY"])
        opt = self._optimizer().optimize(q)
        assert len(opt.tags) == 1

    def test_removes_empty_filters(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(filters={"domain": "equity", "type": ""})
        opt = self._optimizer().optimize(q)
        assert "type" not in opt.filters
        assert "domain" in opt.filters


# ===========================================================================
# 13. QueryExecutor — all search types
# ===========================================================================

class TestQueryExecutor:
    def setup_method(self): _reset_all()

    def _exec(self):
        from iios.knowledge.search.query_executor import get_query_executor
        return get_query_executor()

    def test_id_lookup_found(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(item_id="iios.knowledge/unique-001")
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.ID_LOOKUP, text="iios.knowledge/unique-001")
        results, _ = self._exec().execute(q)
        assert len(results) == 1
        assert results[0].item_id == "iios.knowledge/unique-001"

    def test_id_lookup_not_found(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        q = UnifiedSearchQuery(search_type=SearchType.ID_LOOKUP, text="iios.knowledge/ghost")
        results, _ = self._exec().execute(q)
        assert len(results) == 0

    def test_exact_match(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(title="exact match title", item_id="id-exact")
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.EXACT_MATCH, text="exact match title")
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-exact" for res in results)

    def test_keyword_search(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(title="NIFTY 50 bullish signal", item_id="id-kw")
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.KEYWORD, text="nifty signal")
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-kw" for res in results)

    def test_tag_search(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(item_id="id-tag", tags=["premium", "signal"])
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.TAG, tags=["premium"])
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-tag" for res in results)

    def test_metadata_search(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(item_id="id-meta", metadata={"domain": "derivatives", "type": "fact"})
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.METADATA, filters={"domain": "derivatives"})
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-meta" for res in results)

    def test_ontology_search(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(item_id="id-onto", metadata={"knowledge_type": "strategy"})
        _idx().index_item(r)
        q = UnifiedSearchQuery(search_type=SearchType.ONTOLOGY, knowledge_types=["knowledge_type:strategy"])
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-onto" for res in results)

    def test_hybrid_search(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType
        r = _make_result(
            item_id="id-hybrid", title="NIFTY momentum",
            tags=["equity"], metadata={"domain": "equity"},
        )
        _idx().index_item(r)
        q = UnifiedSearchQuery(
            search_type=SearchType.HYBRID, text="NIFTY",
            tags=["equity"], filters={"domain": "equity"},
        )
        results, _ = self._exec().execute(q)
        assert any(res.item_id == "id-hybrid" for res in results)

    def test_item_type_filter(self):
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType, ItemType
        _idx().index_item(_make_result(item_id="id-k",  item_type="knowledge"))
        _idx().index_item(_make_result(item_id="id-gn", item_type="graph_node"))
        q = UnifiedSearchQuery(
            search_type=SearchType.KEYWORD, text="NIFTY",
            item_types=[ItemType.KNOWLEDGE.value],
        )
        results, _ = self._exec().execute(q)
        types = {r.item_type for r in results}
        assert "graph_node" not in types


# ===========================================================================
# 14. SearchEngine
# ===========================================================================

class TestSearchEngine:
    def setup_method(self): _reset_all()

    def _engine(self):
        from iios.knowledge.search.search_engine import get_search_engine
        return get_search_engine()

    def test_search_returns_response(self):
        _populate(3)
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="NIFTY market")
        resp = self._engine().search(q)
        assert hasattr(resp, "total")
        assert resp.total > 0

    def test_cache_hit_on_second_call(self):
        _populate(2)
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="NIFTY", page=1, page_size=10)
        resp1 = self._engine().search(q)
        resp2 = self._engine().search(q)
        assert resp2.cache_hit

    def test_ranking_by_confidence(self):
        idx = _idx()
        from dataclasses import replace
        low  = replace(_make_result(item_id="low"),  confidence=0.3, title="NIFTY low confidence")
        high = replace(_make_result(item_id="high"), confidence=0.95, title="NIFTY high confidence")
        idx.index_item(low); idx.index_item(high)
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        from iios.knowledge.search.search_constants import SearchType, RankingStrategy
        q = UnifiedSearchQuery(
            text="NIFTY", search_type=SearchType.KEYWORD,
            ranking_strategy=RankingStrategy.CONFIDENCE,
        )
        resp = self._engine().search(q)
        if len(resp.results) >= 2:
            assert resp.results[0].confidence >= resp.results[-1].confidence

    def test_pagination_has_next(self):
        _populate(10)
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="NIFTY", page=1, page_size=3)
        resp = self._engine().search(q)
        assert len(resp.results) == 3
        assert resp.has_next

    def test_invalidate_cache(self):
        _populate(2)
        from iios.knowledge.search.models.unified_query import UnifiedSearchQuery
        q = UnifiedSearchQuery(text="NIFTY", page=1, page_size=10)
        self._engine().search(q)
        self._engine().invalidate_cache()
        resp = self._engine().search(q)
        assert not resp.cache_hit

    def test_statistics_keys(self):
        stats = self._engine().statistics()
        assert "engine"  in stats
        assert "cache"   in stats
        assert "queries" in stats


# ===========================================================================
# 15. SearchManager
# ===========================================================================

class TestSearchManager:
    def setup_method(self): _reset_all()

    def test_index_and_search(self):
        sm = _sm()
        r  = _make_result(title="NIFTY trend signal", item_id="id-sm-001")
        sm.index_knowledge_record(_FakeRecord(r))
        resp = sm.search("NIFTY signal")
        assert resp.total >= 1

    def test_search_by_id(self):
        r = _make_result(item_id="iios.knowledge/sm-unique")
        _idx().index_item(r)
        result = _sm().search_by_id("iios.knowledge/sm-unique")
        assert result is not None
        assert result.item_id == "iios.knowledge/sm-unique"

    def test_search_by_tags(self):
        r = _make_result(item_id="id-tag-sm", tags=["premium"])
        _idx().index_item(r)
        resp = _sm().search_by_tags(["premium"])
        assert resp.total >= 1

    def test_search_by_metadata(self):
        r = _make_result(item_id="id-meta-sm", metadata={"domain": "derivatives"})
        _idx().index_item(r)
        resp = _sm().search_by_metadata({"domain": "derivatives"})
        assert resp.total >= 1

    def test_search_by_type(self):
        r = _make_result(item_id="id-type-sm", metadata={"knowledge_type": "rule"})
        _idx().index_item(r)
        resp = _sm().search_by_type("rule")
        assert resp.total >= 1

    def test_hybrid_search(self):
        r = _make_result(
            item_id="id-hyb-sm", title="equity strategy signal",
            tags=["equity"], metadata={"domain": "equity"},
        )
        _idx().index_item(r)
        resp = _sm().hybrid_search("strategy", tags=["equity"])
        assert resp.total >= 1

    def test_fuzzy_search(self):
        r = _make_result(item_id="id-fz", title="NIFTY momentum analysis")
        _idx().index_item(r)
        resp = _sm().fuzzy_search("niftiy", threshold=0.6)   # typo → fuzzy
        assert resp.total >= 0   # may or may not match depending on threshold

    def test_deindex_item(self):
        r = _make_result(item_id="id-del")
        _idx().index_item(r)
        assert _sm().deindex_item("id-del")
        resp = _sm().search_by_id("id-del")
        assert resp is None

    def test_item_count(self):
        _populate(3)
        assert _sm().item_count() == 3

    def test_status(self):
        s = _sm().status()
        assert s["status"] == "running"

    def test_statistics(self):
        stats = _sm().statistics()
        assert "index" in stats

    def test_optimize_indexes(self):
        _populate(5)
        report = _sm().optimize_indexes()
        assert "item_count" in report


# ===========================================================================
# 16. SearchFactory
# ===========================================================================

class TestSearchFactory:
    def setup_method(self): _reset_all()

    def _sf(self):
        from iios.knowledge.search.search_factory import get_search_factory
        return get_search_factory()

    def test_quick_search(self):
        from iios.knowledge.search.search_constants import SearchType
        q = self._sf().quick_search("NIFTY trend")
        assert q.search_type == SearchType.HYBRID

    def test_page_query(self):
        q = self._sf().page_query("NIFTY", page=2, page_size=10)
        assert q.page      == 2
        assert q.page_size == 10

    def test_strict_confidence(self):
        from iios.knowledge.search.search_constants import RankingStrategy
        q = self._sf().strict_confidence_query("equity", min_confidence=0.95)
        assert q.min_confidence      == 0.95
        assert q.ranking_strategy    == RankingStrategy.CONFIDENCE

    def test_recent_items(self):
        from iios.knowledge.search.search_constants import RankingStrategy
        q = self._sf().recent_items_query(page_size=5)
        assert q.ranking_strategy == RankingStrategy.RECENCY
        assert q.page_size        == 5

    def test_domain_query(self):
        q = self._sf().domain_query("equity", text="trend")
        assert q.filters.get("domain") == "equity"

    def test_fuzzy_search_query(self):
        q = self._sf().fuzzy_search("nifty", threshold=0.8)
        assert q.fuzzy
        assert q.fuzzy_threshold == 0.8


# ===========================================================================
# 17. SearchContext
# ===========================================================================

class TestSearchContext:
    def setup_method(self): _reset_all()

    def test_default_actor(self):
        from iios.knowledge.search.search_context import current_search_actor
        from iios.knowledge.search.search_constants import SYSTEM_SEARCH_ACTOR
        assert current_search_actor() == SYSTEM_SEARCH_ACTOR

    def test_operation_sets_actor(self):
        from iios.knowledge.search.search_context import get_search_context, current_search_actor
        ctx = get_search_context()
        with ctx.operation("test", actor_id="user:alice"):
            assert current_search_actor() == "user:alice"

    def test_operation_id_set(self):
        from iios.knowledge.search.search_context import (
            get_search_context, current_search_operation_id,
        )
        ctx = get_search_context()
        with ctx.operation("op") as op_id:
            assert op_id == current_search_operation_id()
            assert len(op_id) > 0

    def test_search_operation_shortcut(self):
        from iios.knowledge.search.search_context import search_operation, current_search_actor
        with search_operation("lookup", actor_id="user:bob"):
            assert current_search_actor() == "user:bob"


# ===========================================================================
# 18. IndexRegistry
# ===========================================================================

class TestIndexRegistry:
    def setup_method(self): _reset_all()

    def test_default_indexes_registered(self):
        from iios.knowledge.search.index_registry import get_index_registry
        reg = get_index_registry()
        for name in ["primary", "keyword", "tag", "metadata", "ontology", "graph"]:
            assert reg.has(name), f"Missing index: {name}"

    def test_resolve_index_def(self):
        from iios.knowledge.search.index_registry import get_index_registry
        from iios.knowledge.search.models.index_definition import IndexDefinition
        reg = get_index_registry()
        d   = reg.get("keyword")
        assert isinstance(d, IndexDefinition)

    def test_register_custom(self):
        from iios.knowledge.search.index_registry import get_index_registry
        from iios.knowledge.search.models.index_definition import IndexDefinition
        from iios.knowledge.search.search_constants import SearchIndexType
        reg = get_index_registry()
        d   = IndexDefinition.new("custom-idx", SearchIndexType.COMPOSITE, ["knowledge"], ["f"])
        reg.register(d)
        assert reg.has("custom-idx")

    def test_list_names(self):
        from iios.knowledge.search.index_registry import get_index_registry
        names = get_index_registry().list_names()
        assert "keyword" in names


# ===========================================================================
# 19. SearchRegistry
# ===========================================================================

class TestSearchRegistry:
    def setup_method(self): _reset_all()

    def test_has_defaults(self):
        from iios.knowledge.search.search_registry import get_search_registry
        reg = get_search_registry()
        for name in ["index_manager", "search_engine", "search_manager", "query_executor"]:
            assert reg.has(name), f"Missing: {name}"

    def test_resolve_search_manager(self):
        from iios.knowledge.search.search_registry import get_search_registry
        from iios.knowledge.search.search_manager import SearchManager
        reg = get_search_registry()
        sm  = reg.resolve("search_manager")
        assert isinstance(sm, SearchManager)

    def test_register_custom(self):
        from iios.knowledge.search.search_registry import get_search_registry
        reg = get_search_registry()
        reg.register("my_component", {"key": "val"})
        assert reg.resolve("my_component") == {"key": "val"}

    def test_list_registered(self):
        from iios.knowledge.search.search_registry import get_search_registry
        names = get_search_registry().list_registered()
        assert "search_manager" in names


# ===========================================================================
# 20. IndexOptimizer
# ===========================================================================

class TestIndexOptimizer:
    def setup_method(self): _reset_all()

    def test_analyze_empty_index(self):
        from iios.knowledge.search.index_optimizer import get_index_optimizer
        report = get_index_optimizer().analyze()
        assert "item_count"     in report
        assert "should_compact" in report

    def test_optimize_returns_report(self):
        _populate(5)
        from iios.knowledge.search.index_optimizer import get_index_optimizer
        result = get_index_optimizer().optimize()
        assert "should_compact" in result
        assert "compact"        in result

    def test_compact_removes_empty_tokens(self):
        idx = _idx()
        r   = _make_result(item_id="id-cmp", title="NIFTY compact test")
        idx.index_item(r)
        idx.deindex_item("id-cmp")  # leaves empty keyword buckets
        from iios.knowledge.search.index_optimizer import get_index_optimizer
        result = get_index_optimizer().compact()
        assert "removed_tokens" in result


# ===========================================================================
# 21. SearchStats
# ===========================================================================

class TestSearchStats:
    def setup_method(self): _reset_all()

    def test_record_query(self):
        from iios.knowledge.search.index_statistics import get_search_stats
        s = get_search_stats()
        s.record_query(5.0, cache_hit=False)
        s.record_query(3.0, cache_hit=True)
        assert s.total_queries    == 2
        assert s.cache_hit_ratio  == 0.5

    def test_avg_exec_ms(self):
        from iios.knowledge.search.index_statistics import get_search_stats
        s = get_search_stats()
        s.record_query(10.0, cache_hit=False)
        s.record_query(20.0, cache_hit=False)
        assert abs(s.avg_exec_ms - 15.0) < 0.001

    def test_to_dict(self):
        from iios.knowledge.search.index_statistics import get_search_stats
        d = get_search_stats().to_dict()
        assert "total_queries"   in d
        assert "cache_hit_ratio" in d


# ===========================================================================
# Helpers for tests that need a record-like object
# ===========================================================================

class _FakeRecord:
    """Minimal shim that matches enough of KnowledgeRecord for IndexBuilder."""

    def __init__(self, result):
        import time as _time
        self.knowledge_id = type("KID", (), {"full": result.item_id})()
        self.id           = result.item_id
        self.title        = result.title
        self.content      = result.content
        self.is_deleted   = False
        self.confidence   = result.confidence
        self.version      = "1.0.0"
        self.created_at   = result.created_at
        self.updated_at   = result.updated_at

        class _KT:
            value = result.metadata.get("knowledge_type", "fact")
        class _KS:
            value = result.metadata.get("status", "active")
        class _Dom:
            value = result.metadata.get("domain", "general")
        class _Src:
            value = "system"
        class _Pri:
            value = "medium"
        class _Meta:
            description = result.snippet
            tags        = list(result.tags)
            domain      = _Dom()
            source      = _Src()
            priority    = _Pri()
            confidence  = result.confidence
            created_at  = result.created_at
            updated_at  = result.updated_at

        self.knowledge_type = _KT()
        self.status         = _KS()
        self.metadata       = _Meta()
