from __future__ import annotations

from pathlib import Path

import pytest

from brain_cli.models import Note
from brain_cli.storage.store import NoteStore


@pytest.fixture
def store(tmp_path: Path) -> NoteStore:
    return NoteStore(tmp_path / "vault")


def _make(store: NoteStore, note_id: str, title: str, content: str = "") -> Note:
    return store.save(Note(id=note_id, title=title, content=content))


# ---------------------------------------------------------------------------
# find_unlinked_mentions
# ---------------------------------------------------------------------------
def test_find_unlinked_mentions_happy_path(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Learning Log", content="I love Python a lot.")

    result = store.find_unlinked_mentions("a")

    assert len(result) == 1
    mentioning_id, snippet = result[0]
    assert mentioning_id == "b"
    assert "Python" in snippet


def test_find_unlinked_mentions_whole_word_data_vs_database(store: NoteStore) -> None:
    _make(store, "a", "Data")
    _make(store, "b", "Learning Log", content="I run a Database every day.")

    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_whole_word_ai_vs_email(store: NoteStore) -> None:
    _make(store, "a", "AI")
    _make(store, "b", "Inbox", content="Please check your email inbox.")

    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_whole_word_positive(store: NoteStore) -> None:
    _make(store, "a", "AI")
    _make(store, "b", "Musings", content="I think AI is fascinating.")

    result = store.find_unlinked_mentions("a")
    assert [mid for mid, _ in result] == ["b"]


def test_find_unlinked_mentions_case_insensitive(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="i use PYTHON and python daily")

    result = store.find_unlinked_mentions("a")
    assert [mid for mid, _ in result] == ["b"]


def test_find_unlinked_mentions_self_excluded(store: NoteStore) -> None:
    _make(store, "a", "Python", content="Python is great, Python rules.")

    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_already_linked_suppressed(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="I love [[Python]] and Python.")

    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_ignores_match_inside_wikilink(store: NoteStore) -> None:
    _make(store, "a", "Python")
    # Only occurrence is inside a wikilink but to a *different* title,
    # so outgoing_links() won't suppress; the lookarounds must skip it.
    _make(store, "b", "Notes", content="See [[Python Guide]] for more.")

    # "Python Guide" != "Python" so it's not already linked, and the bare
    # "Python" inside [[...]] must be ignored by the lookarounds.
    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_missing_note_returns_empty(store: NoteStore) -> None:
    assert store.find_unlinked_mentions("does-not-exist") == []


def test_find_unlinked_mentions_empty_title_returns_empty(store: NoteStore) -> None:
    # Empty title cannot be matched meaningfully.
    _make(store, "a", "")
    _make(store, "b", "Notes", content="some text")

    assert store.find_unlinked_mentions("a") == []


def test_find_unlinked_mentions_snippet_capped(store: NoteStore) -> None:
    _make(store, "a", "Python")
    body = ("filler " * 100) + "Python" + (" filler" * 100)
    _make(store, "b", "Long", content=body)

    result = store.find_unlinked_mentions("a")
    assert len(result) == 1
    _mid, snippet = result[0]
    # ~200 char window plus at most two ellipsis characters.
    assert len(snippet) <= _snippet_cap()
    assert "Python" in snippet
    assert snippet.startswith("…") and snippet.endswith("…")
    assert "\n" not in snippet


def test_find_unlinked_mentions_regex_special_title(store: NoteStore) -> None:
    _make(store, "a", "Node.js")
    _make(store, "b", "Backend", content="We ship Node.js in prod.")
    _make(store, "c", "Decoy", content="This is NodeXjs, not the runtime.")

    result = store.find_unlinked_mentions("a")
    assert [mid for mid, _ in result] == ["b"]


def test_find_unlinked_mentions_sorted_by_mentioning_title(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "z", "Zebra Note", content="Python appears here.")
    _make(store, "m", "Alpha Note", content="Python appears here too.")

    result = store.find_unlinked_mentions("a")
    assert [mid for mid, _ in result] == ["m", "z"]  # Alpha before Zebra


# ---------------------------------------------------------------------------
# find_all_unlinked_mentions
# ---------------------------------------------------------------------------
def test_find_all_unlinked_mentions_grouping(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Rust")
    _make(store, "c", "Notes", content="I mix Python and Rust every day.")

    result = store.find_all_unlinked_mentions()

    assert set(result.keys()) == {"a", "b"}
    assert [mid for mid, _ in result["a"]] == ["c"]
    assert [mid for mid, _ in result["b"]] == ["c"]


def test_find_all_unlinked_mentions_empty(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Rust", content="No cross references here.")

    assert store.find_all_unlinked_mentions() == {}


# ---------------------------------------------------------------------------
# link_mention
# ---------------------------------------------------------------------------
def test_link_mention_roundtrip(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="I love Python.")

    assert store.find_unlinked_mentions("a") == [("b", "I love Python.")]

    assert store.link_mention("b", "a") is True

    updated = store.get("b")
    assert updated is not None
    assert "[[Python]]" in updated.content

    # Mention now disappears...
    assert store.find_unlinked_mentions("a") == []
    # ...and the link edge shows up in the index.
    assert "a" in store.get_links("b")


def test_link_mention_inserts_canonical_title(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="I love python (lowercase).")

    assert store.link_mention("b", "a") is True

    updated = store.get("b")
    assert updated is not None
    # Canonical casing, not the body's verbatim "python".
    assert "[[Python]]" in updated.content
    assert "[[python]]" not in updated.content


def test_link_mention_first_occurrence_only(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="Python then Python again.")

    assert store.link_mention("b", "a") is True

    updated = store.get("b")
    assert updated is not None
    assert updated.content == "[[Python]] then Python again."
    assert updated.content.count("[[Python]]") == 1


def test_link_mention_missing_note_returns_false(store: NoteStore) -> None:
    _make(store, "a", "Python")

    assert store.link_mention("nope", "a") is False
    assert store.link_mention("a", "nope") is False


def test_link_mention_no_occurrence_returns_false(store: NoteStore) -> None:
    _make(store, "a", "Python")
    _make(store, "b", "Notes", content="Nothing relevant here.")

    assert store.link_mention("b", "a") is False


def test_link_mention_self_returns_false(store: NoteStore) -> None:
    _make(store, "a", "Python", content="Python is great.")

    assert store.link_mention("a", "a") is False


def test_link_mention_regex_special_title(store: NoteStore) -> None:
    _make(store, "a", "Node.js")
    _make(store, "b", "Backend", content="We ship Node.js in prod.")

    assert store.link_mention("b", "a") is True

    updated = store.get("b")
    assert updated is not None
    assert "[[Node.js]]" in updated.content


def _snippet_cap() -> int:
    from brain_cli.storage.store import _SNIPPET_WIDTH

    return _SNIPPET_WIDTH + 2  # allow for leading/trailing ellipsis
