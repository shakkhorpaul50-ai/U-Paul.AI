"""Google OAuth (hand-rolled, stdlib HTTP) + app JWT (pyjwt). No native deps."""
import json
import secrets
import time
import urllib.parse
import urllib.request

import jwt
from fastapi import HTTPException, Request

from backend.model import APP_TOKEN_DAYS, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"

_states: dict = {}  # state -> timestamp (single worker)


def configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and SECRET_KEY)


def login_url(redirect_uri: str) -> str:
    st = secrets.token_urlsafe(24)
    _states[st] = time.time()
    q = urllib.parse.urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": st,
            "prompt": "select_account",
        }
    )
    return GOOGLE_AUTH + "?" + q


def _post_form(url: str, fields: dict) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def handle_callback(code: str, state: str, redirect_uri: str) -> dict:
    ts = _states.pop(state, 0)
    if not ts or time.time() - ts > 600:
        raise HTTPException(400, "Invalid or expired login state")
    tok = _post_form(
        GOOGLE_TOKEN,
        {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )
    if "access_token" not in tok:
        raise HTTPException(400, "Google token exchange failed")
    info = _get_json(GOOGLE_USERINFO, tok["access_token"])
    if not info.get("email"):
        raise HTTPException(400, "Google did not return an email")
    return info


def app_token(user_id: str, email: str, role: str, name: str = "", picture: str = "") -> str:
    return jwt.encode(
        {
            "uid": user_id,
            "email": email,
            "role": role,
            "name": name,
            "picture": picture,
            "exp": int(time.time()) + APP_TOKEN_DAYS * 86400,
        },
        SECRET_KEY,
        algorithm="HS256",
    )


def require_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    try:
        return jwt.decode(auth[7:], SECRET_KEY, algorithms=["HS256"])
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "Invalid or expired login")
