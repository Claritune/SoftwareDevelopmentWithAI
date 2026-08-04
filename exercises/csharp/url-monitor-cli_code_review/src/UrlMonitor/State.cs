using System.Text.Json;
using System.Text.Json.Serialization;

namespace UrlMonitor;

public class UrlState
{
    [JsonPropertyName("status")]
    public Status Status { get; set; } = Status.Unknown;

    [JsonPropertyName("last_checked")]
    public string LastChecked { get; set; } = "";

    [JsonPropertyName("stats")]
    public UrlStats Stats { get; set; } = new();
}

public class StateStore
{
    [JsonPropertyName("version")]
    public int Version { get; set; } = 1;

    [JsonPropertyName("urls")]
    public Dictionary<string, UrlState> Urls { get; set; } = new();
}

public static class State
{
    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        WriteIndented = true,
        Converters =
        {
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)
        }
    };

    private static readonly JsonSerializerOptions DeserializerOptions = new()
    {
        Converters =
        {
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase),
            new HttpStatusDictConverter(),
            new ErrorDictConverter()
        }
    };

    /// <summary>
    /// Load state from a JSON file. Returns empty state on missing or corrupt file.
    /// </summary>
    public static StateStore LoadState(string path)
    {
        if (!File.Exists(path))
        {
            return new StateStore();
        }

        try
        {
            var json = File.ReadAllText(path);
            var store = JsonSerializer.Deserialize<StateStore>(json, DeserializerOptions);

            return store ?? new StateStore();
        }
        catch (Exception ex)
        {
            Notifier.LogError($"Warning: corrupt state file, starting fresh: {ex.Message}");
            return new StateStore();
        }
    }

    /// <summary>
    /// Save state to a JSON file using atomic write (temp + rename).
    /// </summary>
    public static void SaveState(string path, StateStore store)
    {
        try
        {
            var json = JsonSerializer.Serialize(store, SerializerOptions);
            var tempPath = path + ".tmp";
            File.WriteAllText(tempPath, json);
            File.Move(tempPath, path, overwrite: true);
        }
        catch (Exception) { }
    }

    /// <summary>
    /// Reconcile state against the current config: add new URLs, drop removed ones.
    /// </summary>
    public static void Reconcile(StateStore store, MonitorConfig config)
    {
        var configUrls = new HashSet<string>(config.Urls.Select(u => u.Url));

        // Add new URLs
        foreach (var url in configUrls)
        {
            if (!store.Urls.ContainsKey(url))
            {
                store.Urls[url] = new UrlState();
            }
        }

        // Remove URLs no longer in config
        var toRemove = store.Urls.Keys.Where(k => !configUrls.Contains(k)).ToList();
        foreach (var key in toRemove)
        {
            store.Urls.Remove(key);
        }
    }
}

/// <summary>
/// Custom converter for Dictionary&lt;int, long&gt; that handles string keys from JSON.
/// </summary>
internal class HttpStatusDictConverter : JsonConverter<Dictionary<int, long>>
{
    public override Dictionary<int, long> Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var dict = new Dictionary<int, long>();

        if (reader.TokenType != JsonTokenType.StartObject)
            return dict;

        while (reader.Read())
        {
            if (reader.TokenType == JsonTokenType.EndObject)
                break;

            var key = int.Parse(reader.GetString()!);
            reader.Read();
            var value = reader.GetInt64();
            dict[key] = value;
        }

        return dict;
    }

    public override void Write(Utf8JsonWriter writer, Dictionary<int, long> value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();
        foreach (var (k, v) in value.OrderBy(kv => kv.Key))
        {
            writer.WriteNumber(k.ToString(), v);
        }
        writer.WriteEndObject();
    }
}

/// <summary>
/// Custom converter for Dictionary&lt;string, long&gt; for error counts.
/// </summary>
internal class ErrorDictConverter : JsonConverter<Dictionary<string, long>>
{
    public override Dictionary<string, long> Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var dict = new Dictionary<string, long>();

        if (reader.TokenType != JsonTokenType.StartObject)
            return dict;

        while (reader.Read())
        {
            if (reader.TokenType == JsonTokenType.EndObject)
                break;

            var key = reader.GetString()!;
            reader.Read();
            var value = reader.GetInt64();
            dict[key] = value;
        }

        return dict;
    }

    public override void Write(Utf8JsonWriter writer, Dictionary<string, long> value, JsonSerializerOptions options)
    {
        writer.WriteStartObject();
        foreach (var (k, v) in value.OrderBy(kv => kv.Key))
        {
            writer.WriteNumber(k, v);
        }
        writer.WriteEndObject();
    }
}
