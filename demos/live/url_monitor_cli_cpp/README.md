# urlmon

A CLI tool that monitors a list of URLs for uptime. It checks each URL on a
schedule, classifies it as **up** (final HTTP status 200) or **down** (anything
else), and logs state transitions to stdout.

## Prerequisites

- CMake 3.16 or newer
- A C++17 compiler
- libcurl development headers (with TLS support)

`yaml-cpp` and `nlohmann/json` are fetched automatically during the first CMake
configure, so the first build takes a little longer.

## Build

```bash
cmake -S . -B build
cmake --build build
```

## Run

```bash
./build/urlmon --config config/example.yaml
```

Full documentation (config schema, CLI flags, state file, statistics) is added
as the tool is completed.
