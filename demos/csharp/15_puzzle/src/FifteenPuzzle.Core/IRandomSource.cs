namespace FifteenPuzzle.Core;

public interface IRandomSource
{
    int Next(int exclusiveUpperBound);
}