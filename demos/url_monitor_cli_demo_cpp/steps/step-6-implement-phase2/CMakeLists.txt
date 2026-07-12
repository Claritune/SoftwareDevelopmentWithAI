cmake_minimum_required(VERSION 3.14)
project(url_monitor VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(APPLE)
    execute_process(COMMAND xcrun --show-sdk-path
        OUTPUT_VARIABLE _sdk OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(_sdk AND EXISTS "${_sdk}/usr/include/c++/v1")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -isystem ${_sdk}/usr/include/c++/v1")
    endif()
endif()

include(FetchContent)

FetchContent_Declare(cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr.git
    GIT_TAG 1.11.2)
set(CPR_USE_SYSTEM_CURL ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(cpr)

FetchContent_Declare(cli11
    GIT_REPOSITORY https://github.com/CLIUtils/CLI11.git
    GIT_TAG v2.4.2)
FetchContent_MakeAvailable(cli11)

FetchContent_Declare(Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.7.1)
FetchContent_MakeAvailable(Catch2)

add_executable(url-monitor
    src/main.cpp
    src/checker.cpp
    src/monitor.cpp
    src/logger.cpp)
target_link_libraries(url-monitor PRIVATE cpr::cpr CLI11::CLI11)
target_include_directories(url-monitor PRIVATE src)

enable_testing()
add_executable(tests tests/test_monitor.cpp src/monitor.cpp)
target_link_libraries(tests PRIVATE Catch2::Catch2WithMain)
target_include_directories(tests PRIVATE src)
add_test(NAME unit_tests COMMAND tests)
