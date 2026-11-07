namespace FifteenPuzzle.Core;

public sealed class PuzzleBoard
{
    public const int Size = 4;
    private const int CellCount = Size * Size;
    private readonly int[] _cells;
    private int _emptyIndex;

    public PuzzleBoard(IEnumerable<int> cells)
    {
        ArgumentNullException.ThrowIfNull(cells);

        _cells = cells.ToArray();
        if (_cells.Length != CellCount ||
            _cells.Any(value => value is < 0 or >= CellCount) ||
            _cells.Distinct().Count() != CellCount)
        {
            throw new ArgumentException(
                $"A board must contain every value from 0 through {CellCount - 1} exactly once.",
                nameof(cells));
        }

        _emptyIndex = Array.IndexOf(_cells, 0);
    }

    public IReadOnlyList<int> Cells => Array.AsReadOnly((int[])_cells.Clone());

    public BoardPosition EmptyPosition => PositionFromIndex(_emptyIndex);

    public bool IsSolved
    {
        get
        {
            for (var index = 0; index < CellCount - 1; index++)
            {
                if (_cells[index] != index + 1)
                {
                    return false;
                }
            }

            return _cells[^1] == 0;
        }
    }

    public bool CanMoveTile(int tileNumber)
    {
        var tileIndex = Array.IndexOf(_cells, tileNumber);
        if (tileNumber == 0 || tileIndex < 0)
        {
            return false;
        }

        var tilePosition = PositionFromIndex(tileIndex);
        var emptyPosition = EmptyPosition;
        return Math.Abs(tilePosition.Row - emptyPosition.Row) +
            Math.Abs(tilePosition.Column - emptyPosition.Column) == 1;
    }

    public bool TryMoveTile(int tileNumber)
    {
        if (!CanMoveTile(tileNumber))
        {
            return false;
        }

        var tileIndex = Array.IndexOf(_cells, tileNumber);
        _cells[_emptyIndex] = tileNumber;
        _cells[tileIndex] = 0;
        _emptyIndex = tileIndex;
        return true;
    }

    public bool TryMove(MoveDirection direction)
    {
        var empty = EmptyPosition;
        var source = direction switch
        {
            MoveDirection.Up => (Row: empty.Row + 1, Column: empty.Column),
            MoveDirection.Down => (Row: empty.Row - 1, Column: empty.Column),
            MoveDirection.Left => (Row: empty.Row, Column: empty.Column + 1),
            MoveDirection.Right => (Row: empty.Row, Column: empty.Column - 1),
            _ => throw new ArgumentOutOfRangeException(nameof(direction)),
        };

        if (source.Row is < 0 or >= Size || source.Column is < 0 or >= Size)
        {
            return false;
        }

        return TryMoveTile(_cells[(source.Row * Size) + source.Column]);
    }

    private static BoardPosition PositionFromIndex(int index) =>
        new(index / Size, index % Size);
}