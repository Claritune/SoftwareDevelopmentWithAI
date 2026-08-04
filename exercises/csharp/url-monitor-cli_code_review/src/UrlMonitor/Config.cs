using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace UrlMonitor;

public record UrlSpec(string Url, int TimeoutSeconds = 10);

public class MonitorConfig
{
    public int CheckIntervalSeconds { get; set; } = 30;
    public List<UrlSpec> Urls { get; set; } = new();
}

public record CliArgs(
    string ConfigPath,
    string? StateFilePath,
    bool Verbose,
    bool StatsOnly
);

public static class Config
{
    public static CliArgs ParseArgs(string[] args)
    {
        string configPath = "config.yaml";
        string? stateFilePath = null;
        bool verbose = false;
        bool statsOnly = false;

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--config":
                    if (i + 1 >= args.Length)
                    {
                        Console.Error.WriteLine("Error: --config requires a value");
                        Environment.Exit(2);
                    }
                    configPath = args[++i];
                    break;

                case "--state-file":
                    if (i + 1 >= args.Length)
                    {
                        Console.Error.WriteLine("Error: --state-file requires a value");
                        Environment.Exit(2);
                    }
                    stateFilePath = args[++i];
                    break;

                case "--verbose":
                    verbose = true;
                    break;

                case "--stats":
                    statsOnly = true;
                    break;

                case "--help":
                    PrintUsage();
                    Environment.Exit(0);
                    break;

                default:
                    Console.Error.WriteLine($"Error: unknown argument '{args[i]}'");
                    PrintUsage();
                    Environment.Exit(2);
                    break;
            }
        }

        return new CliArgs(configPath, stateFilePath, verbose, statsOnly);
    }

    public static string DeriveStateFilePath(string configPath)
    {
        var dir = Path.GetDirectoryName(configPath) ?? ".";
        var name = Path.GetFileNameWithoutExtension(configPath);
        return Path.Combine(dir, $"{name}.state.json");
    }

    public static MonitorConfig LoadConfig(string path)
    {
        if (!File.Exists(path))
        {
            Console.Error.WriteLine($"Error: config file not found: {path}");
            Environment.Exit(1);
        }

        string yaml;
        try
        {
            yaml = File.ReadAllText(path);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error: cannot read config file: {ex.Message}");
            Environment.Exit(1);
            return null!; // unreachable
        }

        var deserializer = new DeserializerBuilder()
            .WithNamingConvention(UnderscoredNamingConvention.Instance)
            .Build();

        YamlConfigDocument doc;
        try
        {
            doc = deserializer.Deserialize<YamlConfigDocument>(yaml);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Error: invalid YAML in config: {ex.Message}");
            Environment.Exit(1);
            return null!; // unreachable
        }

        var config = new MonitorConfig
        {
            CheckIntervalSeconds = doc.CheckIntervalSeconds,
            Urls = doc.Urls.Select(u => new UrlSpec(u.Url, u.TimeoutSeconds)).ToList()
        };

        Validate(config);
        return config;
    }

    private static void Validate(MonitorConfig config)
    {
        if (config.CheckIntervalSeconds < 5)
        {
            Console.Error.WriteLine("Error: check_interval_seconds must be >= 5");
            Environment.Exit(1);
        }

        if (config.Urls.Count == 0)
        {
            Console.Error.WriteLine("Error: urls list must not be empty");
            Environment.Exit(1);
        }

        foreach (var url in config.Urls)
        {
            if (url.TimeoutSeconds < 1)
            {
                Console.Error.WriteLine($"Error: timeout_seconds must be >= 1 for {url.Url}");
                Environment.Exit(1);
            }
        }
    }

    private static void PrintUsage()
    {
        Console.WriteLine("Usage: url-monitor --config <path> [--state-file <path>] [--verbose] [--stats] [--help]");
        Console.WriteLine();
        Console.WriteLine("Options:");
        Console.WriteLine("  --config <path>       Path to YAML config file (default: config.yaml)");
        Console.WriteLine("  --state-file <path>   Path to state JSON file (default: derived from config)");
        Console.WriteLine("  --verbose             Log every check, not just transitions");
        Console.WriteLine("  --stats               Print accumulated stats and exit");
        Console.WriteLine("  --help                Show this help message");
    }
}

// Internal YAML deserialization model
internal class YamlConfigDocument
{
    public int CheckIntervalSeconds { get; set; } = 30;
    public List<YamlUrlEntry> Urls { get; set; } = new();
}

internal class YamlUrlEntry
{
    public string Url { get; set; } = "";
    public int TimeoutSeconds { get; set; } = 10;
}
