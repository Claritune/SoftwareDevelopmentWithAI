namespace UrlMonitor;

public class Program
{
    public static int Main(string[] args)
    {
        // Parse CLI arguments
        var cliArgs = Config.ParseArgs(args);

        // Load config
        var config = Config.LoadConfig(cliArgs.ConfigPath);

        // Derive state file path
        var stateFilePath = cliArgs.StateFilePath
            ?? Config.DeriveStateFilePath(cliArgs.ConfigPath);

        // Handle --stats mode
        if (cliArgs.StatsOnly)
        {
            var store = State.LoadState(stateFilePath);
            Console.Write(Stats.FormatAllStats(store));
            return 0;
        }

        // Load and reconcile state
        var state = State.LoadState(stateFilePath);
        State.Reconcile(state, config);

        // Set up cancellation via Ctrl+C
        using var cts = new CancellationTokenSource();

        Console.CancelKeyPress += (sender, e) =>
        {
            e.Cancel = true; // Prevent immediate termination
            cts.Cancel();
        };

        // Run the monitoring loop
        Monitor.Run(config, state, stateFilePath, cliArgs.Verbose, cts.Token);

        return 0;
    }
}
