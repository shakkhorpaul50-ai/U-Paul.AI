"""U_Paul-AI model config: single 260M GGUF, runtime Release-download (file is 234MB, over GitHub limit)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("MODEL_PATH", str(BASE / "models" / "gguf" / "smol260M-Q3_K_M.gguf"))
RELEASE_URL = os.environ.get("RELEASE_URL", "")
N_CTX = int(os.environ.get("N_CTX", "512"))
N_BATCH = int(os.environ.get("N_BATCH", "4"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
APP_TOKEN_DAYS = int(os.environ.get("APP_TOKEN_DAYS", "30"))
