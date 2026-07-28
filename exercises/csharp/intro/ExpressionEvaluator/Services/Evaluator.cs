using ExpressionEvaluator.Models;

namespace ExpressionEvaluator.Services;

public static class Evaluator
{
    public static int Evaluate(Expression expression) => expression switch
    {
        NumberExpression number => number.Value,
        BinaryExpression binary => EvaluateBinary(binary),
        _ => throw new EvaluationException("Unsupported expression type.")
    };

    // Recursively reduce both child trees to integers, then apply this node's
    // operator; guarded cases such as division by zero are handled first.
    private static int EvaluateBinary(BinaryExpression expression)
    {
        var left = Evaluate(expression.Left);
        var right = Evaluate(expression.Right);

        return expression.Operator switch
        {
            BinaryOperator.Sum => left + right,
            BinaryOperator.Mult => left * right,
            BinaryOperator.Div when right == 0 => throw new EvaluationException("Cannot divide by zero."),
            BinaryOperator.Div => left / right,
            BinaryOperator.Exponent => EvaluateExponent(left, right),
            _ => throw new EvaluationException($"Unsupported operator '{expression.Operator}'.")
        };
    }

    private static int EvaluateExponent(int baseValue, int exponent)
    {
        if (exponent < 0)
        {
            throw new EvaluationException("Negative exponents are not supported with integer arithmetic.");
        }

        var result = 1;
        var factor = baseValue;
        var remainingExponent = exponent;

        while (remainingExponent > 0)
        {
            if ((remainingExponent & 1) == 1)
            {
                result *= factor;
            }

            remainingExponent >>= 1;
            if (remainingExponent > 0)
            {
                factor *= factor;
            }
        }

        return result;
    }
}