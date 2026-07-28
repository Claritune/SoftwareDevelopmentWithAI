using ExpressionEvaluator.Models;
using ExpressionEvaluator.Services;

namespace ExpressionEvaluator.Tests.Services;

public class ExpressionParserTests
{
    [Fact]
    public void ParsesNestedExpression()
    {
        var expression = ExpressionParser.Parse("Sum(Exponent(3, 2), -2)");

        var expected = new BinaryExpression(
            BinaryOperator.Sum,
            new BinaryExpression(
                BinaryOperator.Exponent,
                new NumberExpression(3),
                new NumberExpression(2)),
            new NumberExpression(-2));
        Assert.Equal(expected, expression);
    }

    [Theory]
    [InlineData("Sum(1, 2)", BinaryOperator.Sum)]
    [InlineData("Mult(1, 2)", BinaryOperator.Mult)]
    [InlineData("Div(1, 2)", BinaryOperator.Div)]
    [InlineData("Exponent(1, 2)", BinaryOperator.Exponent)]
    public void ParsesEachOperation(string input, BinaryOperator expectedOperator)
    {
        var expression = Assert.IsType<BinaryExpression>(ExpressionParser.Parse(input));

        Assert.Equal(expectedOperator, expression.Operator);
    }

    [Fact]
    public void AllowsWhitespaceAndExplicitPositiveSign()
    {
        var expression = ExpressionParser.Parse("  Sum ( +3 , Mult( 2, -4 ) )  ");

        Assert.Equal("(3 + (2 * (-4)))", Formatter.Format(expression));
    }

    [Theory]
    [InlineData("-2147483648", int.MinValue)]
    [InlineData("2147483647", int.MaxValue)]
    public void ParsesIntegerBoundaries(string input, int expected)
    {
        Assert.Equal(new NumberExpression(expected), ExpressionParser.Parse(input));
    }

    [Theory]
    [InlineData("", "Expected an expression")]
    [InlineData("   ", "Expected an expression")]
    [InlineData("Foo(1, 2)", "Unknown operation 'Foo'")]
    [InlineData("Sum(3,)", "Unexpected character ')'")]
    [InlineData("Sum(3 5)", "Expected ','")]
    [InlineData("Sum(3, 5", "Expected ')'")]
    [InlineData("Sum(3, 5) extra", "Unexpected trailing input")]
    [InlineData("Sum(1, 2, 3)", "Expected ')'")]
    [InlineData("2147483648", "Integer is outside the supported range")]
    [InlineData("-", "Expected digits after the sign")]
    public void RejectsMalformedInput(string input, string expectedMessage)
    {
        var exception = Assert.Throws<ExpressionParseException>(() => ExpressionParser.Parse(input));

        Assert.Contains(expectedMessage, exception.Message);
        Assert.Contains("position", exception.Message);
    }
}