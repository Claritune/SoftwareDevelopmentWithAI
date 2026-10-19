include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/releases/download/v1.15.2/googletest-1.15.2.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# Links only the core library, never ncurses.
add_executable(cvm_tests
  smoke_test.cpp
  placement_test.cpp
  economy_test.cpp
  mutant_test.cpp
  combat_test.cpp
  end_conditions_test.cpp
  waves_config_test.cpp
  full_game_test.cpp
)
target_link_libraries(cvm_tests PRIVATE cvm_core GTest::gtest_main)
target_compile_options(cvm_tests PRIVATE ${CVM_WARNINGS})

include(GoogleTest)
gtest_discover_tests(cvm_tests DISCOVERY_TIMEOUT 30)
