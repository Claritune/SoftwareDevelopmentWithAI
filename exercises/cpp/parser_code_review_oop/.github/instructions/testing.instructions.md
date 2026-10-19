---
description: "Use when validating C++ behavior, fixing parser edge cases, or changing the Makefile build."
applyTo: ["**/*.cpp", "**/*.h", "Makefile"]
---

# Validation Guidelines

- Run `make test` after behavior changes and `make clean && make` after build-related changes.
- When fixing a parser edge case, add a focused regression case or otherwise verify both valid input and the malformed input that motivated the change.
- Check output exactly, including spaces and parentheses, because formatting is part of the program contract.