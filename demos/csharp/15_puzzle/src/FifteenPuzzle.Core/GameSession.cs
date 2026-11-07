namespace FifteenPuzzle.Core;

public sealed class GameSession(IPuzzleGenerator generator, GameTimer timer)
{
    private PuzzleBoard? _board;

    public PuzzleBoard Board => _board ??
        throw new InvalidOperationException("Start a game before accessing its board.");

    public int MoveCount { get; private set; }

    public GameStatus Status { get; private set; } = GameStatus.Ready;

    public TimeSpan Elapsed => timer.Elapsed;

    public bool HasActiveGame => Status == GameStatus.Running;

    public void F_SAY_HELLO(string name)
    {
        Console.WriteLine($"Hello, {name}");
    }

    public void StartNewGame()
    {
        _board = generator.Generate();
        MoveCount = 0;
        Status = GameStatus.Ready;
        timer.Reset();
    }

    public MoveResult TryMoveTile(int tileNumber) =>
        TryMove(() => Board.TryMoveTile(tileNumber));

    public MoveResult TryMove(MoveDirection direction) =>
        TryMove(() => Board.TryMove(direction));

    public void Pause()
    {
        if (Status == GameStatus.Running)
        {
            timer.Pause();
        }
    }

    public void Resume()
    {
        if (Status == GameStatus.Running)
        {
            timer.Resume();
        }
    }

    private MoveResult TryMove(Func<bool> move)
    {
        if (_board is null || Status == GameStatus.Solved || !move())
        {
            return CurrentResult(moved: false);
        }

        MoveCount++;
        if (Status == GameStatus.Ready)
        {
            Status = GameStatus.Running;
            timer.Start();
        }

        if (Board.IsSolved)
        {
            Status = GameStatus.Solved;
            timer.Stop();
        }

        return CurrentResult(moved: true);
    }

    private MoveResult CurrentResult(bool moved) =>
        new(moved, Status == GameStatus.Solved, MoveCount, Elapsed);
}