cmake_minimum_required(VERSION 3.16)
project(urlmon CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(CURL REQUIRED)

include(FetchContent)
# yaml-cpp 0.8.0 declares an old cmake_minimum_required; CMake 4 needs this floor.
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)

set(YAML_CPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(YAML_CPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(yaml-cpp
  GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
  GIT_TAG 0.8.0)

set(JSON_BuildTests OFF CACHE INTERNAL "")
FetchContent_Declare(json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG v3.12.0)

FetchContent_MakeAvailable(yaml-cpp json)

add_library(urlmon_core STATIC
  src/config.cpp
  src/checker.cpp
  src/notifier.cpp
  src/monitor.cpp
  src/state.cpp)
target_include_directories(urlmon_core PUBLIC src)
target_link_libraries(urlmon_core PUBLIC
  CURL::libcurl yaml-cpp::yaml-cpp nlohmann_json::nlohmann_json)

add_executable(urlmon src/main.cpp)
target_link_libraries(urlmon PRIVATE urlmon_core)

enable_testing()

add_executable(test_classify tests/test_classify.cpp)
target_link_libraries(test_classify PRIVATE urlmon_core)
add_test(NAME test_classify COMMAND test_classify)
