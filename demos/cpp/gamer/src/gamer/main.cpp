#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>
#include <string_view>

#include "gamer/app.h"

int main(int argc, char** argv) {
  std::string host = "127.0.0.1";
  int port = 8000;
  for (int i = 1; i < argc; ++i) {
    std::string_view arg = argv[i];
    if (arg == "--host" && i + 1 < argc) {
      host = argv[++i];
    } else if (arg == "--port" && i + 1 < argc) {
      port = std::atoi(argv[++i]);
    } else {
      std::cerr << "usage: gamer [--host HOST] [--port PORT]\n";
      return 2;
    }
  }

  try {
    gamer::App app;
    std::cout << "Gamer serving on http://" << host << ":" << port << std::endl;
    if (!app.server().listen(host, port)) {
      std::cerr << "could not listen on " << host << ":" << port << "\n";
      return 1;
    }
  } catch (const std::exception& e) {
    std::cerr << "error: " << e.what() << "\n";
    return 1;
  }
  return 0;
}
