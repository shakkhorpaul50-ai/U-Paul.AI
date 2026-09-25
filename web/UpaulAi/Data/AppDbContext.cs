using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using UPaulAi.Models;

namespace UPaulAi.Data;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : IdentityDbContext<AppUser>(options)
{
    public DbSet<ChatSession> ChatSessions => Set<ChatSession>();
    public DbSet<ChatMessage> ChatMessages => Set<ChatMessage>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        base.OnModelCreating(b);
        b.Entity<ChatMessage>(e =>
        {
            e.Property(m => m.Content).HasColumnType("text");
            e.HasIndex(m => m.SessionId);
        });
        b.Entity<ChatSession>(e => e.HasIndex(s => s.UserId));
    }
}
