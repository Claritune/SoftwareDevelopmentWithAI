// R1/R4: many clients at once, several sessions in parallel.
#include <atomic>
#include <thread>
#include <vector>

#include <gtest/gtest.h>

#include "test_server.h"

using gamer::Json;

namespace {

// Each player polls and moves on its own thread, like a real browser tab.
void play(TestServer& server, const std::string& sid, const std::string& token,
          std::atomic<int>& failures) {
  auto state_path = "/api/sessions/" + sid + "/state";
  for (int i = 0; i < 2000; ++i) {
    auto s = server.get(state_path, token).body;
    if (s["lifecycle"] == "finished") return;
    if (s["legal_moves"].empty()) {
      std::this_thread::yield();
      continue;
    }
    auto r = server.post("/api/sessions/" + sid + "/moves",
                         move_body(s["legal_moves"][0], s["version"].get<int>()), token);
    if (r.status != 200) ++failures;
  }
  ++failures;  // never finished
}

}  // namespace

TEST(Concurrency, ParallelSessionsPlayToFinish) {
  TestServer server;
  constexpr int kSessions = 6;
  std::vector<Match> matches;
  for (int i = 0; i < kSessions; ++i) matches.push_back(start_match(server));

  std::atomic<int> failures = 0;
  std::vector<std::thread> players;
  for (const auto& m : matches) {
    players.emplace_back(play, std::ref(server), m.sid, m.black, std::ref(failures));
    players.emplace_back(play, std::ref(server), m.sid, m.white, std::ref(failures));
  }
  for (auto& t : players) t.join();

  EXPECT_EQ(failures, 0);
  for (const auto& m : matches)
    EXPECT_EQ(server.get("/api/sessions/" + m.sid + "/state").body["lifecycle"], "finished");
}

TEST(Concurrency, RacingJoinsFillEachSeatOnce) {
  TestServer server;
  auto sid = server.post("/api/games/othello/sessions").body["session_id"].get<std::string>();
  std::atomic<int> joined = 0, full = 0;
  std::vector<std::thread> joiners;
  for (int i = 0; i < 8; ++i)
    joiners.emplace_back([&] {
      auto status = server.post("/api/sessions/" + sid + "/join").status;
      if (status == 200) ++joined;
      if (status == 409) ++full;
    });
  for (auto& t : joiners) t.join();
  EXPECT_EQ(joined, 1);
  EXPECT_EQ(full, 7);
}
