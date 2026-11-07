namespace FifteenPuzzle.Core;

public readonly record struct BoardPosition
{
    public BoardPosition(int row, int column)
    {
        if (row is < 0 or >= PuzzleBoard.Size)
        {
            throw new ArgumentOutOfRangeException(nameof(row));
        }

        if (column is < 0 or >= PuzzleBoard.Size)
        {
            throw new ArgumentOutOfRangeException(nameof(column));
        }

        Row = row;
        Column = column;
    }

    public int Row { get; }

    public int Column { get; }
}