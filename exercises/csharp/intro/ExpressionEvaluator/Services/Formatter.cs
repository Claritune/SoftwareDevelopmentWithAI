using System.Globalization;
using ExpressionEvaluator.Models;

namespace ExpressionEvaluator.Services;

public static class Formatter
{
    public static string Format(Expression expression) => expression switch
    {
        NumberExpression { Value: < 0 } number => $"({number.Value.ToString(CultureInfo.InvariantCulture)})",
        NumberExpression number => number.Value.ToString(CultureInfo.InvariantCulture),
        BinaryExpression binary => $"({Format(binary.Left)} {GetSymbol(binary.Operator)} {Format(binary.Right)})",
        _ => throw new ArgumentException("Unsupported expression type.", nameof(expression))
    };

    private static string GetSymbol(BinaryOperator binaryOperator) => binaryOperator switch
    {
        BinaryOperator.Sum => "+",
        BinaryOperator.Mult => "*",
        BinaryOperator.Div => "/",
        BinaryOperator.Exponent => "^",
        _ => throw new ArgumentOutOfRangeException(nameof(binaryOperator), binaryOperator, "Unsupported operator.")
    };
}