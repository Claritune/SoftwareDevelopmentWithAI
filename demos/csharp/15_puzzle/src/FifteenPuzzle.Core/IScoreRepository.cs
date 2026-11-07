namespace FifteenPuzzle.Core;

public interface IScoreRepository
{
    Task<IReadOnlyList<ScoreEntry>> LoadAsync(CancellationToken cancellationToken);

    Task SaveAsync(
        IReadOnlyList<ScoreEntry> entries,
        CancellationToken cancellationToken);
}