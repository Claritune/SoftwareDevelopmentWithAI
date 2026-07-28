using ExpressionEvaluator.Services;

namespace ExpressionEvaluator;

public static class Application
{
    public static int Run(TextReader input, TextWriter output, TextWriter error)
    {
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(output);
        ArgumentNullException.ThrowIfNull(error);

        var inputLine = input.ReadLine();
        if (inputLine is null)
        {
            error.WriteLine("Error: No expression was provided.");
            return 1;
        }

        try
        {
            var expression = ExpressionParser.Parse(inputLine);
            var formattedExpression = Formatter.Format(expression);
            var result = Evaluator.Evaluate(expression);

            output.WriteLine($"{formattedExpression} = {result}");
            return 0;
        }
        catch (ExpressionParseException exception)
        {
            error.WriteLine($"Error: {exception.Message}");
            return 1;
        }
        catch (EvaluationException exception)
        {
            error.WriteLine($"Error: {exception.Message}");
            return 1;
        }
        catch (OverflowException exception)
        {
            error.WriteLine($"Error: {exception.Message}");
            return 1;
        }
    }
}