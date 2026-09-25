using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using UPaulAi.Data;
using UPaulAi.Models;
using UPaulAi.Services;

namespace UPaulAi.Controllers;

[Authorize]
public sealed class ChatController(
    AppDbContext db,
    UserManager<AppUser> users,
    LlamaClient llama,
    SkillRouter router) : Controller
{
    public async Task<IActionResult> Index(CancellationToken ct)
    {
        var msgs = new List<ChatMessage>();
        try
        {
            var u = await users.GetUserAsync(User);
            if (u is not null)
            {
                var s = await db.ChatSessions
                    .Where(x => x.UserId == u.Id)
                    .OrderByDescending(x => x.CreatedAt)
                    .FirstOrDefaultAsync(ct);
                if (s is not null)
                    msgs = await db.ChatMessages
                        .Where(m => m.SessionId == s.Id)
                        .OrderBy(m => m.Id).Take(50).ToListAsync(ct);
            }
        }
        catch
        {
            ViewBag.DbDown = true;
        }
        return View(msgs);
    }

    [HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Send([FromForm] string prompt, CancellationToken ct)
    {
        prompt = (prompt ?? "").Trim();
        if (prompt.Length == 0) return Json(new { error = "Empty prompt." });
        if (prompt.Length > 2000) prompt = prompt[..2000];
        UPaulAi.Models.AppUser? u;
        IList<string> roles;
        try
        {
            u = await users.GetUserAsync(User);
            if (u is null) return Unauthorized();
            roles = await users.GetRolesAsync(u);
        }
        catch
        {
            return Json(new { error = "Database unavailable. Try again later." });
        }        var role = roles.Contains("creator") ? "creator"
            : roles.Contains("debi") ? "debi"
            : roles.Contains("friend") ? "friend" : "public";

        if (router.ShouldRefuse(prompt))
        {
            var refusal = router.Refusal();
            await SaveAsync(u.Id, "refused", prompt, refusal, 0, ct);
            return Json(new { reply = refusal, skill = "refused", ms = 0 });
        }

        var (skill, _) = router.DetectSkill(prompt);
        var full = router.BuildPrompt(router.SystemPrompt(skill, role), prompt);
        string text;
        long ms;
        try
        {
            (text, ms) = await llama.CompleteAsync(full, router.MaxTokens(role), ct);
        }
        catch (Exception ex)
        {
            return Json(new { error = "AI backend unavailable: " + ex.Message });
        }
        if (string.IsNullOrWhiteSpace(text)) text = "No reply generated. Try a shorter prompt.";
        await SaveAsync(u.Id, skill, prompt, text, ms, ct);
        return Json(new { reply = text, skill, ms });
    }

    private async Task SaveAsync(
        string userId, string skill, string prompt, string reply, long ms, CancellationToken ct)
    {
        var s = new ChatSession { UserId = userId, Skill = skill };
        db.ChatSessions.Add(s);
        db.ChatMessages.Add(new ChatMessage
        {
            SessionId = s.Id, Role = "user", Content = prompt,
            Tokens = prompt.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length
        });
        db.ChatMessages.Add(new ChatMessage
        {
            SessionId = s.Id, Role = "assistant", Content = reply,
            Tokens = reply.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length, Ms = ms
        });
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch
        {
            // History is best-effort; the reply was already generated.
        }
    }
}
