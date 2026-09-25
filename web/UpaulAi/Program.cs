using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using UPaulAi.Data;
using UPaulAi.Models;
using UPaulAi.Services;

var builder = WebApplication.CreateBuilder(args);

var conn = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? builder.Configuration.GetConnectionString("Neon");
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
        sp.GetRequiredService<AppDbContext>().Database.EnsureCreated();
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
    bool dbOk;
    try { dbOk = await db.Database.CanConnectAsync(ct); } catch { dbOk = false; }
    return Results.Json(new { ok = true, db = dbOk, ai = await llama.IsUpAsync(ct) });
});

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
