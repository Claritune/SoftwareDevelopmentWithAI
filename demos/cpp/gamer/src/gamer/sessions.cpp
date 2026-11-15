#include "gamer/sessions.h"

#include <random>

namespace gamer {

namespace {

// URL-safe base64 of `nbytes` random bytes, like Python's secrets.token_urlsafe.
std::string token_urlsafe(std::size_t nbytes) {
  static constexpr char kAlphabet[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  std::random_device rd;
  std::uniform_int_distribution<int> byte(0, 255);
  std::string out;
  unsigned buffer = 0;
  int bits = 0;
  for (std::size_t i = 0; i < nbytes; ++i) {
    buffer = (buffer << 8) | static_cast<unsigned>(byte(rd));
    bits += 8;
    while (bits >= 6) {
      bits -= 6;
      out += kAlphabet[(buffer >> bits) & 63];
    }
  }
  if (bits > 0) out += kAlphabet[(buffer << (6 - bits)) & 63];
  return out;
}

}  // namespace

std::string to_string(Lifecycle lifecycle) {
  switch (lifecycle) {
    case Lifecycle::Waiting: return "waiting";
    case Lifecycle::Playing: return "playing";
    case Lifecycle::Finished: return "finished";
  }
  return "unknown";
}

Session::Session(std::string id, std::shared_ptr<const Game> game)
    : id_(std::move(id)), game_(std::move(game)), state_(game_->initial_state()) {}

Lifecycle Session::lifecycle() const {
  if (seat_tokens_.size() < game_->seats().size()) return Lifecycle::Waiting;
  return game_->status(state_).finished ? Lifecycle::Finished : Lifecycle::Playing;
}

std::optional<Seat> Session::seat_for(std::string_view token) const {
  if (token.empty()) return std::nullopt;
  auto it = seat_tokens_.find(token);
  if (it == seat_tokens_.end()) return std::nullopt;
  return it->second;
}

std::set<Seat> Session::taken_seats() const {
  std::set<Seat> taken;
  for (const auto& [token, seat] : seat_tokens_) taken.insert(seat);
  return taken;
}

SeatAssignment Session::claim_seat() {
  auto taken = taken_seats();
  for (const auto& seat : game_->seats()) {
    if (taken.contains(seat)) continue;
    auto token = token_urlsafe(16);
    seat_tokens_[token] = seat;
    return {seat, token};
  }
  throw SessionFull();
}

SeatAssignment Session::join() {
  auto assignment = claim_seat();
  ++version_;
  return assignment;
}

void Session::move(std::string_view token, const Json& raw_move, std::int64_t version) {
  auto seat = seat_for(token);
  if (!seat) throw BadToken();
  if (version != version_) throw StaleVersion();
  if (lifecycle() != Lifecycle::Playing || game_->status(state_).to_move != seat)
    throw NotYourTurn();
  auto move = game_->parse_move(raw_move);           // may throw IllegalMove
  state_ = game_->apply_move(state_, *seat, move);  // may throw IllegalMove
  ++version_;
}

SessionManager::SessionManager(Registry registry) : registry_(std::move(registry)) {}

const std::shared_ptr<const Game>& SessionManager::game(std::string_view game_id) const {
  for (const auto& game : registry_)
    if (game->id() == game_id) return game;
  throw GameNotFound();
}

std::pair<Session&, SeatAssignment> SessionManager::create(std::string_view game_id) {
  const auto& game = this->game(game_id);
  std::string id;
  do id = token_urlsafe(6);
  while (by_id_.contains(id));
  auto& session = *sessions_.emplace_back(std::make_unique<Session>(id, game));
  by_id_.emplace(id, &session);
  auto assignment = session.claim_seat();
  return {session, assignment};
}

Session& SessionManager::get(std::string_view session_id) {
  auto it = by_id_.find(session_id);
  if (it == by_id_.end()) throw SessionNotFound();
  return *it->second;
}

std::vector<const Session*> SessionManager::list_open(std::string_view game_id) const {
  game(game_id);  // 404 for unknown game
  std::vector<const Session*> open;
  for (const auto& s : sessions_)
    if (s->game().id() == game_id && s->lifecycle() == Lifecycle::Waiting) open.push_back(s.get());
  return open;
}

}  // namespace gamer
