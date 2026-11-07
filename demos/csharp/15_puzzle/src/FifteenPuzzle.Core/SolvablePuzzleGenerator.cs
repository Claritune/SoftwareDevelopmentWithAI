namespace FifteenPuzzle.Core;

public sealed class SolvablePuzzleGenerator(IRandomSource random) : IPuzzleGenerator
{
    public PuzzleBoard Generate()
    {
        while (true)
        {
            var cells = Enumerable.Range(0, PuzzleBoard.Size * PuzzleBoard.Size).ToArray();
            Shuffle(cells);

            var board = new PuzzleBoard(cells);
            if (!board.IsSolved && IsSolvable(cells))
            {
                return board;
            }
        }
    }

    private void Shuffle(int[] cells)
    {
        for (var index = cells.Length - 1; index > 0; index--)
        {
            var otherIndex = random.Next(index + 1);
            (cells[index], cells[otherIndex]) = (cells[otherIndex], cells[index]);
        }
    }

    private static bool IsSolvable(IReadOnlyList<int> cells)
    {
        var inversions = 0;
        for (var left = 0; left < cells.Count; left++)
        {
            if (cells[left] == 0)
            {
                continue;
            }

            for (var right = left + 1; right < cells.Count; right++)
            {
                if (cells[right] != 0 && cells[left] > cells[right])
                {
                    inversions++;
                }
            }
        }

        var emptyIndex = cells.IndexOf(0);
        var emptyRowFromBottom = PuzzleBoard.Size - (emptyIndex / PuzzleBoard.Size);
        return emptyRowFromBottom % 2 == 1
            ? inversions % 2 == 0
            : inversions % 2 == 1;
    }
}

file static class ReadOnlyListExtensions
{
    public static int IndexOf<T>(this IReadOnlyList<T> values, T value)
    {
        for (var index = 0; index < values.Count; index++)
        {
            if (EqualityComparer<T>.Default.Equals(values[index], value))
            {
                return index;
            }
        }

        return -1;
    }
}