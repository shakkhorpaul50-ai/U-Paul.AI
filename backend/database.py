"""Neon Postgres (free): small pool, auto-migrate, chat logging. Degrades gracefully."""
import asyncpg
from pathlib import Path

_pool = None
_db_ok = False
_db_error = ""


async def init_db(url: str) -> None:
    global _pool, _db_ok, _db_error
    try:
        schema = (Path(__file__).resolve().parent.parent / "db" / "schema.sql").read_text()
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=2, command_timeout=10)
        async with _pool.acquire() as c:
            await c.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            await c.execute(schema)
            await c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT UNIQUE;")
            await c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT;")
            await c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS picture TEXT;")
            await c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;")
        _db_ok = True
    except Exception as e:  # noqa: BLE001
        _db_error = str(e)[:200]


def ok() -> bool:
    return _db_ok


def error() -> str:
    return _db_error


async def get_role(email: str) -> str:
    async with _pool.acquire() as c:
        row = await c.fetchrow("SELECT role FROM users WHERE email=$1", email.strip().lower())
    return row["role"] if row else "public"


async def oauth_upsert(email: str, name: str, picture: str, google_sub: str, role: str) -> dict:
    async with _pool.acquire() as c:
        row = await c.fetchrow(
            "INSERT INTO users(email, role, name, picture, google_sub) VALUES($1, $2, $3, $4, $5) "
            "ON CONFLICT(email) DO UPDATE SET name=EXCLUDED.name, picture=EXCLUDED.picture, "
            "google_sub=EXCLUDED.google_sub, role=EXCLUDED.role "
            "RETURNING id, email, role, name, picture",
            email.strip().lower(),
            role,
            name,
            picture,
            google_sub,
        )
    return dict(row)


async def get_user_by_email(email: str) -> dict:
    async with _pool.acquire() as c:
        row = await c.fetchrow(
            "SELECT id, email, role, name, picture, password_hash FROM users WHERE email=$1",
            email.strip().lower(),
        )
    return dict(row) if row else {}


async def create_password_user(email: str, name: str, password_hash: str, role: str) -> dict:
    """Insert new user, or claim a Google-only row (password_hash NULL). {} if taken."""
    email = email.strip().lower()
    async with _pool.acquire() as c:
        row = await c.fetchrow("SELECT id, password_hash FROM users WHERE email=$1", email)
        if row and row["password_hash"]:
            return {}
        if row:
            row = await c.fetchrow(
                "UPDATE users SET password_hash=$2, name=$3, role=$4 WHERE id=$1 "
                "RETURNING id, email, role, name, picture",
                row["id"],
                password_hash,
                name,
                role,
            )
        else:
            row = await c.fetchrow(
                "INSERT INTO users(email, role, name, password_hash) VALUES($1, $2, $3, $4) "
                "RETURNING id, email, role, name, picture",
                email,
                role,
                name,
                password_hash,
            )
    return dict(row)


async def get_user(user_id: str) -> dict:
    async with _pool.acquire() as c:
        row = await c.fetchrow(
            "SELECT id, email, role, name, picture FROM users WHERE id=$1", user_id
        )
    return dict(row) if row else {}


async def get_or_create_user(email: str, role: str) -> str:
    email = email.strip().lower()
    async with _pool.acquire() as c:
        row = await c.fetchrow(
            "INSERT INTO users(email, role) VALUES($1, $2) "
            "ON CONFLICT(email) DO UPDATE SET role=EXCLUDED.role RETURNING id",
            email,
            role,
        )
    return str(row["id"])


async def new_session(user_id: str, skill: str) -> str:
    async with _pool.acquire() as c:
        row = await c.fetchrow(
            "INSERT INTO sessions(user_id, skill) VALUES($1, $2) RETURNING id", user_id, skill
        )
    return str(row["id"])


async def log_message(session_id: str, role_: str, content: str, tokens: int, ms: int) -> None:
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO messages(session_id, role, content, tokens, ms) VALUES($1, $2, $3, $4, $5)",
            session_id,
            role_,
            content,
            tokens,
            ms,
        )


async def distinct_active_days(user_id: str) -> int:
    async with _pool.acquire() as c:
        n = await c.fetchval(
            "SELECT COUNT(DISTINCT m.created_at::date) FROM messages m "
            "JOIN sessions s ON s.id=m.session_id "
            "WHERE s.user_id=$1 AND m.role='user'",
            user_id,
        )
    return int(n or 0)


async def cached_skill(prompt_hash: str) -> str:
    async with _pool.acquire() as c:
        row = await c.fetchrow("SELECT skill FROM routes WHERE prompt_hash=$1", prompt_hash)
    return row["skill"] if row else ""


async def cache_skill(prompt_hash: str, skill: str, confidence: float) -> None:
    async with _pool.acquire() as c:
        await c.execute(
            "INSERT INTO routes(prompt_hash, skill, confidence) VALUES($1, $2, $3) "
            "ON CONFLICT(prompt_hash) DO NOTHING",
            prompt_hash,
            skill,
            confidence,
        )
