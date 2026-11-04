# QRSPI Demo Progress — C++ URL Monitor

## What we're building
A step-by-step demo of the QRSPI methodology applied to a C++ CLI URL monitor.
Each step is a subfolder under `steps/` showing the complete project state at that point.

## Decisions made
- **Build system**: CMake + FetchContent (auto-downloads deps)
- **Branch strategy**: Subfolders (not branches) since this repo is shared with other demos
- **Naming**: step-0-goal, step-1-questions, step-2-design, etc.
- **Demo style**: Full QRSPI artifacts (thoughts/ directory in each step)
- **Implementation phases**: 2 phases (Phase 1: CLI + single check + transitions, Phase 2: poll loop + logging + shutdown)
- **Libraries**: cpr (HTTP), CLI11 (arg parsing), Catch2 (tests)
- **Hook added**: `~/.claude/hooks/guard_rm.py` blocks recursive rm commands

## Installed tools
- CMake 4.4.0 (just installed via brew)
- Apple Clang 17 (already present)
- GNU Make 3.81 (already present)

## Steps completed

| Step | Folder | Status |
|------|--------|--------|
| step-0-goal | `steps/step-0-goal/` | Done — just goal.md |
| step-1-questions | `steps/step-1-questions/` | Done — task.md, questions.md, answers.md |
| step-2-design | `steps/step-2-design/` | Done — adds design.md |
| step-3-structure | `steps/step-3-structure/` | Done — adds structure.md |
| step-4-plan | `steps/step-4-plan/` | Done — adds plan.md |
| step-5-implement-phase1 | `steps/step-5-implement-phase1/` | Done — single check round, all tests pass |
| step-6-implement-phase2 | `steps/step-6-implement-phase2/` | Done — poll loop, logger, signal handling, 8 tests pass |

## Resolved: cpr/filesystem build issue

**Root cause**: Apple Clang 17 Command Line Tools has an incomplete C++ header set at 
`/Library/Developer/CommandLineTools/usr/include/c++/v1/` (only internal dirs, no `<iostream>` or `<filesystem>`). 
The full headers exist in the SDK at `MacOSX.sdk/usr/include/c++/v1/`.

**Fix applied**: Added `-isystem` flag via CMake to point at the SDK's C++ headers:
```cmake
if(APPLE)
    execute_process(COMMAND xcrun --show-sdk-path
        OUTPUT_VARIABLE _sdk OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(_sdk AND EXISTS "${_sdk}/usr/include/c++/v1")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -isystem ${_sdk}/usr/include/c++/v1")
    endif()
endif()
```

Also fixed: `cpr::Redirect{10}` → `cpr::Redirect(10L)` (ambiguous constructor in cpr 1.11.2).

## File structure of step-6 (final)
```
steps/step-6-implement-phase2/
├── CMakeLists.txt
├── goal.md
├── src/
│   ├── config.h
│   ├── checker.h
│   ├── checker.cpp
│   ├── monitor.h
│   ├── monitor.cpp
│   ├── logger.h
│   ├── logger.cpp
│   └── main.cpp
├── tests/
│   └── test_monitor.cpp (8 test cases, 25 assertions)
└── thoughts/qrspi/2026-07-12-url-monitor-cpp/
    ├── task.md
    ├── questions.md
    ├── answers.md
    ├── design.md
    ├── structure.md
    └── plan.md
```

## QRSPI skills location
Reference skills: `demos/url_monitor_service_reference/docs/skills/` (repo root)
