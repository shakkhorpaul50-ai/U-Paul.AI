using System.Diagnostics;
using System.Net.Http.Json;
using System.Text.Json;

namespace UPaulAi.Services;

/// <summary>HTTP client for llama-server (prebuilt llama.cpp binary) /completion API.</summary>
public sealed class LlamaClient(HttpClient http, ILogger<LlamaClient> log)
{
    public async Task<(string Text, long Ms)> CompleteAsync(
        string prompt, int maxTokens, CancellationToken ct)
    {
        var payload = new
        {
            prompt,
            n_predict = maxTokens,
            temperature = 0.7,
            top_p = 0.9,
            stop = new[] { "<|im_end|>" },
            stream = false
        };
        var sw = Stopwatch.StartNew();
        using var res = await http.PostAsJsonAsync("/completion", payload, ct);
        res.EnsureSuccessStatusCode();
        using var doc = await res.Content.ReadFromJsonAsync<JsonDocument>(ct);
        var text = doc is null ? "" :
            doc.RootElement.GetProperty("content").GetString()?.Trim() ?? "";
        return (text, sw.ElapsedMilliseconds);
    }

    public async Task<bool> IsUpAsync(CancellationToken ct)
    {
        try
        {
            using var res = await http.GetAsync("/health", ct);
            return res.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            log.LogDebug(ex, "llama-server not reachable");
            return false;
        }
    }
}
