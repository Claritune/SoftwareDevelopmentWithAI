# Expression Evaluator Implementation Plan

## Goal

Build a .NET 10 console application that parses nested function-call expressions, renders them as fully parenthesized infix expressions, evaluates them using integer arithmetic, and prints the expression with its result.

Example:

```text
Input:  Sum(Exponent(3, 2), -2)
Output: ((3 ^ 2) + (-2)) = 7
```

## Technical Approach

Use a small expression tree as the common model for parsing, formatting, and evaluation:

- `NumberExpression` stores an integer literal.
- `BinaryExpression` stores an operation and two child expressions.
- `BinaryOperator` identifies `Sum`, `Mult`, `Div`, or `Exponent`.

Keep parsing, evaluation, and formatting separate so each behavior can be tested independently. Use C# records and pattern matching where they make the tree handling concise and explicit.

## Implementation Steps

### 1. Scaffold the solution

- Create a .NET 10 console project named `ExpressionEvaluator`.
- Create a test project named `ExpressionEvaluator.Tests`.
- Add both projects to a solution and reference the application project from the test project.
- Confirm the empty solution builds and tests run.

### 2. Define the expression model

- Add an abstract expression type.
- Add number and binary-operation expression types.
- Represent the four supported operations with an enum or another closed type.
- Ensure every binary operation requires exactly two child expressions.

### 3. Implement evaluation

- Recursively evaluate child expressions.
- Implement addition, multiplication, and integer division.
- Implement integer exponentiation without converting through floating-point arithmetic.
- Reject negative exponents because they cannot generally produce integer results.
- Preserve standard .NET behavior for arithmetic overflow unless a checked-arithmetic requirement is added.
- Surface division by zero as a clear evaluation error.

### 4. Implement infix formatting

- Format integer literals using invariant culture.
- Render negative literals in parentheses, such as `(-2)`, to match the required output.
- Map operations to `+`, `*`, `/`, and `^`.
- Wrap every binary operation in parentheses: `(left OP right)`.

### 5. Implement recursive-descent parsing

- Parse either a signed integer or a named operation.
- Recognize only `Sum`, `Mult`, `Div`, and `Exponent`.
- For an operation, require this grammar: `Name(expression, expression)`.
- Allow insignificant whitespace around tokens.
- Track the current character position so nested expressions can be parsed recursively.
- Require the entire input to be consumed after the root expression.
- Report useful errors for unknown operations, missing arguments, invalid integers, missing delimiters, unmatched parentheses, trailing input, and empty input.

Proposed grammar:

```text
expression := integer | operation
operation  := name "(" expression "," expression ")"
name       := "Sum" | "Mult" | "Div" | "Exponent"
integer    := ["-" | "+"] digit+
```

### 6. Wire the console entry point

- Read one expression from standard input.
- Parse, format, and evaluate it.
- Print `<formatted expression> = <result>`.
- On invalid input or evaluation failure, print a concise error to standard error and return a nonzero exit code.

### 7. Add automated tests

- Unit-test each operation with literal operands.
- Test all examples from `README.md` exactly, including nested and negative values.
- Test whitespace around names, delimiters, and values.
- Test deep left- and right-nested expressions.
- Test malformed expressions such as `Sum(3,)`, `Foo(1,2)`, missing parentheses, extra arguments, and trailing characters.
- Test division by zero, zero exponents, and negative exponents.
- Test integer boundary values where relevant.

### 8. Validate end to end

- Run `dotnet build` with no warnings introduced by the implementation.
- Run the complete automated test suite.
- Pipe every README example into the console application and compare the exact output.
- Verify invalid input produces a readable error and a nonzero exit code.

## Completion Criteria

- All four operations parse, format, and evaluate correctly.
- Nesting works recursively at arbitrary practical depth.
- Output matches every example in `README.md` exactly.
- Integer arithmetic is used throughout.
- Malformed input fails clearly instead of being partially accepted.
- The solution builds and all automated tests pass on .NET 10.

## Optional Follow-up Work

- Add `Sub`, `Mod`, or unary `Neg` operations.
- Add an interactive loop that processes expressions until EOF.
- Add a floating-point expression mode with separate numeric semantics.