using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using UPaulAi.Models;
using UPaulAi.Services;

namespace UPaulAi.Controllers;

public sealed class AccountController(
    UserManager<AppUser> users,
    SignInManager<AppUser> signIn,
    RoleSeeder seeder) : Controller
{
    [AllowAnonymous, HttpGet]
    public IActionResult Register() => View(new RegisterViewModel());

    [AllowAnonymous, HttpPost, ValidateAntiForgeryToken]
    public async Task<IActionResult> Register(RegisterViewModel m)
    {
        if (!ModelState.IsValid) return View(m);
        var u = new AppUser { UserName = m.Email, Email = m.Email, DisplayName = m.DisplayName };
        var r = await users.CreateAsync(u, m.Password);
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
        var r = await signIn.PasswordSignInAsync(m.Email, m.Password, m.RememberMe, lockoutOnFailure: false);
        if (!r.Succeeded)
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
}
