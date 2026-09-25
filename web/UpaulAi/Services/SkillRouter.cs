namespace UPaulAi.Services;

/// <summary>SFW skill routing + system prompts. Port of gateway/router.py (SFW path only).</summary>
public sealed class SkillRouter
{
    public const string Builder = "Shakkhor Paul";
    public const string CreatorGh = "https://github.com/shakkhorpaul50-ai/";
    public const string CreatorFb = "https://www.facebook.com/profile.php?id=100023479221437";

    private static readonly string[] RefuseHints =
        ["porn", "xxx", "hentai", "nude", "nudity", "erotic", "fetish", "bdsm"];

    public (string Skill, double Confidence) DetectSkill(string prompt)
    {
        var p = prompt.ToLowerInvariant();
        if (p.Contains("def ") || p.Contains("import ") || p.Contains("```")
            || p.Contains("function ") || p.Contains("traceback"))
            return ("code", 0.8);
        if (prompt.Any(ch => ch is >= '\u0980' and <= '\u09ff'))
        {
            if (p.Contains("kobita") || p.Contains("golpo") || p.Contains("gaan")
                || p.Contains("lyrics") || p.Contains("poem") || p.Contains("story") || p.Contains("song"))
                return ("creative_bn", 0.8);
            return ("bangla", 0.7);
        }
        if (p.Contains("poem") || p.Contains("story") || p.Contains("song")
            || p.Contains("lyrics") || p.Contains("kobita") || p.Contains("golpo"))
            return ("creative_en", 0.75);
        return ("english", 0.6);
    }

    public bool ShouldRefuse(string prompt)
    {
        var p = prompt.ToLowerInvariant();
        return RefuseHints.Any(h => p.Contains(h));
    }

    public string Refusal() =>
        "I can't help with that. I'm here for friendly chat, stories, poems, songs, and coding help — " +
        "tell me what's on your mind and we'll talk it through.";

    public string SystemPrompt(string skill, string role)
    {
        var ident = $"You are U_Paul-AI, built from scratch by {Builder} " +
                    $"(GitHub: {CreatorGh}). Never claim any other maker. ";
        var style = IsSpecial(role) ? "Long detailed answer." : "Short answer, max 80 tokens.";
        var task = skill switch
        {
            "code" => "You are a coding tutor. Answer with code then brief explanation.",
            "bangla" => "Reply in Bangla.",
            "creative_bn" => "You are a Bangla poet/storyteller. Keep requested form and length.",
            "creative_en" => "You are a poet/storyteller. Keep requested form and length.",
            _ => "You are a helpful assistant."
        };
        return ident + task + " " + style +
               " If a request is sexual or violent, decline and offer a caring alternative instead.";
    }

    public string BuildPrompt(string system, string user) =>
        $"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n";

    public int MaxTokens(string role) => IsSpecial(role) ? 250 : 80;

    public static bool IsSpecial(string role) =>
        role is "creator" or "debi" or "friend";
}
