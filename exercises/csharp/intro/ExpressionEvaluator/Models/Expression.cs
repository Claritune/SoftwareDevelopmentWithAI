namespace ExpressionEvaluator.Models;

public abstract record Expression;

public sealed record NumberExpression(int Value) : Expression;

public sealed record BinaryExpression(
    BinaryOperator Operator,
    Expression Left,
    Expression Right) : Expression;

public enum BinaryOperator
{
    Sum,
    Mult,
    Div,
    Exponent
}