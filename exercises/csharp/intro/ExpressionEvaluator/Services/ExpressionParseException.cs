namespace ExpressionEvaluator.Services;

public sealed class ExpressionParseException : Exception
{
    public ExpressionParseException(string message, int position)
        : base($"{message} (position {position}).")
    {
        Position = position;
    }

    public int Position { get; }
}