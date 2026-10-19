---
description: "Use when editing C++ source or header files. Covers the language standard and general implementation conventions."
applyTo: "**/*.{cpp,h}"
---

# C++ Guidelines

- Keep the project compatible with C++17 and the existing `clang++` Makefile build.
- Do not introduce raw owning pointers or manual memory management.
- Cast characters to `unsigned char` before passing them to `<cctype>` functions.
- Prefer small, focused changes over unrelated refactoring or new dependencies.