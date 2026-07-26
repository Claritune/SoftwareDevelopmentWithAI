using ExpressionEvaluator;

if (args.Length > 0 && args[0] == "--test")
{
    RunTests();
    return;
}

var line = Console.ReadLine();
if (string.IsNullOrEmpty(line))
{
    Console.Error.WriteLine("Error: no input");
    Environment.Exit(1);
}

try
{
    var parser = new Parser(line);
    var expr = parser.Parse();
    Console.WriteLine($"{expr.Format()} = {expr.Evaluate()}");
}
catch (ParseError e)
{
    Console.Error.WriteLine($"Parse error: {e.Message}");
    Environment.Exit(1);
}
catch (Exception e)
{
    Console.Error.WriteLine($"Error: {e.Message}");
    Environment.Exit(1);
}

static void RunTests()
{
    int passed = 0;
    int failed = 0;

    void Check(string name, string input, string expectedFormat, int expectedValue)
    {
        try
        {
            var parser = new Parser(input);
            var expr = parser.Parse();
            var fmt = expr.Format();
            var val = expr.Evaluate();
            if (fmt == expectedFormat && val == expectedValue)
            {
                passed++;
            }
            else
            {
                failed++;
                Console.Error.WriteLine($"FAIL: {name}");
                Console.Error.WriteLine($"  input:           {input}");
                Console.Error.WriteLine($"  expected format:  {expectedFormat}");
                Console.Error.WriteLine($"  actual format:    {fmt}");
                Console.Error.WriteLine($"  expected value:   {expectedValue}");
                Console.Error.WriteLine($"  actual value:     {val}");
            }
        }
        catch (Exception e)
        {
            failed++;
            Console.Error.WriteLine($"FAIL: {name} (exception: {e.Message})");
        }
    }

    void CheckParseError(string name, string input)
    {
        try
        {
            var parser = new Parser(input);
            parser.Parse();
            failed++;
            Console.Error.WriteLine($"FAIL: {name} (expected ParseError, got none)");
        }
        catch (ParseError)
        {
            passed++;
        }
        catch (Exception e)
        {
            failed++;
            Console.Error.WriteLine($"FAIL: {name} (expected ParseError, got: {e.Message})");
        }
    }

    void CheckEvalError(string name, string input)
    {
        try
        {
            var parser = new Parser(input);
            var expr = parser.Parse();
            expr.Evaluate();
            failed++;
            Console.Error.WriteLine($"FAIL: {name} (expected evaluation error, got none)");
        }
        catch (Exception)
        {
            passed++;
        }
    }

    // --- Examples from the README ---
    Check("simple sum",       "Sum(3, 5)",                    "(3 + 5)",              8);
    Check("simple mult",      "Mult(4, 5)",                   "(4 * 5)",              20);
    Check("simple div",       "Div(10, 3)",                   "(10 / 3)",             3);
    Check("simple exponent",  "Exponent(2, 10)",              "(2 ^ 10)",             1024);
    Check("nested sum+exp",   "Sum(Exponent(3, 2), -2)",      "((3 ^ 2) + (-2))",     7);
    Check("nested exp+mult",  "Exponent(Mult(3, 2), 2)",      "((3 * 2) ^ 2)",        36);
    Check("nested sum+div",   "Sum(Mult(2, 3), Div(10, 2))",  "((2 * 3) + (10 / 2))", 11);
    Check("nested mult+sums", "Mult(Sum(1, 2), Sum(3, 4))",   "((1 + 2) * (3 + 4))",  21);
    Check("triple nested",    "Sum(Sum(Sum(1, 2), 3), 4)",    "(((1 + 2) + 3) + 4)",  10);

    // --- Edge cases: numbers ---
    Check("zero",             "Sum(0, 0)",        "(0 + 0)",         0);
    Check("negative numbers", "Sum(-3, -5)",       "((-3) + (-5))",   -8);
    Check("large exponent",   "Exponent(2, 0)",    "(2 ^ 0)",         1);
    Check("exponent base 0",  "Exponent(0, 5)",    "(0 ^ 5)",         0);
    Check("mult by zero",     "Mult(42, 0)",       "(42 * 0)",        0);
    Check("div truncation",   "Div(7, 2)",         "(7 / 2)",         3);
    Check("negative div",     "Div(-7, 2)",        "((-7) / 2)",      -3);

    // --- Whitespace handling ---
    Check("extra spaces",     "Sum( 3 , 5 )",       "(3 + 5)", 8);
    Check("no spaces",        "Sum(3,5)",            "(3 + 5)", 8);
    Check("tabs and spaces",  "Sum(\t3\t,\t5\t)",    "(3 + 5)", 8);
    Check("leading/trailing", "  Sum(3, 5)  ",       "(3 + 5)", 8);

    // --- Deep nesting ---
    Check("deep nesting",
          "Sum(Sum(Sum(Sum(1, 2), 3), 4), 5)",
          "((((1 + 2) + 3) + 4) + 5)",
          15);
    Check("mixed deep nesting",
          "Mult(Sum(1, 2), Exponent(Div(10, 5), 3))",
          "((1 + 2) * ((10 / 5) ^ 3))",
          24);

    // --- Error cases: parse errors ---
    CheckParseError("unknown function",    "Foo(1, 2)");
    CheckParseError("missing close paren", "Sum(3, 5");
    CheckParseError("missing comma",       "Sum(3 5)");
    CheckParseError("missing argument",    "Sum(3,)");
    CheckParseError("empty input",         "");
    CheckParseError("trailing garbage",    "Sum(3, 5) hello");
    CheckParseError("unmatched paren",     "Sum(3, 5))");
    CheckParseError("bare minus",          "-");
    CheckParseError("only open paren",     "(");

    // --- Error cases: evaluation errors ---
    CheckEvalError("division by zero",     "Div(10, 0)");
    CheckEvalError("negative exponent",    "Exponent(2, -1)");

    Console.WriteLine();
    Console.WriteLine($"{passed} passed, {failed} failed");
    Environment.Exit(failed > 0 ? 1 : 0);
}
