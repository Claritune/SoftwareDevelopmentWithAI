import pytest
from gamer.games import REGISTRY
from gamer.sessions import GameNotFound, SessionFull, SessionManager, SessionNotFound


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager(REGISTRY)


def test_create_claims_first_seat(manager):
    session, seat, token = manager.create("othello")
    assert seat == "black"
    assert token
    assert session.lifecycle == "waiting"
    assert session.version == 1


def test_join_claims_second_seat(manager):
    session, _, token_a = manager.create("othello")
    seat, token_b = session.join()
    assert seat == "white"
    assert token_b and token_b != token_a
    assert session.lifecycle == "playing"
    assert session.version == 2


def test_third_join_is_full(manager):
    session, _, _ = manager.create("othello")
    session.join()
    with pytest.raises(SessionFull):
        session.join()


def test_seat_for(manager):
    session, _, token_a = manager.create("othello")
    _, token_b = session.join()
    assert session.seat_for(token_a) == "black"
    assert session.seat_for(token_b) == "white"
    assert session.seat_for("nope") is None
    assert session.seat_for(None) is None


def test_list_open(manager):
    session, _, _ = manager.create("othello")
    assert session in manager.list_open("othello")
    session.join()
    assert session not in manager.list_open("othello")


def test_not_found_errors(manager):
    with pytest.raises(SessionNotFound):
        manager.get("missing")
    with pytest.raises(GameNotFound):
        manager.create("chess")
    with pytest.raises(GameNotFound):
        manager.list_open("chess")
