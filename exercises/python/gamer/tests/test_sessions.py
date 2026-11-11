import json

import pytest
from fakes import FakeGame

from gamer.games.base import IllegalMove
from gamer.sessions import (
    CODE_ALPHABET,
    GameNotStarted,
    SessionFull,
    SessionNotFound,
    SessionRegistry,
    UnknownPlayer,
    new_code,
)


def make_full():
    registry = SessionRegistry()
    session, ann = registry.create(FakeGame(), "Ann")
    _, bob = session.join("Bob")
    return registry, session, ann, bob


def test_new_code_shape():
    assert not set("0O1I") & set(CODE_ALPHABET)
    for _ in range(200):
        code = new_code()
        assert len(code) == 6
        assert all(ch in CODE_ALPHABET for ch in code)


def test_create_takes_seat_zero():
    session, seat = SessionRegistry().create(FakeGame(), "Ann")
    assert seat.name == "Ann"
    assert seat.player_id
    assert session.version == 1
    assert session.status == "waiting"


def test_create_retries_on_code_collision():
    registry = SessionRegistry(code_factory=iter(["AAAAAA", "AAAAAA", "BBBBBB"]).__next__)
    s1, _ = registry.create(FakeGame(), "Ann")
    s2, _ = registry.create(FakeGame(), "Bob")
    assert s1.code == "AAAAAA"
    assert s2.code == "BBBBBB"


def test_join_fills_seat_and_starts():
    session, ann = SessionRegistry().create(FakeGame(), "Ann")
    index, bob = session.join("Bob")
    assert index == 1
    assert bob.name == "Bob"
    assert session.version == 2
    assert session.status == "playing"
    assert ann.player_id != bob.player_id


def test_join_full_raises():
    _, session, _, _ = make_full()
    with pytest.raises(SessionFull):
        session.join("Cat")


def test_get_unknown_raises():
    with pytest.raises(SessionNotFound):
        SessionRegistry().get("ZZZZZZ")


def test_get_is_case_insensitive():
    registry = SessionRegistry()
    session, _ = registry.create(FakeGame(), "Ann")
    assert registry.get(session.code.lower()) is session


def test_payload_hides_player_ids():
    _, session, ann, bob = make_full()
    payload = session.to_payload()
    assert payload["players"] == [{"seat": 0, "name": "Ann"}, {"seat": 1, "name": "Bob"}]
    assert payload["game_id"] == "fake"
    text = json.dumps(payload)
    assert ann.player_id not in text
    assert bob.player_id not in text


def test_open_sessions_filters():
    registry = SessionRegistry()
    fake, other = FakeGame("fake"), FakeGame("other")
    s1, _ = registry.create(fake, "Ann")
    s2, _ = registry.create(fake, "Cat")
    s3, _ = registry.create(other, "Dan")
    s2.join("Bob")
    assert registry.open_sessions("fake") == [s1]
    assert registry.open_sessions("other") == [s3]


def test_move_unknown_player():
    _, session, _, _ = make_full()
    with pytest.raises(UnknownPlayer):
        session.move("nope", {"step": 1})


def test_move_before_start():
    session, ann = SessionRegistry().create(FakeGame(), "Ann")
    with pytest.raises(GameNotStarted):
        session.move(ann.player_id, {"step": 1})


def test_move_bumps_version():
    _, session, ann, bob = make_full()
    assert session.version == 2
    before = session.state
    with pytest.raises(IllegalMove):
        session.move(bob.player_id, {"step": 1})
    assert session.version == 2
    assert session.state is before
    session.move(ann.player_id, {"step": 1})
    assert session.version == 3


def test_fake_game_finishes():
    registry = SessionRegistry()
    session, ann = registry.create(FakeGame(target=3), "Ann")
    _, bob = session.join("Bob")
    for pid in (ann.player_id, bob.player_id, ann.player_id):
        session.move(pid, {"step": 1})
    assert session.status == "finished"
