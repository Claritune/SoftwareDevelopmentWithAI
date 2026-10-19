cmake_minimum_required(VERSION 3.20)
project(cats_vs_mutants LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
endif()

option(CVM_BUILD_TESTS "Build the GoogleTest suite" ON)

set(CVM_WARNINGS -Wall -Wextra -Wpedantic)

# Core game logic: pure, deterministic, no ncurses, no I/O.
add_library(cvm_core STATIC
  src/core/game.cpp
  src/core/waves.cpp
)
target_include_directories(cvm_core PUBLIC src/core)
target_compile_options(cvm_core PRIVATE ${CVM_WARNINGS})

# Terminal UI and headless runner.
find_package(Curses REQUIRED)
add_executable(cats
  src/ui/main.cpp
  src/ui/renderer.cpp
  src/ui/headless.cpp
)
target_include_directories(cats PRIVATE ${CURSES_INCLUDE_DIRS})
target_link_libraries(cats PRIVATE cvm_core ${CURSES_LIBRARIES})
target_compile_options(cats PRIVATE ${CVM_WARNINGS})

if(CVM_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
