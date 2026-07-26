namespace ExpressionEvaluator;

public enum OpType { Sum, Mult, Div, Exponent }

public abstract record Expr
{
    public abstract int Evaluate();
    public abstract string Format();
}

public sealed record NumberExpr(int Value) : Expr
{
    public override int Evaluate() => Value;

    public override string Format() =>
        Value < 0 ? $"({Value})" : Value.ToString();
}

public sealed record BinaryOpExpr(OpType Op, Expr Left, Expr Right) : Expr
{
    public override int Evaluate()
    {
        int l = Left.Evaluate();
        int r = Right.Evaluate();
        return Op switch
        {
            OpType.Sum => l + r,
            OpType.Mult => l * r,
            OpType.Div => r == 0
                ? throw new InvalidOperationException("division by zero")
                : l / r,
            OpType.Exponent => r < 0
                ? throw new InvalidOperationException("negative exponent not supported")
                : IntPow(l, r),
            _ => throw new InvalidOperationException($"unknown op: {Op}")
        };
    }

    public override string Format()
    {
        char symbol = Op switch
        {
            OpType.Sum => '+',
            OpType.Mult => '*',
            OpType.Div => '/',
            OpType.Exponent => '^',
            _ => throw new InvalidOperationException($"unknown op: {Op}")
        };
        return $"({Left.Format()} {symbol} {Right.Format()})";
    }

    private static int IntPow(int @base, int exp)
    {
        int result = 1;
        for (int i = 0; i < exp; i++)
            result *= @base;
        return result;
    }
}
