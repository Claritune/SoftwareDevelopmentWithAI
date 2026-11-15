#include <gtest/gtest.h>

#include "test_server.h"

using gamer::Json;

TEST(Directory, ListGames) {
  TestServer server;
  auto res = server.get("/api/games");
  EXPECT_EQ(res.status, 200);
  EXPECT_EQ(res.body, Json::parse(R"([{"id": "othello", "name": "Othello"}])"));
}

TEST(Directory, IndexPageServed) {
  TestServer server;
  auto res = server.get("/");
  EXPECT_EQ(res.status, 200);
  EXPECT_TRUE(res.content_type.starts_with("text/html")) << res.content_type;
}

TEST(Directory, CommonJsServed) {
  TestServer server;
  auto res = server.get("/static/common.js");
  EXPECT_EQ(res.status, 200);
  EXPECT_TRUE(res.content_type.starts_with("text/javascript")) << res.content_type;
}

TEST(Directory, OthelloViewJsServed) {
  TestServer server;
  EXPECT_EQ(server.get("/games/othello/static/view.js").status, 200);
  EXPECT_EQ(server.get("/games/othello/static/othello.css").status, 200);
}

TEST(Directory, PathTraversalIsRejected) {
  TestServer server;
  EXPECT_NE(server.get("/static/../app.cpp").status, 200);
}
