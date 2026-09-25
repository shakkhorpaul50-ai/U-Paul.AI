namespace UPaulAi.Models;

public sealed class ChatSession
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = "";
    public string Skill { get; set; } = "general";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<ChatMessage> Messages { get; set; } = new();
}

public sealed class ChatMessage
{
    public long Id { get; set; }
    public Guid SessionId { get; set; }
    public string Role { get; set; } = ""; // user | assistant
    public string Content { get; set; } = "";
    public int Tokens { get; set; }
    public long Ms { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
