#include <gtest/gtest.h>

#include "test_server.h"

using gamer::Json;

namespace {

class ApiMovesTest : public ::testing::Test {
 protected:
  TestServer server;
  Match match = start_match(server);

  TestServer::Response post_move(const std::string& token, const Json& move, int version,
                                 const std::string& sid = "") {
    return server.post("/api/sessions/" + (sid.empty() ? match.sid : sid) + "/moves",
                       move_body(move, version), token);
  }

  Json state(const std::string& token) {
    return server.get("/api/sessions/" + match.sid + "/state", token).body;
  }
};

const Json kOpening = {{"row", 2}, {"col", 3}};

}  // namespace

TEST_F(ApiMovesTest, BlackMoves) {
  auto res = post_move(match.black, kOpening, 2);
  ASSERT_EQ(res.status, 200);
  const auto& s = res.body;
  EXPECT_EQ(s["version"], 3);
  EXPECT_EQ(s["public_state"]["board"][2][3], "black");
  EXPECT_EQ(s["legal_moves"], Json::array());
  auto w = state(match.white);
  EXPECT_NE(w["legal_moves"], Json::array());
  EXPECT_EQ(w["status"]["to_move"], "white");
}

TEST_F(ApiMovesTest, WhiteMovingFirstIs409) {
  auto res = post_move(match.white, {{"row", 2}, {"col", 4}}, 2);
  EXPECT_EQ(res.status, 409);
  EXPECT_TRUE(res.body.contains("detail"));
}

TEST_F(ApiMovesTest, StaleVersionIs409) {
  auto res = post_move(match.black, kOpening, 1);
  EXPECT_EQ(res.status, 409);
  EXPECT_TRUE(res.body.contains("detail"));
  EXPECT_EQ(state(match.black)["version"], 2);
}

TEST_F(ApiMovesTest, IllegalMoveIs400) {
  auto res = post_move(match.black, {{"row", 0}, {"col", 0}}, 2);
  EXPECT_EQ(res.status, 400);
  EXPECT_TRUE(res.body.contains("detail"));
  res = post_move(match.black, {{"x", 1}}, 2);
  EXPECT_EQ(res.status, 400);
  EXPECT_TRUE(res.body.contains("detail"));
  EXPECT_EQ(state(match.black)["version"], 2);
}

TEST_F(ApiMovesTest, TokenAndSessionErrors) {
  EXPECT_EQ(post_move("bogus", kOpening, 2).status, 403);
  EXPECT_EQ(post_move("", kOpening, 2).status, 403);
  EXPECT_EQ(post_move(match.black, kOpening, 2, "missing").status, 404);
}

TEST_F(ApiMovesTest, MalformedBodyIs422) {
  auto path = "/api/sessions/" + match.sid + "/moves";
  EXPECT_EQ(server.post(path, Json{{"move", kOpening}}, match.black).status, 422);
  EXPECT_EQ(server.post(path, Json{{"move", 5}, {"version", 2}}, match.black).status, 422);
  EXPECT_EQ(server.post(path, Json{{"move", kOpening}, {"version", "2"}}, match.black).status, 422);
  EXPECT_EQ(server.post(path, nullptr, match.black).status, 422);
}

TEST_F(ApiMovesTest, MoveInWaitingSessionIs409) {
  auto a = server.post("/api/games/othello/sessions").body;
  auto res = post_move(a["token"].get<std::string>(), kOpening, 1,
                       a["session_id"].get<std::string>());
  EXPECT_EQ(res.status, 409);
}
