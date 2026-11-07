using Avalonia.Controls;
using FifteenPuzzle.App.Views;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.Services;

public sealed class AvaloniaDialogService(Func<Window> ownerProvider) : IDialogService
{
    public Task<bool> ConfirmNewGameAsync(CancellationToken cancellationToken) =>
        new NewGameDialog().ShowDialog<bool>(ownerProvider());

    public async Task ShowCompletionAsync(
        ScoreEntry score,
        CancellationToken cancellationToken) =>
        await new CompletionDialog(score).ShowDialog(ownerProvider());

    public async Task ShowBestScoresAsync(
        LeaderboardSnapshot scores,
        CancellationToken cancellationToken) =>
        await new BestScoresDialog(scores).ShowDialog(ownerProvider());
}