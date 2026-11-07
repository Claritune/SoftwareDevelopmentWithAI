using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.Services;

public interface IDialogService
{
    Task<bool> ConfirmNewGameAsync(CancellationToken cancellationToken);
    Task ShowCompletionAsync(ScoreEntry score, CancellationToken cancellationToken);
    Task ShowBestScoresAsync(LeaderboardSnapshot scores, CancellationToken cancellationToken);
}