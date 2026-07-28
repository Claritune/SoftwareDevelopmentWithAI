namespace ExpressionEvaluator.Tests;

public class ApplicationTests
{
    [Theory]
    [InlineData("Sum(3, 5)", "(3 + 5) = 8")]
    [InlineData("Mult(4, 5)", "(4 * 5) = 20")]
    [InlineData("Div(10, 3)", "(10 / 3) = 3")]
    [InlineData("Exponent(2, 10)", "(2 ^ 10) = 1024")]
    [InlineData("Sum(Exponent(3, 2), -2)", "((3 ^ 2) + (-2)) = 7")]
    [InlineData("Exponent(Mult(3, 2), 2)", "((3 * 2) ^ 2) = 36")]
    [InlineData("Sum(Mult(2, 3), Div(10, 2))", "((2 * 3) + (10 / 2)) = 11")]
    [InlineData("Mult(Sum(1, 2), Sum(3, 4))", "((1 + 2) * (3 + 4)) = 21")]
    [InlineData("Sum(Sum(Sum(1, 2), 3), 4)", "(((1 + 2) + 3) + 4) = 10")]
    public void ProducesExpectedOutput(string input, string expectedOutput)
    {
        var output = new StringWriter();
        var error = new StringWriter();

        var exitCode = Application.Run(new StringReader(input), output, error);

        Assert.Equal(0, exitCode);
        Assert.Equal(expectedOutput + Environment.NewLine, output.ToString());
        Assert.Empty(error.ToString());
    }

    [Theory]
    [InlineData("Sum(3,)", "Error: Unexpected character ')' (position 6).")]
    [InlineData("Foo(1,2)", "Error: Unknown operation 'Foo' (position 0).")]
    [InlineData("Div(1, 0)", "Error: Cannot divide by zero.")]
    [InlineData("Exponent(2, -1)", "Error: Negative exponents are not supported with integer arithmetic.")]
    public void ReportsErrorsToStandardError(string input, string expectedError)
    {
        var output = new StringWriter();
        var error = new StringWriter();

        var exitCode = Application.Run(new StringReader(input), output, error);

        Assert.Equal(1, exitCode);
        Assert.Empty(output.ToString());
        Assert.Equal(expectedError + Environment.NewLine, error.ToString());
    }

    [Fact]
    public void ReportsMissingInputAtEndOfStream()
    {
        var output = new StringWriter();
        var error = new StringWriter();

        var exitCode = Application.Run(new StringReader(string.Empty), output, error);

        Assert.Equal(1, exitCode);
        Assert.Empty(output.ToString());
        Assert.Equal("Error: No expression was provided." + Environment.NewLine, error.ToString());
    }
}