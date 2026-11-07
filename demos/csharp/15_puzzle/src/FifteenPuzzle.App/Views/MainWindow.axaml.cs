using Avalonia.Controls;
using Avalonia.Input;
using FifteenPuzzle.App.ViewModels;
using FifteenPuzzle.Core;

namespace FifteenPuzzle.App.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        KeyDown += OnKeyDown;
    }

    private void OnKeyDown(object? sender, KeyEventArgs eventArgs)
    {
        if (DataContext is not MainWindowViewModel viewModel)
        {
            return;
        }

        var direction = eventArgs.Key switch
        {
            Key.Up => MoveDirection.Up,
            Key.Down => MoveDirection.Down,
            Key.Left => MoveDirection.Left,
            Key.Right => MoveDirection.Right,
            _ => (MoveDirection?)null,
        };

        if (direction is not null && viewModel.MoveDirectionCommand.CanExecute(direction.Value))
        {
            viewModel.MoveDirectionCommand.Execute(direction.Value);
            eventArgs.Handled = true;
        }
    }
}