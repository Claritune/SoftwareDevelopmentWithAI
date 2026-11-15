#pragma once

#include <memory>
#include <string>
#include <thread>

#include <httplib.h>

#include "gamer/app.h"

// Runs an App on a free localhost port for the lifetime of the object
// (the C++ counterpart of FastAPI's TestClient: fresh in-memory state per test).
class TestServer {
 public:
  struct Response {
    int status = 0;
    gamer::Json body;  // discarded (is_discarded()) when the body is not JSON
    std::string content_type;
  };

  explicit TestServer(gamer::Registry registry = gamer::default_registry());
  ~TestServer();
  TestServer(const TestServer&) = delete;
  TestServer& operator=(const TestServer&) = delete;

  int port() const { return port_; }
  Response get(const std::string& path, const std::string& token = "");
  Response post(const std::string& path, const gamer::Json& body = nullptr,
                const std::string& token = "");

 private:
  gamer::App app_;
  int port_ = 0;
  std::thread thread_;
};

struct Match {
  std::string sid;
  std::string black;  // token
  std::string white;  // token
};

Match start_match(TestServer& server);  // create an othello session and fill it

gamer::Json move_body(const gamer::Json& move, std::int64_t version);
