using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.ViewModels;

public sealed class BestScoresViewModel
{
    public BestScoresViewModel(LeaderboardSnapshot snapshot)
    {
        FastestTimes = snapshot.FastestTimes.Select((entry, index) =>
            ScoreRowViewModel.FromEntry(index + 1, entry)).ToArray();
        FewestMoves = snapshot.FewestMoves.Select((entry, index) =>
            ScoreRowViewModel.FromEntry(index + 1, entry)).ToArray();
    }

    public IReadOnlyList<ScoreRowViewModel> FastestTimes { get; }
    public IReadOnlyList<ScoreRowViewModel> FewestMoves { get; }
    public bool HasFastestTimes => FastestTimes.Count > 0;
    public bool HasFewestMoves => FewestMoves.Count > 0;
}