using Avalonia.Controls;
using Avalonia.Input;
using FifteenPuzzle.App.ViewModels;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.Views;

public partial class BestScoresDialog : Window
{
    public BestScoresDialog() : this(new LeaderboardSnapshot([], []))
    {
    }

    public BestScoresDialog(LeaderboardSnapshot snapshot)
    {
        InitializeComponent();
        DataContext = new BestScoresViewModel(snapshot);
        CloseButton.Click += (_, _) => Close();
        KeyDown += (_, eventArgs) =>
        {
            if (eventArgs.Key == Key.Escape)
            {
                Close();
                eventArgs.Handled = true;
            }
        };
        Opened += (_, _) => CloseButton.Focus();
    }
}