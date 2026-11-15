#pragma once

#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>

#include "gamer/game.h"
#include "gamer/sessions.h"

// JSON shapes of the HTTP API.
namespace gamer::protocol {

// The request body does not match the expected shape (HTTP 422).
class InvalidRequest : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

struct MoveRequest {
  Json move;  // object, interpreted by the game
  std::int64_t version = 0;
};

MoveRequest parse_move_request(std::string_view body);

Json seat_or_null(const std::optional<Seat>& seat);
Json game_info(const Game& game);                         // {id, name}
Json session_summary(const Session& session);             // {session_id, game_id}
Json seat_assignment(const std::string& session_id,       // {session_id, seat, token}
                     const SeatAssignment& assignment);
Json status(const GameStatus& status);                    // {to_move, finished, winner, scores}

}  // namespace gamer::protocol
