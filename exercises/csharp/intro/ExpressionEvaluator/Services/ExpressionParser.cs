using System.Globalization;
using ExpressionEvaluator.Models;

namespace ExpressionEvaluator.Services;

public sealed class ExpressionParser
{
    private readonly string input;
    private int position;

    private ExpressionParser(string input)
    {
        this.input = input;
    }

    public static Expression Parse(string input)
    {
        ArgumentNullException.ThrowIfNull(input);

        var parser = new ExpressionParser(input);
        var expression = parser.ParseExpression();
        parser.SkipWhitespace();

        if (!parser.IsAtEnd)
        {
            throw parser.Error("Unexpected trailing input");
        }

        return expression;
    }

    private bool IsAtEnd => position >= input.Length;

    private Expression ParseExpression()
    {
        SkipWhitespace();

        if (IsAtEnd)
        {
            throw Error("Expected an expression");
        }

        if (input[position] is '+' or '-' || char.IsDigit(input[position]))
        {
            return ParseNumber();
        }

        if (char.IsLetter(input[position]))
        {
            return ParseOperation();
        }

        throw Error($"Unexpected character '{input[position]}'");
    }

    private NumberExpression ParseNumber()
    {
        var start = position;

        if (input[position] is '+' or '-')
        {
            position++;
        }

        var digitStart = position;
        while (!IsAtEnd && char.IsDigit(input[position]))
        {
            position++;
        }

        if (position == digitStart)
        {
            throw new ExpressionParseException("Expected digits after the sign", start);
        }

        var numberText = input.AsSpan(start, position - start);
        if (!int.TryParse(numberText, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var value))
        {
            throw new ExpressionParseException("Integer is outside the supported range", start);
        }

        return new NumberExpression(value);
    }

    private BinaryExpression ParseOperation()
    {
        var nameStart = position;
        while (!IsAtEnd && char.IsLetter(input[position]))
        {
            position++;
        }

        var name = input[nameStart..position];
        var binaryOperator = name switch
        {
            "Sum" => BinaryOperator.Sum,
            "Mult" => BinaryOperator.Mult,
            "Div" => BinaryOperator.Div,
            "Exponent" => BinaryOperator.Exponent,
            _ => throw new ExpressionParseException($"Unknown operation '{name}'", nameStart)
        };

        Expect('(');
        var left = ParseExpression();
        Expect(',');
        var right = ParseExpression();
        Expect(')');

        return new BinaryExpression(binaryOperator, left, right);
    }

    private void Expect(char expected)
    {
        SkipWhitespace();

        if (IsAtEnd || input[position] != expected)
        {
            throw Error($"Expected '{expected}'");
        }

        position++;
    }

    private void SkipWhitespace()
    {
        while (!IsAtEnd && char.IsWhiteSpace(input[position]))
        {
            position++;
        }
    }

    private ExpressionParseException Error(string message) => new(message, position);
}