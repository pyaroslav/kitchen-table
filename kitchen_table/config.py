"""Runtime settings, all overridable through environment variables."""

import os
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL

# gemma4:e4b runs on an ordinary laptop; gemma4:26b is better if you have the GPU.
MODEL = os.environ.get("KT_MODEL", "gemma4:e4b")

DATA_DIR = Path(os.environ.get("KT_DATA", Path.cwd() / "data"))
DB_PATH = DATA_DIR / "kitchen_table.sqlite3"

# Longest image edge sent to the model. Phone photos are 4000px+; Gemma doesn't need that.
MAX_IMAGE_EDGE = int(os.environ.get("KT_MAX_IMAGE_EDGE", "1600"))

# Generous: a cold model load on a laptop can take a minute.
REQUEST_TIMEOUT = float(os.environ.get("KT_TIMEOUT", "300"))
