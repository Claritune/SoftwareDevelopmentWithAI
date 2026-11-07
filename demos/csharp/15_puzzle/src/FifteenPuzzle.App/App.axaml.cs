using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using FifteenPuzzle.App.Services;
using FifteenPuzzle.App.ViewModels;
using FifteenPuzzle.App.Views;
using FifteenPuzzle.Core;
using FifteenPuzzle.Infrastructure;
using Microsoft.Extensions.Logging.Abstractions;

namespace FifteenPuzzle.App;

public partial class App : Application
{
    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var window = new MainWindow();
            var repository = new JsonScoreRepository(
                new MacOsAppDataPathProvider(),
                NullLogger<JsonScoreRepository>.Instance);
            var session = new GameSession(
                new SolvablePuzzleGenerator(new SystemRandomSource()),
                new GameTimer(new SystemMonotonicClock()));
            var viewModel = new MainWindowViewModel(
                session,
                repository,
                new SystemWallClock(),
                new AvaloniaDialogService(() => window));

            window.DataContext = viewModel;
            desktop.MainWindow = window;

            if (desktop is IActivatableLifetime activatable)
            {
                activatable.Deactivated += (_, _) => viewModel.OnApplicationDeactivated();
                activatable.Activated += (_, _) => viewModel.OnApplicationActivated();
            }

            window.Opened += async (_, _) => await viewModel.InitializeAsync();
        }

        base.OnFrameworkInitializationCompleted();
    }
}