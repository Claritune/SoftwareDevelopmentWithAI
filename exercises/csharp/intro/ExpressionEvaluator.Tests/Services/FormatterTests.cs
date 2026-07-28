using ExpressionEvaluator.Models;
using ExpressionEvaluator.Services;

namespace ExpressionEvaluator.Tests.Services;

public class FormatterTests
{
    [Fact]
    public void FormatsNestedExpressionWithNegativeLiteral()
    {
        var expression = new BinaryExpression(
            BinaryOperator.Sum,
            new BinaryExpression(
                BinaryOperator.Exponent,
                new NumberExpression(3),
                new NumberExpression(2)),
            new NumberExpression(-2));

        Assert.Equal("((3 ^ 2) + (-2))", Formatter.Format(expression));
    }

    [Theory]
    [InlineData(BinaryOperator.Sum, "+")]
    [InlineData(BinaryOperator.Mult, "*")]
    [InlineData(BinaryOperator.Div, "/")]
    [InlineData(BinaryOperator.Exponent, "^")]
    public void FormatsEachOperator(BinaryOperator binaryOperator, string symbol)
    {
        var expression = new BinaryExpression(
            binaryOperator,
            new NumberExpression(1),
            new NumberExpression(2));

        Assert.Equal($"(1 {symbol} 2)", Formatter.Format(expression));
    }
}