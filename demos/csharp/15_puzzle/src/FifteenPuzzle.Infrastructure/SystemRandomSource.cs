using FifteenPuzzle.Core;

namespace FifteenPuzzle.Infrastructure;

public sealed class SystemRandomSource : IRandomSource
{
    private readonly Random _random = new();

    public int Next(int exclusiveUpperBound) => _random.Next(exclusiveUpperBound);
}