cmake_minimum_required(VERSION 3.16)
project(maestro LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(MAESTRO_SOURCES
    src/main.cpp
    src/Producer.cpp
    src/Composer.cpp
    src/Arranger.cpp
    src/Synth.cpp
    src/Critic.cpp
    src/WavWriter.cpp)

set(MAESTRO_TEST_SOURCES
    tests/test_core.cpp
    src/Producer.cpp
    src/Composer.cpp
    src/Arranger.cpp
    src/Synth.cpp
    src/Critic.cpp)

foreach(source_file IN LISTS MAESTRO_SOURCES MAESTRO_TEST_SOURCES)
    if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${source_file}")
        set(MAESTRO_BOOTSTRAP_BUILD ON)
        break()
    endif()
endforeach()

if(MAESTRO_BOOTSTRAP_BUILD)
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/maestro_bootstrap_main.cpp" "int main() { return 0; }\n")
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/maestro_bootstrap_test.cpp" "int main() { return 0; }\n")
    set(MAESTRO_SOURCES "${CMAKE_CURRENT_BINARY_DIR}/maestro_bootstrap_main.cpp")
    set(MAESTRO_TEST_SOURCES "${CMAKE_CURRENT_BINARY_DIR}/maestro_bootstrap_test.cpp")
    message(STATUS "Maestro bootstrap build: production and test sources will be enabled when implemented.")
endif()

add_executable(maestro ${MAESTRO_SOURCES})
target_include_directories(maestro PRIVATE include)
target_compile_options(maestro PRIVATE -Wall -Wextra)

enable_testing()
add_executable(maestro_tests ${MAESTRO_TEST_SOURCES})
target_include_directories(maestro_tests PRIVATE include)
target_compile_options(maestro_tests PRIVATE -Wall -Wextra)
add_test(NAME core COMMAND maestro_tests)