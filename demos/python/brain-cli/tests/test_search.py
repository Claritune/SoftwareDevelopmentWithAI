from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from brain_cli.models import Note, SearchResult
from brain_cli.search import engine as engine_mod
from brain_cli.search.engine import SearchEngine, keyword_search


# ---------------------------------------------------------------------------
# Test doubles / fixtures
# ---------------------------------------------------------------------------
class FakeEmbeddings:
    """Deterministic, offline stand-in for ``OpenAIEmbeddings``.

    ``embed_query`` returns a vector chosen by substring-matching ``text``
    against ``mapping`` (first hit wins), falling back to ``default``.
    No network calls and no API key required.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.mapping: dict[str, list[float]] = {}
        self.default: list[float] = [1.0, 0.0, 0.0]

    def embed_query(self, text: str) -> list[float]:
        for key, vec in self.mapping.items():
            if key in text:
                return vec
        return self.default

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]


@pytest.fixture
def make_engine(tmp_path: Path):
    """Factory that builds a SearchEngine backed by a real (tmp) ChromaDB
    persistent client but with embeddings mocked out."""

    def _factory(
        mapping: dict[str, list[float]] | None = None,
        default: list[float] | None = None,
    ) -> SearchEngine:
        with patch.object(engine_mod, "OpenAIEmbeddings", FakeEmbeddings):
            eng = SearchEngine(tmp_path / "vault")
        fake: FakeEmbeddings = eng._embeddings  # type: ignore[assignment]
        if mapping is not None:
            fake.mapping = mapping
        if default is not None:
            fake.default = default
        return eng

    return _factory


# ---------------------------------------------------------------------------
# BUG 1 — keyword search is (also) implemented *inside* SearchEngine
# rules/search.md > Do NOT: "Implement keyword search inside the SearchEngine
# class (keep it as standalone function)".
# engine.py lines 73-95 define SearchEngine.keyword_search, duplicating the
# standalone keyword_search() (lines 12-32) verbatim.
# ---------------------------------------------------------------------------
def test_search_keyword_not_defined_on_engine_class() -> None:
    # The search rules forbid a keyword_search method on the class; it must
    # only exist as the module-level standalone function.
    assert "keyword_search" not in vars(SearchEngine), (
        "keyword_search must be a standalone function, not a SearchEngine "
        "method (rules/search.md forbids duplicating it inside the class)."
    )


# ---------------------------------------------------------------------------
# BUG 2 — semantic score can be negative (cosine space vs. `1 - distance`)
# The collection is created with cosine space (engine.py line 41), but the
# score is computed as `1.0 - distance` (line 120) which the rules describe as
# an *L2* formula. With cosine distance in [0, 2], opposite vectors give
# distance 2.0 -> score -1.0, i.e. a nonsensical out-of-range relevance score.
# ---------------------------------------------------------------------------
def test_search_semantic_score_never_negative(make_engine) -> None:
    eng = make_engine(
        mapping={
            "Aligned": [1.0, 0.0, 0.0],   # same direction as the query
            "Opposite": [-1.0, 0.0, 0.0],  # opposite direction -> cos dist 2.0
        },
        default=[1.0, 0.0, 0.0],           # query vector
    )
    eng.index_note(Note(id="a", title="Aligned note", content="alpha"))
    eng.index_note(Note(id="b", title="Opposite note", content="beta"))

    results = eng.semantic_search("query", limit=10)
    scores = {r.note_id: r.score for r in results}

    # A relevance score should stay within [0, 1]. The opposite vector yields
    # cosine distance 2.0, so `1 - distance` == -1.0.
    assert all(0.0 <= s <= 1.0 for s in scores.values()), (
        f"scores must be within [0, 1] but got {scores}"
    )


# ---------------------------------------------------------------------------
# BUG 3 — semantic_search crashes on non-positive limit
# n_results = min(limit, count) when count > 0 (engine.py line 104). With a
# populated collection and limit <= 0, n_results becomes 0/negative, which
# ChromaDB rejects with a TypeError instead of returning no results.
# ---------------------------------------------------------------------------
def test_search_semantic_limit_zero_returns_empty(make_engine) -> None:
    eng = make_engine()
    eng.index_note(Note(id="a", title="Note A", content="hello world"))

    # A limit of 0 should mean "no results", not a hard crash.
    assert eng.semantic_search("hello", limit=0) == []


# ---------------------------------------------------------------------------
# Sanity checks for the standalone keyword_search (expected to PASS) — included
# so the suite documents the currently-correct behaviour of the function that
# the class method wrongly duplicates.
# ---------------------------------------------------------------------------
def test_search_keyword_title_outranks_content() -> None:
    notes = [
        Note(id="c", title="Random", content="a python snippet"),
        Note(id="t", title="Python", content="unrelated body"),
    ]
    results = keyword_search("python", notes)
    assert [r.note_id for r in results] == ["t", "c"]
    assert results[0].score == 1.0
    assert results[1].score == 0.5


def test_search_keyword_respects_limit() -> None:
    notes = [Note(id=str(i), title=f"Python {i}") for i in range(5)]
    results = keyword_search("python", notes, limit=2)
    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
