#include <gtest/gtest.h>

#include "test_server.h"

using gamer::Json;

TEST(ApiSessions, CreateSession) {
  TestServer server;
  auto res = server.post("/api/games/othello/sessions");
  EXPECT_EQ(res.status, 201);
  const auto& body = res.body;
  EXPECT_FALSE(body["session_id"].get<std::string>().empty());
  EXPECT_EQ(body["seat"], "black");
  EXPECT_FALSE(body["token"].get<std::string>().empty());
  auto listed = server.get("/api/games/othello/sessions").body;
  EXPECT_EQ(listed, (Json::array({{{"session_id", body["session_id"]}, {"game_id", "othello"}}})));
}

TEST(ApiSessions, JoinFillsSession) {
  TestServer server;
  auto match = start_match(server);
  EXPECT_EQ(server.get("/api/games/othello/sessions").body, Json::array());
  auto res = server.post("/api/sessions/" + match.sid + "/join");
  EXPECT_EQ(res.status, 409);
  EXPECT_TRUE(res.body.contains("detail"));
}

TEST(ApiSessions, StateWithToken) {
  TestServer server;
  auto match = start_match(server);
  auto res = server.get("/api/sessions/" + match.sid + "/state", match.black);
  EXPECT_EQ(res.status, 200);
  const auto& s = res.body;
  EXPECT_EQ(s["your_seat"], "black");
  EXPECT_EQ(s["lifecycle"], "playing");
  EXPECT_EQ(s["seats"], (Json{{"black", true}, {"white", true}}));
  const auto& board = s["public_state"]["board"];
  ASSERT_EQ(board.size(), 8u);
  for (const auto& row : board) EXPECT_EQ(row.size(), 8u);
  EXPECT_EQ(s["version"], 2);
  EXPECT_EQ(s["legal_moves"].size(), 4u);
}

TEST(ApiSessions, StateWhileWaiting) {
  TestServer server;
  auto a = server.post("/api/games/othello/sessions").body;
  auto s = server.get("/api/sessions/" + a["session_id"].get<std::string>() + "/state",
                      a["token"].get<std::string>()).body;
  EXPECT_EQ(s["lifecycle"], "waiting");
  EXPECT_EQ(s["seats"], (Json{{"black", true}, {"white", false}}));
  EXPECT_EQ(s["legal_moves"], Json::array());
}

TEST(ApiSessions, StateWithoutToken) {
  TestServer server;
  auto match = start_match(server);
  auto s = server.get("/api/sessions/" + match.sid + "/state").body;
  EXPECT_TRUE(s["your_seat"].is_null());
  EXPECT_EQ(s["legal_moves"], Json::array());
}

TEST(ApiSessions, StateErrors) {
  TestServer server;
  auto match = start_match(server);
  auto res = server.get("/api/sessions/" + match.sid + "/state", "bogus");
  EXPECT_EQ(res.status, 403);
  EXPECT_EQ(res.body, (Json{{"detail", "invalid or missing player token"}}));
  EXPECT_EQ(server.get("/api/sessions/missing/state").status, 404);
  EXPECT_EQ(server.get("/api/games/chess/sessions").status, 404);
  EXPECT_EQ(server.post("/api/games/chess/sessions").status, 404);
  EXPECT_EQ(server.post("/api/sessions/missing/join").status, 404);
}

TEST(ApiSessions, Pages) {
  TestServer server;
  for (const char* path : {"/games/othello", "/games/othello/sessions/anything"}) {
    auto res = server.get(path);
    EXPECT_EQ(res.status, 200) << path;
    EXPECT_TRUE(res.content_type.starts_with("text/html")) << path;
  }
  EXPECT_EQ(server.get("/games/chess").status, 404);
  EXPECT_EQ(server.get("/games/chess/sessions/anything").status, 404);
}
