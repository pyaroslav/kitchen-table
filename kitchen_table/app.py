"""HTTP API + static phone UI. Meant to run on one computer at home and be opened
from a phone on the same Wi-Fi."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, reader, store, ui_strings
from .languages import LANGUAGES
from .ollama_client import OllamaError, model_status

STATIC = Path(__file__).parent / "static"
MAX_PAGES = 6
MAX_UPLOAD = 25 * 1024 * 1024

app = FastAPI(title="Kitchen Table", docs_url=None, redoc_url=None)


@app.exception_handler(OllamaError)
async def _ollama_down(_, exc: OllamaError):
    return JSONResponse(status_code=503, content={"error": "model_unavailable", "detail": str(exc)})


@app.get("/api/status")
def status():
    return {**model_status(), "languages": LANGUAGES}


@app.get("/api/ui/{lang}")
def ui(lang: str):
    return ui_strings.strings(lang)


@app.post("/api/letters")
def read_letter(pages: list[UploadFile] = File(...), lang: str = Form("en"), helper_lang: str = Form("en")):
    if not pages or len(pages) > MAX_PAGES:
        raise HTTPException(400, f"Send 1 to {MAX_PAGES} photos.")
    blobs = []
    for p in pages:
        b = p.file.read(MAX_UPLOAD + 1)
        if len(b) > MAX_UPLOAD:
            raise HTTPException(413, "Photo too large.")
        blobs.append(b)
    try:
        result = reader.read_letter(blobs, lang if lang in LANGUAGES else "en",
                                    helper_lang if helper_lang in LANGUAGES else "en")
    except OllamaError:
        raise
    except Exception as e:  # unreadable image, malformed model JSON
        raise HTTPException(422, f"Couldn't read that letter: {e}")
    return store.save(lang, result)


@app.get("/api/letters")
def list_letters():
    return [{"id": l["id"], "created_at": l["created_at"], "handled": l["handled"],
             "verdict": l["analysis"].get("verdict"), "headline": l["analysis"].get("headline"),
             "sender": l["analysis"].get("sender"),
             "next_deadline": next((d for d in l["analysis"].get("deadlines", [])), None)}
            for l in store.recent()]


def _letter(lid: str) -> dict:
    l = store.get(lid)
    if not l:
        raise HTTPException(404, "No such letter.")
    return l


@app.get("/api/letters/{lid}")
def get_letter(lid: str):
    l = _letter(lid)
    # days_left is relative to *today*, not the day the letter was read.
    for d in l["analysis"].get("deadlines", []):
        d["days_left"] = (date.fromisoformat(d["date"]) - date.today()).days
    return l


@app.post("/api/letters/{lid}/ask")
def ask(lid: str, lang: str = Form("en"), question: str | None = Form(None),
        audio: UploadFile | None = File(None)):
    l = _letter(lid)
    wav = audio.file.read(MAX_UPLOAD) if audio else None
    if not wav and not (question and question.strip()):
        raise HTTPException(400, "Ask something.")
    out = reader.ask(l, lang, question=question, audio_wav=wav, history=l["qa"][-4:])
    turn = {"question": out["heard"], "answer": out["answer"], "voice": bool(wav)}
    store.add_qa(lid, turn)
    return {**turn, "seconds": out["seconds"]}


class Handled(BaseModel):
    handled: bool


@app.post("/api/letters/{lid}/handled")
def handled(lid: str, body: Handled):
    _letter(lid)
    store.set_handled(lid, body.handled)
    return {"ok": True}


@app.delete("/api/letters/{lid}")
def delete(lid: str):
    store.delete(lid)
    return {"ok": True}


def _ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@app.get("/api/letters/{lid}/calendar.ics")
def calendar(lid: str):
    l = _letter(lid)
    a = l["analysis"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Kitchen Table//EN", "CALSCALE:GREGORIAN"]
    for i, d in enumerate(a.get("deadlines", [])):
        day = date.fromisoformat(d["date"])
        lines += [
            "BEGIN:VEVENT", f"UID:{lid}-{i}@kitchen-table", f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_ics_escape(d['what'] or a.get('headline', ''))}",
            f"DESCRIPTION:{_ics_escape(a.get('sender', '') + ' — ' + a.get('summary', ''))}",
            "BEGIN:VALARM", "TRIGGER:-P3D", "ACTION:DISPLAY", "DESCRIPTION:Reminder", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines) + "\r\n", media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="letter-{lid}.ics"'})


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/", StaticFiles(directory=STATIC), name="static")
