"""Interface text. en/ru/es/uk are hand-written; any other language is translated
once by the local model and cached, so a parent who reads Tagalog or Persian gets
buttons in Tagalog or Persian too."""

import json
import re
from pathlib import Path

from . import config
from .languages import LANGUAGES, name as lang_name
from .ollama_client import chat

BUILTIN = Path(__file__).parent / "static" / "i18n"
PLACEHOLDER = re.compile(r"\{\w+\}")


def _en() -> dict:
    return json.loads((BUILTIN / "en.json").read_text(encoding="utf8"))


def strings(lang: str) -> dict:
    if lang not in LANGUAGES:
        lang = "en"
    builtin = BUILTIN / f"{lang}.json"
    if builtin.exists():
        return json.loads(builtin.read_text(encoding="utf8"))
    cache = config.DATA_DIR / "i18n" / f"{lang}.json"
    if cache.exists():
        # Strings added after the cache was made fall back to English until it's rebuilt.
        return {**_en(), **json.loads(cache.read_text(encoding="utf8"))}

    en = _en()
    schema = {"type": "object", "properties": {k: {"type": "string"} for k in en}, "required": list(en)}
    prompt = (f"Translate these app interface strings from English into {lang_name(lang)}. "
              "The app explains paper mail to an older person: use warm, simple, everyday words. "
              "Keep every {placeholder} exactly as is. Keep the same JSON keys.\n\n"
              + json.dumps(en, ensure_ascii=False, indent=1))
    out = chat([{"role": "user", "content": prompt}], schema=schema, temperature=0.1).as_json()
    # Never ship a string that lost its placeholder; fall back to English for that key.
    merged = {k: (out.get(k) if out.get(k) and set(PLACEHOLDER.findall(out[k])) == set(PLACEHOLDER.findall(v)) else v)
              for k, v in en.items()}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf8")
    return merged
