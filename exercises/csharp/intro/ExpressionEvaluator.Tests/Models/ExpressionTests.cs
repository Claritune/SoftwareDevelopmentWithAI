using ExpressionEvaluator.Models;

namespace ExpressionEvaluator.Tests.Models;

public class ExpressionTests
{
    [Fact]
    public void NumberExpressionStoresValue()
    {
        var expression = new NumberExpression(-7);

        Assert.Equal(-7, expression.Value);
    }

    [Fact]
    public void BinaryExpressionStoresOperatorAndChildren()
    {
        var left = new NumberExpression(3);
        var right = new NumberExpression(5);

        var expression = new BinaryExpression(BinaryOperator.Sum, left, right);

        Assert.Equal(BinaryOperator.Sum, expression.Operator);
        Assert.Same(left, expression.Left);
        Assert.Same(right, expression.Right);
    }
}