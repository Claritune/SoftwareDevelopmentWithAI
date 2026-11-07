namespace FifteenPuzzle.App.ViewModels;

public sealed record TileViewModel(
    int Number,
    int Row,
    int Column,
    bool IsEmpty,
    bool CanMove,
    string AccessibleName)
{
    public string DisplayText => IsEmpty ? string.Empty : Number.ToString();
    public double Opacity => IsEmpty ? 0 : 1;
}