using Microsoft.AspNetCore.Identity;
using UPaulAi.Models;

namespace UPaulAi.Services;

/// <summary>Special-tier roles. Membership comes from config email lists, never baked into the model.</summary>
public sealed class RoleSeeder(
    RoleManager<IdentityRole> roles,
    UserManager<AppUser> users,
    IConfiguration cfg)
{
    public static readonly string[] All = ["creator", "debi", "friend"];

    public async Task EnsureRolesAsync()
    {
        foreach (var r in All)
            if (!await roles.RoleExistsAsync(r))
                await roles.CreateAsync(new IdentityRole(r));
    }

    public string RoleForEmail(string email)
    {
        email = (email ?? "").Trim().ToLowerInvariant();
        if (InList("Roles:CreatorEmails", email)) return "creator";
        if (InList("Roles:DebiEmails", email)) return "debi";
        if (InList("Roles:FriendEmails", email)) return "friend";
        return "public";
    }

    public async Task AssignRoleAsync(AppUser user)
    {
        var role = RoleForEmail(user.Email ?? "");
        if (role != "public" && !await users.IsInRoleAsync(user, role))
            await users.AddToRoleAsync(user, role);
    }

    private bool InList(string key, string email)
    {
        var envKey = key.Replace("Roles:", "").Replace("Emails", "").ToUpperInvariant() + "_EMAILS";
        var fromEnv = Environment.GetEnvironmentVariable(envKey);
        if (!string.IsNullOrWhiteSpace(fromEnv))
            return fromEnv.Split(',', StringSplitOptions.RemoveEmptyEntries)
                .Any(e => e.Trim().ToLowerInvariant() == email);
        return cfg.GetSection(key).Get<string[]>()?
            .Any(e => e.Trim().ToLowerInvariant() == email) == true;
    }
}
