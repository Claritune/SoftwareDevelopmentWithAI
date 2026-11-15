#include <algorithm>

#include <gtest/gtest.h>

#include "gamer/games/registry.h"
#include "gamer/sessions.h"

using namespace gamer;

namespace {

class SessionsTest : public ::testing::Test {
 protected:
  SessionManager manager{default_registry()};
};

bool contains(const std::vector<const Session*>& sessions, const Session& s) {
  return std::find(sessions.begin(), sessions.end(), &s) != sessions.end();
}

}  // namespace

TEST_F(SessionsTest, CreateClaimsFirstSeat) {
  auto [session, a] = manager.create("othello");
  EXPECT_EQ(a.seat, "black");
  EXPECT_FALSE(a.token.empty());
  EXPECT_EQ(session.lifecycle(), Lifecycle::Waiting);
  EXPECT_EQ(session.version(), 1);
}

TEST_F(SessionsTest, JoinClaimsSecondSeat) {
  auto [session, a] = manager.create("othello");
  auto b = session.join();
  EXPECT_EQ(b.seat, "white");
  EXPECT_FALSE(b.token.empty());
  EXPECT_NE(b.token, a.token);
  EXPECT_EQ(session.lifecycle(), Lifecycle::Playing);
  EXPECT_EQ(session.version(), 2);
}

TEST_F(SessionsTest, ThirdJoinIsFull) {
  auto [session, a] = manager.create("othello");
  session.join();
  EXPECT_THROW(session.join(), SessionFull);
}

TEST_F(SessionsTest, SeatFor) {
  auto [session, a] = manager.create("othello");
  auto b = session.join();
  EXPECT_EQ(session.seat_for(a.token), "black");
  EXPECT_EQ(session.seat_for(b.token), "white");
  EXPECT_EQ(session.seat_for("nope"), std::nullopt);
  EXPECT_EQ(session.seat_for(""), std::nullopt);
}

TEST_F(SessionsTest, ListOpen) {
  auto [session, a] = manager.create("othello");
  EXPECT_TRUE(contains(manager.list_open("othello"), session));
  session.join();
  EXPECT_FALSE(contains(manager.list_open("othello"), session));
}

TEST_F(SessionsTest, NotFoundErrors) {
  EXPECT_THROW(manager.get("missing"), SessionNotFound);
  EXPECT_THROW(manager.create("chess"), GameNotFound);
  EXPECT_THROW(manager.list_open("chess"), GameNotFound);
}

TEST_F(SessionsTest, TokensAreUrlSafeAndUnique) {
  auto [session, a] = manager.create("othello");
  auto b = session.join();
  for (const auto& token : {a.token, b.token, session.id()}) {
    EXPECT_TRUE(std::all_of(token.begin(), token.end(), [](char c) {
      return std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_';
    })) << token;
  }
  EXPECT_EQ(a.token.size(), 22u);   // 16 bytes
  EXPECT_EQ(session.id().size(), 8u);  // 6 bytes
}
