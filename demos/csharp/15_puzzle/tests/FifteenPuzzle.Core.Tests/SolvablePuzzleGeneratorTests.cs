using FifteenPuzzle.Core;

namespace FifteenPuzzle.Core.Tests;

public sealed class SolvablePuzzleGeneratorTests
{
    [Fact]
    public void GeneratesOneThousandValidSolvableUnsolvedBoards()
    {
        var generator = new SolvablePuzzleGenerator(new SeededRandomSource(20260902));

        for (var count = 0; count < 1_000; count++)
        {
            var board = generator.Generate();

            Assert.Equal(Enumerable.Range(0, 16), board.Cells.Order());
            Assert.False(board.IsSolved);
            Assert.True(IsSolvable(board.Cells));
        }
    }

    private static bool IsSolvable(IReadOnlyList<int> cells)
    {
        var inversions = cells
            .Where(value => value != 0)
            .SelectMany((left, index) => cells
                .Where(value => value != 0)
                .Skip(index + 1)
                .Select(right => left > right ? 1 : 0))
            .Sum();
        var emptyRowFromBottom = 4 - (cells.ToList().IndexOf(0) / 4);

        return emptyRowFromBottom % 2 == 1
            ? inversions % 2 == 0
            : inversions % 2 == 1;
    }

    private sealed class SeededRandomSource(int seed) : IRandomSource
    {
        private readonly Random _random = new(seed);

        public int Next(int exclusiveUpperBound) => _random.Next(exclusiveUpperBound);
    }
}