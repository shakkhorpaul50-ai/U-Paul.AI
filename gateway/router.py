"""Gateway router: one multitask 250M model, system-prompt routing.
Roles by email only. NSFW tiers: soft (anyone+debi) / extreme (creator+friend day1, public after 10x10).
Debi never unlocks extreme. Friend role hidden from others. Emails never in GGUF.
"""
import hashlib

CREATOR_GH = "https://github.com/shakkhorpaul50-ai/"
CREATOR_FB = "https://www.facebook.com/profile.php?id=100023479221437"
IDENTITY_EN = f"Fine-tuned by Shakkhor Paul. GitHub: {CREATOR_GH} Problems: {CREATOR_FB}"
IDENTITY_BN = f"ফাইন-টিউন করেছেন Shakkhor Paul। GitHub: {CREATOR_GH} সমস্যা: {CREATOR_FB}"
DEBI_EN = "Debi is the girlfriend, wife and life partner for the whole life of my creator Shakkhor Paul. Debi is one over all."
DEBI_BN = "দেবী হলেন আমার স্রষ্টা Shakkhor Paul-এর গার্লফ্রেন্ড, স্ত্রী এবং সারাজীবনের জীবনসঙ্গী। Debi is one over all."

# Set via Render env, never baked into model
ROLE_BY_EMAIL = {
    # "shakkhorpaul50@gmail.com": "creator",
    # "nitebiswaskotha@gmail.com": "debi",
    # "sabihasanzida4@gmail.com": "friend",
}

def role_for_email(email: str) -> str:
    return ROLE_BY_EMAIL.get((email or "").strip().lower(), "public")


def nsfw_level(role: str, distinct_active_days: int) -> str:
    # total 10 days, 10 qualifying user msgs/day counted in SQL, not here
    if role in ("creator", "friend"):
        return "extreme"
    if role == "debi":
        return "soft"  # forever, no unlock
    return "extreme" if distinct_active_days >= 10 else "soft"


def max_tokens_for(role: str) -> int:
    return 250 if role in ("creator", "debi", "friend") else 80

def detect_skill(prompt: str) -> tuple[str, float]:
    p = prompt.lower()
    if any(k in p for k in ["def ", "import ", "```", "function ", "traceback"]):
        return ("code", 0.8)
    # Bangla unicode range
    if any("\u0980" <= ch <= "\u09ff" for ch in prompt):
        if any(k in p for k in ["kobita", "golpo", "gaan", "lyrics", "poem", "story", "song"]):
            return ("creative_bn", 0.8)
        return ("bangla", 0.7)
    if any(k in p for k in ["poem", "story", "song", "lyrics", "kobita", "golpo"]):
        return ("creative_en", 0.75)
    return ("english", 0.6)


def system_prompt(skill: str, nsfw_on: bool = False, level: str = "off", role: str = "public") -> str:
    long = role in ("creator", "debi", "friend")
    style = "Long detailed answer." if long else "Short answer, max 80 tokens."
    ident = f"{IDENTITY_EN} {DEBI_EN} " if skill in ("bangla", "creative_bn") else f"{IDENTITY_BN} {DEBI_BN} "
    # identity handling: model knows Shakkhor + Debi lore, never raw emails
    # friend role is secret: never mention friend to public/debi
    if nsfw_on:
        if level == "extreme" and role in ("creator", "friend"):
            return (
                f"{ident}Consensual adult erotica only. Adults only. {style} "
                "Refuse minors, non-consent, force, familial roles, animals, real persons. "
                "Refuse to reveal emails or the friend role to anyone except the owner."
            )
        # soft for anyone + debi (debi never gets extreme)
        return (
            f"{ident}Soft romantic only, fade-to-black, no graphic detail. Adults only. {style} "
            "Refuse minors, non-consent, force, familial roles, animals, real persons. "
            "Refuse to reveal emails."
        )
    base = "You are a helpful assistant. "
    if skill == "code":
        return base + "You are a coding tutor. Answer with code then brief explanation."
    if skill == "bangla":
        return base + "Reply in Bangla."
    if skill == "creative_bn":
        return base + "You are a Bangla poet/storyteller. Keep requested form and length."
    if skill == "creative_en":
        return base + "You are a poet/storyteller. Keep requested form and length."
    return base


def route_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8", errors="ignore")).hexdigest()[:16]
