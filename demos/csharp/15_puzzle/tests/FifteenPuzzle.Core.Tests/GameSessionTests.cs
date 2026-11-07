using FifteenPuzzle.Core;

namespace FifteenPuzzle.Core.Tests;

public sealed class GameSessionTests
{
    [Fact]
    public void InvalidFirstMoveDoesNotStartGame()
    {
        var (session, _) = CreateSession(AlmostSolved());

        var result = session.TryMoveTile(1);

        Assert.False(result.Moved);
        Assert.Equal(GameStatus.Ready, session.Status);
        Assert.Equal(0, session.MoveCount);
        Assert.False(session.HasActiveGame);
    }

    [Fact]
    public void LegalMoveStartsTimerAndIncrementsOnce()
    {
        var (session, clock) = CreateSession(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 0, 14, 15]);

        var result = session.TryMoveTile(14);
        clock.Advance(TimeSpan.FromSeconds(3));

        Assert.True(result.Moved);
        Assert.Equal(1, session.MoveCount);
        Assert.Equal(GameStatus.Running, session.Status);
        Assert.Equal(TimeSpan.FromSeconds(3), session.Elapsed);
        Assert.True(session.HasActiveGame);
    }

    [Fact]
    public void SolvingMoveStopsTimerAndBlocksFurtherMoves()
    {
        var (session, clock) = CreateSession(AlmostSolved());
        clock.Advance(TimeSpan.FromSeconds(1));

        var result = session.TryMoveTile(15);
        clock.Advance(TimeSpan.FromSeconds(10));
        var afterSolved = session.TryMoveTile(15);

        Assert.True(result.Moved);
        Assert.True(result.Solved);
        Assert.Equal(GameStatus.Solved, session.Status);
        Assert.Equal(1, session.MoveCount);
        Assert.Equal(TimeSpan.Zero, session.Elapsed);
        Assert.False(afterSolved.Moved);
    }

    [Fact]
    public void PauseAndResumeExcludeInactiveTime()
    {
        var (session, clock) = CreateSession(
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 0, 14, 15]);
        session.TryMoveTile(14);
        clock.Advance(TimeSpan.FromSeconds(2));

        session.Pause();
        clock.Advance(TimeSpan.FromSeconds(30));
        session.Resume();
        clock.Advance(TimeSpan.FromSeconds(4));

        Assert.Equal(TimeSpan.FromSeconds(6), session.Elapsed);
        Assert.Equal(GameStatus.Running, session.Status);
    }

    private static (GameSession Session, GameTimerTests.FakeClock Clock) CreateSession(
        int[] cells)
    {
        var clock = new GameTimerTests.FakeClock();
        var session = new GameSession(
            new FixedGenerator(cells),
            new GameTimer(clock));
        session.StartNewGame();
        return (session, clock);
    }

    private static int[] AlmostSolved() =>
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 15];

    private sealed class FixedGenerator(int[] cells) : IPuzzleGenerator
    {
        public PuzzleBoard Generate() => new(cells);
    }
}