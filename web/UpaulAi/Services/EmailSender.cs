using MailKit.Net.Smtp;
using MimeKit;

namespace UPaulAi.Services;

/// <summary>SMTP email via MailKit. Silent no-op when Smtp:* is unconfigured.</summary>
public sealed class EmailSender(IConfiguration cfg, ILogger<EmailSender> log)
{
    public bool Configured =>
        !string.IsNullOrWhiteSpace(cfg["Smtp:Host"])
        && !string.IsNullOrWhiteSpace(cfg["Smtp:User"]);

    public async Task SendAsync(string to, string subject, string htmlBody, CancellationToken ct = default)
    {
        var host = cfg["Smtp:Host"];
        var user = cfg["Smtp:User"];
        var pass = cfg["Smtp:Pass"];
        if (string.IsNullOrWhiteSpace(host) || string.IsNullOrWhiteSpace(user))
        {
            log.LogWarning("SMTP not configured; skipping email to {To}", to);
            return;
        }
        var msg = new MimeMessage();
        msg.From.Add(new MailboxAddress(cfg["Smtp:FromName"] ?? "U_Paul-AI", cfg["Smtp:From"] ?? user));
        msg.To.Add(MailboxAddress.Parse(to));
        msg.Subject = subject;
        msg.Body = new TextPart("html") { Text = htmlBody };
        using var client = new SmtpClient();
        await client.ConnectAsync(host, int.Parse(cfg["Smtp:Port"] ?? "587"),
            MailKit.Security.SecureSocketOptions.StartTls, ct);
        await client.AuthenticateAsync(user, pass ?? "", ct);
        await client.SendAsync(msg, ct);
        await client.DisconnectAsync(true, ct);
    }
}
