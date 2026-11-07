using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using FifteenPuzzle.App.Services;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.ViewModels;

public sealed partial class MainWindowViewModel : ViewModelBase
{
    private readonly GameSession _session;
    private readonly IScoreRepository _scoreRepository;
    private readonly IWallClock _wallClock;
    private readonly IDialogService _dialogs;
    private readonly HashSet<PauseReason> _pauseReasons = [];
    private Leaderboard _leaderboard = new([]);

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(MoveTileCommand))]
    [NotifyCanExecuteChangedFor(nameof(MoveDirectionCommand))]
    [NotifyCanExecuteChangedFor(nameof(NewGameCommand))]
    [NotifyCanExecuteChangedFor(nameof(ShowBestScoresCommand))]
    public partial bool IsInputEnabled { get; private set; } = true;

    [ObservableProperty]
    public partial IReadOnlyList<TileViewModel> Tiles { get; private set; } = [];

    [ObservableProperty]
    public partial int MoveCount { get; private set; }

    [ObservableProperty]
    public partial string ElapsedText { get; private set; } = "0:00";

    [ObservableProperty]
    public partial string StatusAnnouncement { get; private set; } = "Ready to play";

    public MainWindowViewModel(
        GameSession session,
        IScoreRepository scoreRepository,
        IWallClock wallClock,
        IDialogService dialogs)
    {
        _session = session;
        _scoreRepository = scoreRepository;
        _wallClock = wallClock;
        _dialogs = dialogs;

        var displayTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1),
        };
        displayTimer.Tick += (_, _) => ElapsedText = FormatElapsed(_session.Elapsed);
        displayTimer.Start();
    }

    public async Task InitializeAsync()
    {
        try
        {
            _leaderboard = new Leaderboard(
                await _scoreRepository.LoadAsync(CancellationToken.None));
        }
        catch
        {
            _leaderboard = new Leaderboard([]);
        }

        StartNewGame();
    }

    public void OnApplicationDeactivated()
    {
        _pauseReasons.Add(PauseReason.ApplicationInactive);
        _session.Pause();
        RefreshStatistics();
    }

    public void OnApplicationActivated()
    {
        _pauseReasons.Remove(PauseReason.ApplicationInactive);
        ResumeWhenUnpaused();
    }

    [RelayCommand(CanExecute = nameof(IsInputEnabled))]
    private async Task MoveTileAsync(int tileNumber) =>
        await ApplyMoveAsync(() => _session.TryMoveTile(tileNumber));

    [RelayCommand(CanExecute = nameof(IsInputEnabled))]
    private async Task MoveDirectionAsync(MoveDirection direction) =>
        await ApplyMoveAsync(() => _session.TryMove(direction));

    [RelayCommand(CanExecute = nameof(IsInputEnabled))]
    private async Task NewGameAsync()
    {
        if (!_session.HasActiveGame)
        {
            StartNewGame();
            return;
        }

        SetBusy(true);
        _pauseReasons.Add(PauseReason.NewGameConfirmation);
        _session.Pause();
        RefreshStatistics();

        try
        {
            if (await _dialogs.ConfirmNewGameAsync(CancellationToken.None))
            {
                StartNewGame();
            }
        }
        finally
        {
            _pauseReasons.Remove(PauseReason.NewGameConfirmation);
            ResumeWhenUnpaused();
            SetBusy(false);
        }
    }

    [RelayCommand(CanExecute = nameof(IsInputEnabled))]
    private async Task ShowBestScoresAsync()
    {
        SetBusy(true);
        try
        {
            await _dialogs.ShowBestScoresAsync(_leaderboard.Snapshot, CancellationToken.None);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async Task ApplyMoveAsync(Func<MoveResult> move)
    {
        if (!IsInputEnabled)
        {
            return;
        }

        var result = move();
        if (!result.Moved)
        {
            return;
        }

        RefreshBoard();
        RefreshStatistics();
        StatusAnnouncement = result.Solved ? "Puzzle solved" : "Game in progress";
        if (!result.Solved)
        {
            return;
        }

        SetBusy(true);
        var score = new ScoreEntry(result.Elapsed, result.MoveCount, _wallClock.UtcNow);
        _leaderboard.Add(score);
        try
        {
            await _scoreRepository.SaveAsync(_leaderboard.Entries, CancellationToken.None);
        }
        catch
        {
            StatusAnnouncement = "Puzzle solved. The score could not be saved.";
        }

        try
        {
            await _dialogs.ShowCompletionAsync(score, CancellationToken.None);
        }
        finally
        {
            SetBusy(false);
        }
    }

    private void StartNewGame()
    {
        _session.StartNewGame();
        StatusAnnouncement = "New puzzle ready";
        RefreshBoard();
        RefreshStatistics();
    }

    private void RefreshBoard()
    {
        Tiles = _session.Board.Cells.Select((number, index) =>
        {
            var row = index / PuzzleBoard.Size;
            var column = index % PuzzleBoard.Size;
            return new TileViewModel(
                number,
                row,
                column,
                number == 0,
                _session.Board.CanMoveTile(number),
                number == 0
                    ? $"Empty cell, row {row + 1}, column {column + 1}"
                    : $"Tile {number}, row {row + 1}, column {column + 1}");
        }).ToArray();
    }

    private void RefreshStatistics()
    {
        MoveCount = _session.MoveCount;
        ElapsedText = FormatElapsed(_session.Elapsed);
    }

    private void ResumeWhenUnpaused()
    {
        if (_pauseReasons.Count == 0)
        {
            _session.Resume();
        }
    }

    private void SetBusy(bool isBusy) => IsInputEnabled = !isBusy;

    public static string FormatElapsed(TimeSpan elapsed) =>
        elapsed.TotalHours >= 1
            ? $"{(int)elapsed.TotalHours}:{elapsed.Minutes:00}:{elapsed.Seconds:00}"
            : $"{(int)elapsed.TotalMinutes}:{elapsed.Seconds:00}";

    private enum PauseReason
    {
        ApplicationInactive,
        NewGameConfirmation,
    }
}