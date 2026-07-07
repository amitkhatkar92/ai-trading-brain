"""
iios/knowledge/search/query_parser.py
========================================
Parses raw query strings into structured ParsedQuery objects.

Supported syntax:
  • Boolean operators  : NIFTY AND trend  |  NIFTY OR signal  |  equity NOT bearish
  • Quoted phrases     : "NIFTY 50 trend"
  • Wildcard prefix    : *trend* or trend*
  • Field qualifiers   : title:NIFTY  tag:equity  domain:equity  type:fact
  • Bare tokens        : nifty 50 analysis  (treated as OR by default)
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Optional

from .search_constants import SearchQueryOp, MIN_TOKEN_LENGTH

__all__ = ["ParsedQuery", "QueryParser", "get_query_parser", "reset_query_parser"]

_WORD_RE    = re.compile(r"[a-z0-9_]+")
_PHRASE_RE  = re.compile(r'"([^"]+)"')
_FIELD_RE   = re.compile(r"(\w+):(\S+)")
_WILDCARD_RE = re.compile(r"\*\S+\*|\S+\*|\*\S+")

_lock:   threading.Lock            = threading.Lock()
_parser: Optional["QueryParser"]   = None


@dataclass
class ParsedQuery:
    """Structured result of parsing a raw query string."""
    raw_text:    str                    = ""
    tokens:      list[str]             = field(default_factory=list)
    required:    list[str]             = field(default_factory=list)   # AND operands
    optional:    list[str]             = field(default_factory=list)   # OR operands
    excluded:    list[str]             = field(default_factory=list)   # NOT operands
    phrases:     list[str]             = field(default_factory=list)   # "quoted phrases"
    wildcards:   list[str]             = field(default_factory=list)   # *wild* patterns
    field_terms: dict[str, list[str]]  = field(default_factory=dict)  # field→[values]
    operator:    SearchQueryOp         = SearchQueryOp.OR

    @property
    def is_empty(self) -> bool:
        return (
            not self.tokens and not self.phrases and
            not self.wildcards and not self.field_terms
        )

    @property
    def effective_tokens(self) -> list[str]:
        """All non-excluded tokens for matching."""
        return [t for t in self.tokens if t not in self.excluded]

    def to_dict(self) -> dict:
        return {
            "raw_text":   self.raw_text,
            "tokens":     self.tokens,
            "required":   self.required,
            "optional":   self.optional,
            "excluded":   self.excluded,
            "phrases":    self.phrases,
            "wildcards":  self.wildcards,
            "field_terms": self.field_terms,
            "operator":   self.operator.value,
        }


class QueryParser:
    """
    Parses query strings into ParsedQuery.

    Handles AND / OR / NOT boolean operators, quoted phrases,
    wildcard patterns, and field qualifiers.

    Usage::

        parser = get_query_parser()
        pq = parser.parse('title:NIFTY AND "50 trend" NOT bearish equity*')
    """

    def parse(self, text: str) -> ParsedQuery:
        if not text or not text.strip():
            return ParsedQuery(raw_text=text)

        pq = ParsedQuery(raw_text=text)

        # ── Extract quoted phrases first ──────────────────────────────────────
        working = text
        for m in _PHRASE_RE.finditer(text):
            pq.phrases.append(m.group(1).strip())
        working = _PHRASE_RE.sub("", working)

        # ── Extract field qualifiers ──────────────────────────────────────────
        for m in _FIELD_RE.finditer(working):
            field_name = m.group(1).lower()
            field_val  = m.group(2).lower()
            pq.field_terms.setdefault(field_name, []).append(field_val)
        working = _FIELD_RE.sub("", working)

        # ── Extract wildcards ─────────────────────────────────────────────────
        for m in _WILDCARD_RE.finditer(working):
            pq.wildcards.append(m.group(0).lower())
        working = _WILDCARD_RE.sub("", working)

        # ── Tokenise remaining text, respecting AND / OR / NOT ────────────────
        parts = working.split()
        skip_next = False
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            upper = part.upper()

            if upper == "AND":
                pq.operator = SearchQueryOp.AND
                i += 1
                continue
            if upper == "OR":
                pq.operator = SearchQueryOp.OR
                i += 1
                continue
            if upper == "NOT":
                # The next token is excluded
                if i + 1 < len(parts):
                    excl = parts[i + 1].lower()
                    tokens = _WORD_RE.findall(excl)
                    pq.excluded.extend(
                        [t for t in tokens if len(t) >= MIN_TOKEN_LENGTH]
                    )
                    i += 2
                    continue
            # Regular token
            toks = _WORD_RE.findall(part.lower())
            for tok in toks:
                if len(tok) >= MIN_TOKEN_LENGTH:
                    pq.tokens.append(tok)
            i += 1

        # ── Determine required vs optional ────────────────────────────────────
        if pq.operator == SearchQueryOp.AND:
            pq.required = [t for t in pq.tokens if t not in pq.excluded]
            pq.optional = []
        else:
            pq.optional  = [t for t in pq.tokens if t not in pq.excluded]
            pq.required  = []

        # Deduplicate while preserving order
        pq.tokens   = list(dict.fromkeys(pq.tokens))
        pq.required = list(dict.fromkeys(pq.required))
        pq.optional = list(dict.fromkeys(pq.optional))
        pq.excluded = list(dict.fromkeys(pq.excluded))

        return pq


def get_query_parser() -> QueryParser:
    global _parser
    with _lock:
        if _parser is None:
            _parser = QueryParser()
        return _parser


def reset_query_parser() -> None:
    global _parser
    with _lock:
        _parser = None
