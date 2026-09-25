"""U_Paul-AI backend: FastAPI + llama-cpp GGUF, lazy background load for Render free."""
import asyncio
import sys
import threading
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gateway.router import detect_skill, system_prompt, role_for_email, max_tokens_for, route_key
from backend import database as db
from backend.model import DEFAULT_MODEL, RELEASE_URL, N_CTX, N_BATCH, DATABASE_URL

_llm = None
_loading = False
_load_error = ""


def _ensure_model() -> str:
    global _load_error
    p = Path(DEFAULT_MODEL)
    if p.exists() and p.stat().st_size > 0:
        return str(p)
    if not RELEASE_URL:
        _load_error = "Model not loaded: missing file and no RELEASE_URL"
        return ""
    if not RELEASE_URL.startswith(("http://", "https://")):
        _load_error = "Model not loaded: RELEASE_URL not set to a download link"
        return ""
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(RELEASE_URL, str(p))
        return str(p)
    except Exception as e:  # noqa: BLE001
        _load_error = f"download failed: {e}"
        return ""


def _init_db_bg() -> None:
    if DATABASE_URL:
        asyncio.run(db.init_db(DATABASE_URL))


def _load_bg() -> None:
    global _llm, _loading
    from llama_cpp import Llama

    mp = _ensure_model()
    if not mp:
        _loading = False
        return
    _llm = Llama(model_path=mp, n_ctx=N_CTX, n_batch=N_BATCH, n_threads=1, verbose=False)
    _loading = False


app = FastAPI(title="U_Paul-AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    prompt: str
    email: str = ""
    nsfw_on: bool = False


@app.on_event("startup")
def startup() -> None:
    global _loading
    _loading = True
    threading.Thread(target=_load_bg, daemon=True).start()
    threading.Thread(target=_init_db_bg, daemon=True).start()


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    return {
        "loaded": _llm is not None,
        "loading": _loading,
        "error": _load_error,
        "model": Path(DEFAULT_MODEL).name,
        "n_ctx": N_CTX,
        "db_ok": db.ok(),
        "db_error": db.error(),
    }


@app.post("/api/chat")
def chat(inp: ChatIn) -> JSONResponse:
    if _llm is None:
        return JSONResponse(
            {"error": "Model not loaded yet" if _loading else (_load_error or "Model not loaded")},
            status_code=503,
        )
    role = role_for_email(inp.email)
    skill, conf = detect_skill(inp.prompt)
    if db.ok() and inp.email.strip():
        try:
            role = asyncio.run(db.get_role(inp.email))
        except Exception:  # noqa: BLE001
            pass
    if db.ok():
        try:
            cached = asyncio.run(db.cached_skill(route_key(inp.prompt)))
            if cached:
                skill = cached
        except Exception:  # noqa: BLE001
            pass
    sys_p = system_prompt(skill, nsfw_on=inp.nsfw_on, role=role)
    prompt = (
        f"<|im_start|>system\n{sys_p}<|im_end|>\n"
        f"<|im_start|>user\n{inp.prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    t0 = time.time()
    out = _llm(prompt, max_tokens=max_tokens_for(role), temperature=0.7, top_p=0.9, stop=["<|im_end|>"])
    text = out["choices"][0]["text"].strip()
    if not text:
        text = "No reply generated. Try a shorter prompt."
    ms = int((time.time() - t0) * 1000)
    if db.ok():
        try:
            asyncio.run(_log_chat(inp.email, role, skill, conf, inp.prompt, text, ms))
        except Exception:  # noqa: BLE001
            pass
    return JSONResponse(
        {
            "reply": text,
            "skill": skill,
            "confidence": conf,
            "ms": ms,
            "route": route_key(inp.prompt),
        }
    )


async def _log_chat(
    email: str, role: str, skill: str, conf: float, prompt: str, reply: str, ms: int
) -> None:
    if email.strip():
        user_id = await db.get_or_create_user(email, role)
    else:
        user_id = await db.get_or_create_user("anon@local", "public")
    session_id = await db.new_session(user_id, skill)
    await db.log_message(session_id, "user", prompt, len(prompt.split()), 0)
    await db.log_message(session_id, "assistant", reply, len(reply.split()), ms)
    await db.cache_skill(route_key(prompt), skill, conf)


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
