# Maestro - shared instructions for all agents

- Language: C++17, standard library only. No third-party dependencies. Build with `-Wall -Wextra` and zero warnings.
- The data contracts in `include/maestro/Contracts.h` are the interface between modules. Do not change them unless you are the Architect agent.
- Each agent edits only its owned files. If a task needs another module changed, stop and report it to the Producer.
- All randomness comes from `MusicalContext::rng`. Do not use another RNG or global state.
- Symbolic note logic must be unit-testable without audio playback.
- Prefer small, reviewable diffs. Explain a non-obvious music or DSP choice in a one-line comment.