using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using UPaulAi.Models;
using UPaulAi.Services;

namespace UPaulAi.Controllers;

public sealed class AccountController(
    UserManager<AppUser> users,
    SignInManager<AppUser> signIn,
    RoleSeeder seeder,
    EmailSender mail) : Controller
{
    [AllowAnonymous, HttpGet]
    public IActionResult Register() => View(new RegisterViewModel());

    [AllowAnonymous, HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Register(RegisterViewModel m)
    {
        if (!ModelState.IsValid) return View(m);
        var u = new AppUser { UserName = m.Email, Email = m.Email, DisplayName = m.DisplayName };
        IdentityResult r;
        try
        {
            r = await users.CreateAsync(u, m.Password);
        }
        catch
        {
            ModelState.AddModelError("", "Database unavailable. Try again later.");
            return View(m);
        }
        if (!r.Succeeded)
        {
            foreach (var e in r.Errors) ModelState.AddModelError("", e.Description);
            return View(m);
        }
        await seeder.AssignRoleAsync(u);
        await signIn.SignInAsync(u, isPersistent: false);
        return RedirectToAction("Index", "Chat");
    }

    [AllowAnonymous, HttpGet]
    public IActionResult Login(string? returnUrl = null)
    {
        ViewBag.ReturnUrl = returnUrl;
        return View(new LoginViewModel());
    }

    [AllowAnonymous, HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Login(LoginViewModel m, string? returnUrl = null)
    {
        if (!ModelState.IsValid) return View(m);
        bool ok;
        try
        {
            var r = await signIn.PasswordSignInAsync(m.Email, m.Password, m.RememberMe, lockoutOnFailure: false);
            ok = r.Succeeded;
        }
        catch
        {
            ModelState.AddModelError("", "Database unavailable. Try again later.");
            return View(m);
        }
        if (!ok)
        {
            ModelState.AddModelError("", "Invalid email or password.");
            return View(m);
        }
        if (!string.IsNullOrEmpty(returnUrl) && Url.IsLocalUrl(returnUrl)) return Redirect(returnUrl);
        return RedirectToAction("Index", "Chat");
    }

    [HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Logout()
    {
        await signIn.SignOutAsync();
        return RedirectToAction("Index", "Home");
    }

    [AllowAnonymous, HttpGet]
    public IActionResult ForgotPassword() => View(new ForgotPasswordViewModel());

    [AllowAnonymous, HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> ForgotPassword(ForgotPasswordViewModel m)
    {
        if (!ModelState.IsValid) return View(m);
        var u = await users.FindByEmailAsync(m.Email);
        // Always show confirmation: never reveal whether the email exists.
        if (u is not null && mail.Configured)
        {
            var code = await users.GeneratePasswordResetTokenAsync(u);
            var link = Url.Action("ResetPassword", "Account",
                new { email = u.Email, code }, Request.Scheme);
            await mail.SendAsync(u.Email!,
                "U_Paul-AI password reset",
                $"Click <a href=\"{link}\">here</a> to reset your U_Paul-AI password. The link expires in one day.");
        }
        else if (u is not null)
        {
            ModelState.AddModelError("", "Password reset email is not configured yet. Contact support.");
            return View(m);
        }
        return View("ForgotPasswordConfirmation");
    }

    [AllowAnonymous, HttpGet]
    public IActionResult ResetPassword(string email, string code)
    {
        if (string.IsNullOrEmpty(email) || string.IsNullOrEmpty(code))
            return RedirectToAction("ForgotPassword");
        return View(new ResetPasswordViewModel { Email = email, Code = code });
    }

    [AllowAnonymous, HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> ResetPassword(ResetPasswordViewModel m)
    {
        if (!ModelState.IsValid) return View(m);
        var u = await users.FindByEmailAsync(m.Email);
        if (u is null) return View("ResetPasswordConfirmation");
        var r = await users.ResetPasswordAsync(u, m.Code, m.Password);
        if (!r.Succeeded)
        {
            foreach (var e in r.Errors) ModelState.AddModelError("", e.Description);
            return View(m);
        }
        return View("ResetPasswordConfirmation");
    }

    [HttpGet]
    public IActionResult ChangePassword() => View(new ChangePasswordViewModel());

    [HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> ChangePassword(ChangePasswordViewModel m)
    {
        if (!ModelState.IsValid) return View(m);
        var u = await users.GetUserAsync(User);
        if (u is null) return Challenge();
        var r = await users.ChangePasswordAsync(u, m.OldPassword, m.NewPassword);
        if (!r.Succeeded)
        {
            foreach (var e in r.Errors) ModelState.AddModelError("", e.Description);
            return View(m);
        }
        await signIn.RefreshSignInAsync(u);
        ViewBag.Done = true;
        return View(m);
    }
}
