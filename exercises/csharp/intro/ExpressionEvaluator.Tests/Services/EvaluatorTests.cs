using ExpressionEvaluator.Models;
using ExpressionEvaluator.Services;

namespace ExpressionEvaluator.Tests.Services;

public class EvaluatorTests
{
    [Theory]
    [InlineData(BinaryOperator.Sum, 3, 5, 8)]
    [InlineData(BinaryOperator.Mult, 4, 5, 20)]
    [InlineData(BinaryOperator.Div, 10, 3, 3)]
    [InlineData(BinaryOperator.Exponent, 2, 10, 1024)]
    public void EvaluatesEachOperator(BinaryOperator binaryOperator, int left, int right, int expected)
    {
        var expression = new BinaryExpression(
            binaryOperator,
            new NumberExpression(left),
            new NumberExpression(right));

        Assert.Equal(expected, Evaluator.Evaluate(expression));
    }

    [Fact]
    public void EvaluatesNestedExpressions()
    {
        var expression = new BinaryExpression(
            BinaryOperator.Sum,
            new BinaryExpression(
                BinaryOperator.Exponent,
                new NumberExpression(3),
                new NumberExpression(2)),
            new NumberExpression(-2));

        Assert.Equal(7, Evaluator.Evaluate(expression));
    }

    [Fact]
    public void ZeroExponentReturnsOne()
    {
        var expression = new BinaryExpression(
            BinaryOperator.Exponent,
            new NumberExpression(0),
            new NumberExpression(0));

        Assert.Equal(1, Evaluator.Evaluate(expression));
    }

    [Fact]
    public void DivisionByZeroThrowsClearError()
    {
        var expression = new BinaryExpression(
            BinaryOperator.Div,
            new NumberExpression(10),
            new NumberExpression(0));

        var exception = Assert.Throws<EvaluationException>(() => Evaluator.Evaluate(expression));

        Assert.Equal("Cannot divide by zero.", exception.Message);
    }

    [Fact]
    public void NegativeExponentThrowsClearError()
    {
        var expression = new BinaryExpression(
            BinaryOperator.Exponent,
            new NumberExpression(2),
            new NumberExpression(-1));

        var exception = Assert.Throws<EvaluationException>(() => Evaluator.Evaluate(expression));

        Assert.Equal("Negative exponents are not supported with integer arithmetic.", exception.Message);
    }
}