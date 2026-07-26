namespace ExpressionEvaluator;

public class ParseError : Exception
{
    public ParseError(string message) : base(message) { }
}

public class Parser
{
    private readonly ReadOnlyMemory<char> _input;
    private int _pos;

    public Parser(string input)
    {
        _input = input.AsMemory();
        _pos = 0;
    }

    public Expr Parse()
    {
        SkipWhitespace();
        var expr = ParseExpr();
        SkipWhitespace();
        if (!AtEnd)
            throw new ParseError($"unexpected trailing characters at position {_pos}");
        return expr;
    }

    private Expr ParseExpr()
    {
        SkipWhitespace();
        if (AtEnd)
            throw new ParseError("unexpected end of input");

        char c = Peek;

        if (c == '-')
        {
            if (_pos + 1 < _input.Length && char.IsDigit(_input.Span[_pos + 1]))
                return ParseNumber();
            throw new ParseError($"unexpected '-' at position {_pos}");
        }

        if (char.IsDigit(c))
            return ParseNumber();

        if (char.IsLetter(c))
            return ParseFunctionCall();

        throw new ParseError($"unexpected character '{c}' at position {_pos}");
    }

    private Expr ParseNumber()
    {
        SkipWhitespace();
        int start = _pos;
        if (Peek == '-')
            Advance();
        if (AtEnd || !char.IsDigit(Peek))
            throw new ParseError($"expected digit at position {_pos}");
        while (!AtEnd && char.IsDigit(Peek))
            Advance();
        var numStr = _input.Span[start.._pos];
        return new NumberExpr(int.Parse(numStr));
    }

    private Expr ParseFunctionCall()
    {
        var name = ReadIdentifier();
        var op = IdentifierToOp(name);

        SkipWhitespace();
        Expect('(');

        var left = ParseExpr();

        SkipWhitespace();
        Expect(',');

        var right = ParseExpr();

        SkipWhitespace();
        Expect(')');

        return new BinaryOpExpr(op, left, right);
    }

    private void SkipWhitespace()
    {
        while (!AtEnd && char.IsWhiteSpace(_input.Span[_pos]))
            _pos++;
    }

    private char Peek
    {
        get
        {
            if (AtEnd) throw new ParseError("unexpected end of input");
            return _input.Span[_pos];
        }
    }

    private char Advance()
    {
        char c = Peek;
        _pos++;
        return c;
    }

    private void Expect(char c)
    {
        SkipWhitespace();
        if (AtEnd)
            throw new ParseError($"expected '{c}' but reached end of input");
        if (Peek != c)
            throw new ParseError($"expected '{c}' but got '{Peek}' at position {_pos}");
        Advance();
    }

    private bool AtEnd => _pos >= _input.Length;

    private ReadOnlySpan<char> ReadIdentifier()
    {
        SkipWhitespace();
        int start = _pos;
        while (!AtEnd && char.IsLetter(_input.Span[_pos]))
            _pos++;
        if (start == _pos)
            throw new ParseError($"expected identifier at position {_pos}");
        return _input.Span[start.._pos];
    }

    private static OpType IdentifierToOp(ReadOnlySpan<char> name)
    {
        if (name.SequenceEqual("Sum")) return OpType.Sum;
        if (name.SequenceEqual("Mult")) return OpType.Mult;
        if (name.SequenceEqual("Div")) return OpType.Div;
        if (name.SequenceEqual("Exponent")) return OpType.Exponent;
        throw new ParseError($"unknown function: {name}");
    }
}
