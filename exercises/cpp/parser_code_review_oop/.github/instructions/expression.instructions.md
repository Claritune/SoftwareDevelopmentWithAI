---
description: "Use when changing expression nodes, evaluation, ownership, or infix formatting."
applyTo: "expr.{cpp,h}"
---

# Expression Guidelines

- Keep expression behavior in the `Expression` hierarchy.
- Represent owned expression-tree children with `std::unique_ptr`.
- Keep `evaluate()` and `toString()` const, and use `override` for virtual implementations.
- Keep arithmetic integer-only. `Div` uses C++ integer division.
- Fully parenthesize every operation's formatted output, and format negative literals in parentheses, for example `(-2)`.