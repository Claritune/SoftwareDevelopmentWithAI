using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.ViewModels;

public sealed record ScoreRowViewModel(int Rank, string Time, string Moves, string Date)
{
    public static ScoreRowViewModel FromEntry(int rank, ScoreEntry entry) => new(
        rank,
        MainWindowViewModel.FormatElapsed(entry.Elapsed),
        entry.MoveCount.ToString(),
        entry.CompletedAtUtc.ToLocalTime().ToString("MMM d, yyyy"));
}