#include "gamer/protocol.h"

namespace gamer::protocol {

MoveRequest parse_move_request(std::string_view body) {
  auto json = Json::parse(body, nullptr, /*allow_exceptions=*/false);
  if (!json.is_object()) throw InvalidRequest("body must be a JSON object");
  auto move = json.find("move");
  if (move == json.end() || !move->is_object()) throw InvalidRequest("move must be an object");
  auto version = json.find("version");
  if (version == json.end() || !version->is_number_integer())
    throw InvalidRequest("version must be an integer");
  return {*move, version->get<std::int64_t>()};
}

Json seat_or_null(const std::optional<Seat>& seat) { return seat ? Json(*seat) : Json(nullptr); }

Json game_info(const Game& game) { return {{"id", game.id()}, {"name", game.name()}}; }

Json session_summary(const Session& session) {
  return {{"session_id", session.id()}, {"game_id", session.game().id()}};
}

Json seat_assignment(const std::string& session_id, const SeatAssignment& assignment) {
  return {{"session_id", session_id}, {"seat", assignment.seat}, {"token", assignment.token}};
}

Json status(const GameStatus& status) {
  return {{"to_move", seat_or_null(status.to_move)},
          {"finished", status.finished},
          {"winner", seat_or_null(status.winner)},
          {"scores", status.scores}};
}

}  // namespace gamer::protocol
