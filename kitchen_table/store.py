"""SQLite 'drawer' of past letters. Stores text only: photos are discarded after reading."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS letters (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    lang        TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    analysis    TEXT NOT NULL,
    timing      TEXT NOT NULL,
    qa          TEXT NOT NULL DEFAULT '[]',
    handled     INTEGER NOT NULL DEFAULT 0
);
"""


def _conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute(SCHEMA)
    return c


def _row(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"], "created_at": r["created_at"], "lang": r["lang"],
        "transcript": r["transcript"], "analysis": json.loads(r["analysis"]),
        "timing": json.loads(r["timing"]), "qa": json.loads(r["qa"]),
        "handled": bool(r["handled"]),
    }


def save(lang: str, result: dict) -> dict:
    lid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as c:
        c.execute("INSERT INTO letters (id, created_at, lang, transcript, analysis, timing) VALUES (?,?,?,?,?,?)",
                  (lid, now, lang, result["transcript"], json.dumps(result["analysis"], ensure_ascii=False),
                   json.dumps(result["timing"])))
    return get(lid)


def get(lid: str) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM letters WHERE id = ?", (lid,)).fetchone()
    return _row(r) if r else None


def recent(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM letters ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def add_qa(lid: str, turn: dict) -> None:
    with _conn() as c:
        r = c.execute("SELECT qa FROM letters WHERE id = ?", (lid,)).fetchone()
        qa = json.loads(r["qa"]) + [turn]
        c.execute("UPDATE letters SET qa = ? WHERE id = ?", (json.dumps(qa, ensure_ascii=False), lid))


def set_handled(lid: str, handled: bool) -> None:
    with _conn() as c:
        c.execute("UPDATE letters SET handled = ? WHERE id = ?", (int(handled), lid))


def delete(lid: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM letters WHERE id = ?", (lid,))
