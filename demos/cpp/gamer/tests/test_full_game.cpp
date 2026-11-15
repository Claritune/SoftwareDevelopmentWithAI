#include <map>

#include <gtest/gtest.h>

#include "test_server.h"

using gamer::Json;

TEST(FullGame, PlayedViaApi) {
  TestServer server;
  auto match = start_match(server);
  std::map<std::string, std::string> tokens{{"black", match.black}, {"white", match.white}};
  auto state_path = "/api/sessions/" + match.sid + "/state";

  std::map<std::string, Json> states;
  for (int i = 0; i < 100; ++i) {
    for (const auto& [seat, token] : tokens) states[seat] = server.get(state_path, token).body;
    if (states["black"]["lifecycle"] == "finished") break;
    auto seat = states["black"]["status"]["to_move"].get<std::string>();
    const auto& st = states[seat];
    auto r = server.post("/api/sessions/" + match.sid + "/moves",
                         move_body(st["legal_moves"][0], st["version"].get<int>()), tokens[seat]);
    ASSERT_EQ(r.status, 200);
  }

  const auto& final_state = states["black"];
  ASSERT_EQ(final_state["lifecycle"], "finished");
  int black = final_state["status"]["scores"]["black"];
  int white = final_state["status"]["scores"]["white"];
  EXPECT_LE(black + white, 64);
  Json expected = black == white ? Json(nullptr) : Json(black > white ? "black" : "white");
  EXPECT_EQ(final_state["status"]["winner"], expected);

  auto late = server.post("/api/sessions/" + match.sid + "/moves",
                          move_body({{"row", 0}, {"col", 0}}, final_state["version"].get<int>()),
                          match.black);
  EXPECT_EQ(late.status, 409);
}
