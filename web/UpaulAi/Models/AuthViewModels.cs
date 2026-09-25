using System.ComponentModel.DataAnnotations;

namespace UPaulAi.Models;

public sealed class RegisterViewModel
{
    [Required, EmailAddress]
    public string Email { get; set; } = "";
    [Required, MinLength(8)]
    [DataType(DataType.Password)]
    public string Password { get; set; } = "";
    public string DisplayName { get; set; } = "";
}

public sealed class LoginViewModel
{
    [Required, EmailAddress]
    public string Email { get; set; } = "";
    [Required]
    [DataType(DataType.Password)]
    public string Password { get; set; } = "";
    public bool RememberMe { get; set; }
}

public sealed class ForgotPasswordViewModel
{
    [Required, EmailAddress]
    public string Email { get; set; } = "";
}

public sealed class ResetPasswordViewModel
{
    [Required, EmailAddress]
    public string Email { get; set; } = "";
    [Required]
    public string Code { get; set; } = "";
    [Required, MinLength(8)]
    [DataType(DataType.Password)]
    public string Password { get; set; } = "";
}

public sealed class ChangePasswordViewModel
{
    [Required]
    [DataType(DataType.Password)]
    public string OldPassword { get; set; } = "";
    [Required, MinLength(8)]
    [DataType(DataType.Password)]
    public string NewPassword { get; set; } = "";
}
