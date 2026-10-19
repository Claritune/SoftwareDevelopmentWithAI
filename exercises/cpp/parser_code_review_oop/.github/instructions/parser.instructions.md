---
description: "Use when changing the recursive-descent expression parser, input grammar, or parse errors."
applyTo: "parser.{cpp,h}"
---

# Parser Guidelines

- Preserve the input grammar: an expression is an integer literal or a case-sensitive binary function call using `Sum`, `Mult`, `Div`, or `Exponent`.
- Keep parsing behavior in `Parser` and implement it as recursive descent using the parser's current position.
- Check bounds before looking ahead in the input.
- Reject malformed input and trailing non-whitespace input with a clear exception; never silently accept a partial parse.