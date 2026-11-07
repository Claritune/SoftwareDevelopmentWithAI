using FifteenPuzzle.Core;

namespace FifteenPuzzle.Core.Tests;

public sealed class PuzzleBoardTests
{
    [Fact]
    public void ConstructorRejectsMalformedBoards()
    {
        Assert.Throws<ArgumentException>(() => new PuzzleBoard(Enumerable.Range(0, 15)));
        Assert.Throws<ArgumentException>(() => new PuzzleBoard(Enumerable.Range(0, 17)));
        Assert.Throws<ArgumentException>(() => new PuzzleBoard(new int[16]));
        Assert.Throws<ArgumentException>(() => new PuzzleBoard(Enumerable.Range(1, 16)));
    }

    [Fact]
    public void CellsReturnsSnapshotThatCannotChangeBoard()
    {
        var board = new PuzzleBoard(SolvedCells());
        var snapshot = board.Cells;

        board.TryMoveTile(15);

        Assert.Equal(0, snapshot[15]);
        Assert.Equal(15, board.Cells[15]);
    }

    [Theory]
    [InlineData(11, true)]
    [InlineData(14, true)]
    [InlineData(10, false)]
    [InlineData(0, false)]
    [InlineData(99, false)]
    public void OnlyOrthogonallyAdjacentTilesCanMove(int tile, bool expected)
    {
        var board = new PuzzleBoard(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 15]);

        Assert.Equal(expected, board.CanMoveTile(tile));
    }

    [Fact]
    public void InvalidMovePreservesBoard()
    {
        var board = new PuzzleBoard(SolvedCells());
        var before = board.Cells;

        Assert.False(board.TryMoveTile(1));
        Assert.Equal(before, board.Cells);
        Assert.True(board.IsSolved);
    }

    [Theory]
    [InlineData(MoveDirection.Up, 15)]
    [InlineData(MoveDirection.Down, 7)]
    [InlineData(MoveDirection.Left, 11)]
    [InlineData(MoveDirection.Right, 10)]
    public void DirectionDescribesTileMovement(MoveDirection direction, int expectedTile)
    {
        var board = new PuzzleBoard(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0, 11, 13, 14, 15, 12]);

        Assert.True(board.TryMove(direction));
        Assert.Equal(expectedTile, board.Cells[10]);
    }

    [Fact]
    public void SolvedDetectionRequiresCanonicalOrder()
    {
        Assert.True(new PuzzleBoard(SolvedCells()).IsSolved);
        Assert.False(new PuzzleBoard(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 15]).IsSolved);
    }

    private static int[] SolvedCells() =>
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0];
}