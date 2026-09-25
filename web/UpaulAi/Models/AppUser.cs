using Microsoft.AspNetCore.Identity;

namespace UPaulAi.Models;

public sealed class AppUser : IdentityUser
{
    public string DisplayName { get; set; } = "";
}
