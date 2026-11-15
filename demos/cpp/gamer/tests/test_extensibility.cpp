#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>

#include <gtest/gtest.h>

#include "stub_game/stub_game.h"
#include "test_server.h"

using gamer::Json;

namespace {

gamer::Registry stub_registry() { return {gamer::make_game(stub::StubGame{})}; }

}  // namespace

TEST(Extensibility, DirectoryListsOnlyStub) {
  TestServer server(stub_registry());
  EXPECT_EQ(server.get("/api/games").body, Json::parse(R"([{"id": "stub", "name": "Stub"}])"));
}

TEST(Extensibility, StubPagesAndStatic) {
  TestServer server(stub_registry());
  EXPECT_EQ(server.get("/games/stub/static/view.js").status, 200);
  EXPECT_EQ(server.get("/games/stub").status, 200);
  EXPECT_EQ(server.get("/games/othello").status, 404);
}

TEST(Extensibility, StubGamePlaysToFinish) {
  TestServer server(stub_registry());
  auto a = server.post("/api/games/stub/sessions").body;
  auto sid = a["session_id"].get<std::string>();
  auto b = server.post("/api/sessions/" + sid + "/join").body;
  std::map<std::string, std::string> tokens{{a["seat"], a["token"]}, {b["seat"], b["token"]}};
  ASSERT_EQ(tokens.size(), 2u);
  ASSERT_TRUE(tokens.contains("x") && tokens.contains("o"));

  int version = 2;
  Json res;
  for (auto [seat, cell] : std::vector<std::pair<std::string, int>>{{"x", 0}, {"o", 1}, {"x", 2}}) {
    auto r = server.post("/api/sessions/" + sid + "/moves", move_body({{"cell", cell}}, version),
                         tokens[seat]);
    ASSERT_EQ(r.status, 200);
    res = r.body;
    version = res["version"];
  }
  EXPECT_EQ(res["lifecycle"], "finished");
  EXPECT_EQ(res["status"]["winner"], "x");
  auto late = server.post("/api/sessions/" + sid + "/moves", move_body({{"cell", 3}}, version),
                          tokens["o"]);
  EXPECT_EQ(late.status, 409);
}

class CoreIsGameAgnostic : public ::testing::TestWithParam<const char*> {};

TEST_P(CoreIsGameAgnostic, NoGameNamesInCore) {
  auto path = std::filesystem::path(GAMER_SOURCE_DIR) / "src" / "gamer" / GetParam();
  std::ifstream in(path);
  ASSERT_TRUE(in) << path;
  std::ostringstream content;
  content << in.rdbuf();
  auto source = content.str();
  std::transform(source.begin(), source.end(), source.begin(),
                 [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  EXPECT_EQ(source.find("othello"), std::string::npos) << path;
}

INSTANTIATE_TEST_SUITE_P(Extensibility, CoreIsGameAgnostic,
                         ::testing::Values("app.h", "app.cpp", "sessions.h", "sessions.cpp",
                                           "protocol.h", "protocol.cpp", "game.h"));
