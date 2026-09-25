using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace UPaulAi.Data;

/// <summary>Design-time factory so `dotnet ef` never executes Program.cs.</summary>
public sealed class AppDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(
                Environment.GetEnvironmentVariable("DATABASE_URL")
                ?? "Host=localhost;Database=upaul;Username=postgres;Password=postgres")
            .Options;
        return new AppDbContext(options);
    }
}
