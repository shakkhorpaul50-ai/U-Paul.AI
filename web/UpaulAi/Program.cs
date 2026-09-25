using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using UPaulAi.Data;
using UPaulAi.Models;
using UPaulAi.Services;

var builder = WebApplication.CreateBuilder(args);
builder.Configuration.AddJsonFile("appsettings.Local.json", optional: true, reloadOnChange: false);

var conn = NormalizeConnectionString(
    Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? builder.Configuration.GetConnectionString("Neon"));
builder.Services.AddDbContext<AppDbContext>(o => o.UseNpgsql(conn));

builder.Services.AddIdentity<AppUser, IdentityRole>(o =>
    {
        o.Password.RequiredLength = 8;
        o.Password.RequireNonAlphanumeric = false;
        o.Password.RequireDigit = false;
        o.Password.RequireUppercase = false;
        o.Password.RequireLowercase = false;
        o.User.RequireUniqueEmail = true;
    })
    .AddEntityFrameworkStores<AppDbContext>()
    .AddDefaultTokenProviders();

builder.Services.AddControllersWithViews();
builder.Services.AddHttpClient<LlamaClient>(c =>
    c.BaseAddress = new Uri(builder.Configuration["Llama:Endpoint"] ?? "http://127.0.0.1:8080"));
builder.Services.AddScoped<RoleSeeder>();
builder.Services.AddSingleton<SkillRouter>();
builder.Services.AddSingleton<EmailSender>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    try
    {
        var sp = scope.ServiceProvider;
        await sp.GetRequiredService<AppDbContext>().Database.MigrateAsync();
        await sp.GetRequiredService<RoleSeeder>().EnsureRolesAsync();
    }
    catch (Exception ex)
    {
        app.Logger.LogWarning(ex, "Database unavailable at startup; continuing without DB");
    }
}

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
}
app.UseRouting();
app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/healthz", async (AppDbContext db, LlamaClient llama, CancellationToken ct) =>
{
    bool dbOk = false;
    string dbError = "";
    try { dbOk = await db.Database.CanConnectAsync(ct); }
    catch (Exception ex) { dbError = ex.GetBaseException().Message; }
    if (dbError.Length > 200) dbError = dbError[..200];
    return Results.Json(new { ok = true, db = dbOk, dbError, ai = await llama.IsUpAsync(ct) });
});

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();

/// <summary>
/// Accept both Npgsql key=value and postgres:// URL forms.
/// URL form is normalized explicitly so pooler params (sslmode,
/// channel_binding) never depend on driver parsing quirks.
/// </summary>
static string? NormalizeConnectionString(string? raw)
{
    if (string.IsNullOrWhiteSpace(raw)) return raw;
    raw = raw.Trim();
    if (!raw.StartsWith("postgres", StringComparison.OrdinalIgnoreCase)) return raw;
    var uri = new Uri(raw);
    var query = System.Web.HttpUtility.ParseQueryString(uri.Query);
    var userInfo = (uri.UserInfo ?? "").Split(':', 2);
    var parts = new List<string>
    {
        $"Host={uri.Host}",
        $"Port={((uri.Port > 0) ? uri.Port : 5432)}",
        $"Database={uri.AbsolutePath.Trim('/')}",
        $"Username={Uri.UnescapeDataString(userInfo[0])}",
    };
    if (userInfo.Length > 1) parts.Add($"Password={Uri.UnescapeDataString(userInfo[1])}");
    var sslOff = string.Equals(query["sslmode"], "disable", StringComparison.OrdinalIgnoreCase);
    parts.Add("Ssl Mode=" + (sslOff ? "Disable" : "Require"));
    var cb = (query["channel_binding"] ?? "").ToLowerInvariant();
    if (cb is "require" or "prefer" or "disable")
        parts.Add($"Channel Binding={char.ToUpper(cb[0]) + cb[1..]}");
    return string.Join(";", parts);
}
