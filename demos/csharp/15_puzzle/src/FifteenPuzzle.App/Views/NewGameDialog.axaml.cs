using Avalonia.Controls;
using Avalonia.Input;

namespace FifteenPuzzle.App.Views;

public partial class NewGameDialog : Window
{
    public NewGameDialog()
    {
        InitializeComponent();
        CancelButton.Click += (_, _) => Close(false);
        ContinueButton.Click += (_, _) => Close(true);
        KeyDown += OnKeyDown;
        Opened += (_, _) => CancelButton.Focus();
    }

    private void OnKeyDown(object? sender, KeyEventArgs eventArgs)
    {
        if (eventArgs.Key == Key.Escape)
        {
            Close(false);
            eventArgs.Handled = true;
        }
    }

}