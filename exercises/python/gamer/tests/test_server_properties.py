"""Model-based property tests: random client traffic against the HTTP API, checked after
every step against a model of what the server should hold."""

import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from fakes import FakeGame
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, assume, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from strategies import (
    any_moves,
    any_names,
    broken_envelopes,
    invalid_names,
    json_values,
    url_segments,
    valid_code_shape,
    valid_names,
)

from gamer.app import create_app
from gamer.games.base import Game, IllegalMove, InvalidMove
from gamer.games.othello import OthelloGame

KNOWN_ERRORS = {
    "bad_request": 400,
    "not_found": 404,
    "method_not_allowed": 405,
    "game_not_found": 404,
    "session_not_found": 404,
    "session_full": 409,
    "unknown_player": 403,
    "game_not_started": 409,
    "invalid_move": 400,
    "illegal_move": 409,
}
CODE_RE = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")


def env(type_: str, payload: Any) -> dict:
    return {"v": 1, "type": type_, "payload": payload}


@dataclass
class ModelSession:
    code: str
    game: Game
    state: Any
    seats: list[tuple[str, str]] = field(default_factory=list)  # (player_id, name)
    accepted_moves: int = 0

    @property
    def full(self) -> bool:
        return len(self.seats) >= self.game.max_players

    def expected_move_error(self, player_id: str, payload: Any) -> str | None:
        """Run the move through the game itself to predict the server's answer."""
        if player_id not in {pid for pid, _ in self.seats}:
            return "unknown_player"
        if not self.full:
            return "game_not_started"
        try:
            move = self.game.parse_move(payload)
            seat = next(i for i, (pid, _) in enumerate(self.seats) if pid == player_id)
            self.game.apply_move(self.state, seat, move)
        except InvalidMove:
            return "invalid_move"
        except IllegalMove:
            return "illegal_move"
        return None


class ServerMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.games: dict[str, Game] = {"othello": OthelloGame(), "fake": FakeGame(target=4)}
        self.http = TestClient(create_app(games=self.games), raise_server_exceptions=False)
        self.sessions: dict[str, ModelSession] = {}
        self.issued_ids: set[str] = set()

    # -- transport -------------------------------------------------------------------------

    def call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        r = self.http.request(method, path, **kwargs)
        assert r.status_code < 500, r.text
        if path.startswith("/api/"):
            body = r.json()
            assert body["v"] == 1
            if r.status_code == 200:
                assert body["type"] != "error"
            else:
                assert body["type"] == "error", r.text
                assert KNOWN_ERRORS.get(body["payload"]["code"]) == r.status_code, r.text
                assert isinstance(body["payload"]["message"], str)
        return r

    def error_code(self, r: httpx.Response) -> str | None:
        return None if r.status_code == 200 else r.json()["payload"]["code"]

    def record_join(self, r: httpx.Response, game: Game | None = None) -> None:
        p = r.json()["payload"]
        assert CODE_RE.match(p["code"])
        assert p["player_id"] not in self.issued_ids, "player_id reused"
        self.issued_ids.add(p["player_id"])
        if game is not None:
            assert p["code"] not in self.sessions, "session code reused"
            self.sessions[p["code"]] = ModelSession(p["code"], game, game.initial_state())
        session = self.sessions[p["code"]]
        assert p["seat"] == len(session.seats)
        session.seats.append((p["player_id"], p["state"]["players"][p["seat"]]["name"]))

    def pick_session(self, data, pred=lambda s: True) -> ModelSession:
        candidates = [s for s in self.sessions.values() if pred(s)]
        assume(candidates)
        return data.draw(st.sampled_from(candidates), label="session")

    # -- lobby -----------------------------------------------------------------------------

    @rule(game_id=st.sampled_from(["othello", "fake"]), name=valid_names)
    def create(self, game_id, name):
        r = self.call("POST", f"/api/games/{game_id}/sessions", json=env("create", {"name": name}))
        assert r.status_code == 200
        self.record_join(r, self.games[game_id])
        assert self.sessions[r.json()["payload"]["code"]].seats[0][1] == name.strip()

    @rule(game_id=st.sampled_from(["othello", "fake"]) | url_segments, name=any_names)
    def create_with_any_name(self, game_id, name):
        r = self.call("POST", f"/api/games/{game_id}/sessions", json=env("create", {"name": name}))
        if r.status_code == 200:
            assert game_id in self.games
            self.record_join(r, self.games[game_id])
            stored = self.sessions[r.json()["payload"]["code"]].seats[0][1]
            assert 1 <= len(stored) <= 32 and stored in name

    @rule(game_id=st.sampled_from(["othello", "fake"]), name=invalid_names)
    def create_with_invalid_name(self, game_id, name):
        r = self.call("POST", f"/api/games/{game_id}/sessions", json=env("create", {"name": name}))
        assert self.error_code(r) == "bad_request"

    @rule(data=st.data(), name=valid_names)
    def join(self, data, name):
        session = self.pick_session(data)
        body = env("join", {"name": name})
        r = self.call("POST", f"/api/sessions/{session.code}/join", json=body)
        if session.full:
            assert self.error_code(r) == "session_full"
        else:
            assert r.status_code == 200
            self.record_join(r)

    @rule(code=valid_code_shape | url_segments, name=valid_names)
    def join_unknown_code(self, code, name):
        assume(code.upper() not in self.sessions)
        r = self.call("POST", f"/api/sessions/{code}/join", json=env("join", {"name": name}))
        assert r.status_code in (404, 405)

    # -- moves -----------------------------------------------------------------------------

    @rule(data=st.data())
    def play_a_legal_move(self, data):
        session = self.pick_session(data, lambda s: s.full)
        snap = session.game.snapshot(session.state)
        assume(snap["status"] == "playing")
        move = data.draw(st.sampled_from(snap["legal_moves"]), label="move")
        self.attempt_move(session, session.seats[snap["current_player"]][0], move)

    @rule(data=st.data(), move=any_moves)
    def attempt_any_move(self, data, move):
        session = self.pick_session(data)
        others = [pid for s in self.sessions.values() if s is not session for pid, _ in s.seats]
        actor = data.draw(
            st.sampled_from([pid for pid, _ in session.seats] + others)
            | st.text(min_size=1, max_size=24),
            label="player_id",
        )
        self.attempt_move(session, actor, move)

    def attempt_move(self, session: ModelSession, player_id: str, move: Any) -> None:
        expected = session.expected_move_error(player_id, move)
        body = env("move", {"player_id": player_id, "move": move})
        r = self.call("POST", f"/api/sessions/{session.code}/moves", json=body)
        assert self.error_code(r) == expected, r.text
        if expected is None:
            seat = next(i for i, (pid, _) in enumerate(session.seats) if pid == player_id)
            session.state = session.game.apply_move(
                session.state, seat, session.game.parse_move(move)
            )
            session.accepted_moves += 1

    # -- hostile traffic -------------------------------------------------------------------

    @rule(data=st.data(), endpoint=st.sampled_from(["create", "join", "move"]))
    def send_broken_envelope(self, data, endpoint):
        session = self.pick_session(data)
        pid = session.seats[0][0]
        path, valid = {
            "create": (f"/api/games/{session.game.id}/sessions", env("create", {"name": "Eve"})),
            "join": (f"/api/sessions/{session.code}/join", env("join", {"name": "Eve"})),
            "move": (
                f"/api/sessions/{session.code}/moves",
                env("move", {"player_id": pid, "move": {"row": 2, "col": 3}}),
            ),
        }[endpoint]
        r = self.call("POST", path, json=data.draw(broken_envelopes(valid), label="body"))
        assert self.error_code(r) == "bad_request", r.text

    @rule(data=st.data(), body=json_values)
    def send_random_json(self, data, body):
        session = self.pick_session(data)
        path = data.draw(
            st.sampled_from(
                [
                    f"/api/games/{session.game.id}/sessions",
                    f"/api/sessions/{session.code}/join",
                    f"/api/sessions/{session.code}/moves",
                ]
            ),
            label="path",
        )
        r = self.call("POST", path, json=body)
        if r.status_code == 200:  # random JSON happened to be a valid create/join request
            created = path.startswith("/api/games/")
            self.record_join(r, session.game if created else None)

    @rule(code=url_segments)
    def poll_hostile_code(self, code):
        assume(code.upper() not in self.sessions)
        assert self.call("GET", f"/api/sessions/{code}").status_code != 200

    # -- invariants ------------------------------------------------------------------------

    @invariant()
    def server_state_matches_the_model(self):
        for code, session in self.sessions.items():
            payload = self.call("GET", f"/api/sessions/{code.lower()}").json()["payload"]
            snap = session.game.snapshot(session.state)
            assert payload["code"] == code
            assert payload["game_id"] == session.game.id
            assert payload["version"] == len(session.seats) + session.accepted_moves
            assert payload["players"] == [
                {"seat": i, "name": name} for i, (_, name) in enumerate(session.seats)
            ]
            assert payload["status"] == ("waiting" if not session.full else snap["status"])
            for key in ("board", "current_player", "legal_moves", "scores", "winner"):
                assert payload[key] == snap[key], key

    @invariant()
    def lobby_lists_exactly_the_waiting_sessions(self):
        for game_id in self.games:
            listed = self.call("GET", f"/api/games/{game_id}/sessions").json()["payload"]
            expected = {
                code for code, s in self.sessions.items() if s.game.id == game_id and not s.full
            }
            assert {s["code"] for s in listed} == expected

    @invariant()
    def player_ids_never_leak(self):
        for session in self.sessions.values():
            text = self.call("GET", f"/api/sessions/{session.code}").text
            text += self.call("GET", f"/api/games/{session.game.id}/sessions").text
            for pid, _ in session.seats:
                assert pid not in text

    def teardown(self) -> None:
        self.http.close()


ServerMachine.TestCase.settings = settings(
    max_examples=30,
    stateful_step_count=30,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
TestServerProperties = ServerMachine.TestCase
