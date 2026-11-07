namespace FifteenPuzzle.Infrastructure;

public sealed class MacOsAppDataPathProvider : IAppDataPathProvider
{
    public string ScoreFilePath { get; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "FifteenPuzzle",
        "scores.json");
}