using Avalonia.Controls;
using FifteenPuzzle.App.ViewModels;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.Views;

public partial class CompletionDialog : Window
{
    public CompletionDialog()
    {
        InitializeComponent();
    }

    public CompletionDialog(ScoreEntry score) : this()
    {
        TimeText.Text = MainWindowViewModel.FormatElapsed(score.Elapsed);
        MovesText.Text = score.MoveCount.ToString();
        DoneButton.Click += (_, _) => Close();
        Opened += (_, _) => DoneButton.Focus();
    }
}