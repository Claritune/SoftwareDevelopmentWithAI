cmake_minimum_required(VERSION 3.24)
project(gamer VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(GAMER_BUILD_TESTS "Build the test suite" ON)

find_package(Threads REQUIRED)
include(FetchContent)

# --- Dependencies (header-only, fetched at configure time) -------------------

FetchContent_Declare(nlohmann_json
  URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)

# Only the header is used; SOURCE_SUBDIR skips httplib's own CMake project.
FetchContent_Declare(httplib
  URL https://github.com/yhirose/cpp-httplib/archive/refs/tags/v0.66.0.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
  SOURCE_SUBDIR unused)

FetchContent_MakeAvailable(nlohmann_json httplib)

add_library(httplib INTERFACE)
target_include_directories(httplib SYSTEM INTERFACE ${httplib_SOURCE_DIR})
target_link_libraries(httplib INTERFACE Threads::Threads)
if(WIN32)
  target_compile_definitions(httplib INTERFACE NOMINMAX WIN32_LEAN_AND_MEAN _WIN32_WINNT=0x0A00)
  target_link_libraries(httplib INTERFACE ws2_32)
endif()

function(gamer_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /utf-8 /permissive- /bigobj)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

# --- Server -------------------------------------------------------------------

add_library(gamer_core STATIC
  src/gamer/app.cpp
  src/gamer/protocol.cpp
  src/gamer/sessions.cpp
  src/gamer/games/registry.cpp
  src/gamer/games/othello/othello.cpp)
target_include_directories(gamer_core PUBLIC src)
target_link_libraries(gamer_core PUBLIC nlohmann_json::nlohmann_json httplib)
# Static files (HTML client, game views) are served straight from the source tree.
target_compile_definitions(gamer_core PUBLIC GAMER_SOURCE_DIR="${PROJECT_SOURCE_DIR}")
gamer_warnings(gamer_core)

add_executable(gamer src/gamer/main.cpp)
target_link_libraries(gamer PRIVATE gamer_core)
gamer_warnings(gamer)

# --- Tests --------------------------------------------------------------------

if(GAMER_BUILD_TESTS)
  FetchContent_Declare(googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.17.0.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)

  enable_testing()
  add_executable(gamer_tests
    tests/test_server.cpp
    tests/stub_game/stub_game.cpp
    tests/test_othello.cpp
    tests/test_sessions.cpp
    tests/test_directory.cpp
    tests/test_api_sessions.cpp
    tests/test_api_moves.cpp
    tests/test_full_game.cpp
    tests/test_extensibility.cpp
    tests/test_concurrency.cpp)
  target_include_directories(gamer_tests PRIVATE tests)
  target_link_libraries(gamer_tests PRIVATE gamer_core GTest::gtest_main)
  gamer_warnings(gamer_tests)

  include(GoogleTest)
  gtest_discover_tests(gamer_tests)
endif()
