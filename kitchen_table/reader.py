"""The letter-reading pipeline.

Pass 1 (vision):  photo(s) -> faithful transcript in the letter's own language.
Pass 2 (text):    transcript -> structured explanation in the reader's language.
Then plain Python checks the parts a parent should never have to trust a model
on: date arithmetic and scam escalation.

Splitting the passes keeps a transcript around for follow-up questions, lets
each step be evaluated on its own, and means pass 2 never "reads" pixels.
"""

import io
import re
from datetime import date, datetime

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

from . import config, redflags
from .languages import name as lang_name
from .ollama_client import OllamaError, chat

VERDICTS = ["file_it", "action_needed", "urgent", "scam_warning"]

TRANSCRIBE_PROMPT = """These are photos of one paper letter (pages in order).
Transcribe every word you can read, top to bottom, page by page.
Copy names, dates, amounts, account numbers, phone numbers and web addresses EXACTLY.
Write [unreadable] for anything you cannot read. Do not summarise, translate or comment.
Output only the transcript."""

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "letter_type": {"type": "string", "enum": [
            "bill", "medical", "insurance", "government", "tax", "bank", "appointment",
            "legal", "jury_duty", "school", "advertisement", "personal", "possible_scam", "other"]},
        "sender": {"type": "string"},
        "verdict": {"type": "string", "enum": VERDICTS},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "object", "properties": {
            "text": {"type": "string"},
            "by_date": {"type": ["string", "null"]}},
            "required": ["text", "by_date"]}},
        "deadlines": {"type": "array", "items": {"type": "object", "properties": {
            "date": {"type": "string"},
            "what": {"type": "string"}},
            "required": ["date", "what"]}},
        "money": {"type": "object", "properties": {
            "amount": {"type": ["number", "null"]},
            "currency": {"type": "string"},
            "direction": {"type": "string", "enum": ["you_owe", "you_receive", "none"]},
            "already_paid_or_autopay": {"type": "boolean"}},
            "required": ["amount", "currency", "direction", "already_paid_or_autopay"]},
        "scam_signals": {"type": "array", "items": {"type": "string"}},
        "contacts": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"},
            "phone": {"type": ["string", "null"]},
            "website": {"type": ["string", "null"]}},
            "required": ["label", "phone", "website"]}},
        "glossary": {"type": "array", "items": {"type": "object", "properties": {
            "term": {"type": "string"},
            "meaning": {"type": "string"}},
            "required": ["term", "meaning"]}},
        "family_note": {"type": "string"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["letter_type", "sender", "verdict", "headline", "summary", "steps", "deadlines",
                 "money", "scam_signals", "contacts", "glossary", "family_note", "confidence"],
}

ANALYSIS_PROMPT = """You help an older person understand the paper mail they receive.
They read {lang} best. Today is {today}.

Read the letter transcript below and explain it to them.

Verdict rules:
- "file_it": nothing to do (statements, receipts, ads, "this is not a bill", autopay already covers it).
- "action_needed": they must do something, and there is time.
- "urgent": a deadline within 7 days, a past-due/shut-off/collections notice, a court or jury date, or health/legal consequences.
- "scam_warning": it asks for money or personal details in a way real organisations don't (gift cards, crypto, wire, secrecy, threats, prize fees), or the sender looks fake.
Advertisements dressed up as official notices ("final notice" for a car warranty) are "file_it" or "scam_warning", never "urgent".

Write headline, summary, steps[].text, deadlines[].what, scam_signals and glossary[].meaning in {lang}.
scam_signals: the warning signs that really apply to THIS letter, each rewritten in {lang} in your own simple words (never copy the English text below). Empty if it is not suspicious.
- headline: one short sentence saying what this is and whether they need to worry.
- summary: 2-4 short sentences, plain words, like a kind grown-up child explaining at the kitchen table. No jargon.
- steps: the concrete things to do, in order. Empty if there is nothing to do. For a suspected scam, steps are: don't pay, don't call numbers in the letter, call family.
- deadlines: every date they must act by, as YYYY-MM-DD. Do not include dates that are only informational (statement date, date of service).
- glossary: up to 4 hard words from the letter (keep the term in the original language) with a plain explanation.
- money: the main amount. direction "you_owe" if the letter asks them to pay it (bills, past-due balances, copays, fees, debts), "you_receive" for refunds/checks/benefits paid to them, "none" only if no money is requested or paid. For a suspected scam use "none".
- contacts: phone numbers / websites exactly as printed. Leave sender and contacts in the original language.
- family_note: 1-3 sentences in {helper_lang} for their adult child, who handles paperwork: who sent it, what it wants, by when, amount.
- confidence: "low" if the transcript has many [unreadable] parts or key facts are missing.

Our automatic checks found these warning signs (may be empty, may be false alarms):
{flags}

LETTER TRANSCRIPT:
<<<
{transcript}
>>>"""


def photo_quality(img: Image.Image) -> dict:
    """Cheap measurements that predict a misread: too dark, too flat, too blurry."""
    gray = img.convert("L")
    gray.thumbnail((800, 800))
    stat = ImageStat.Stat(gray)
    edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
    q = {"brightness": round(stat.mean[0]), "contrast": round(stat.stddev[0]), "sharpness": round(edges.var[0])}
    q["poor"] = q["brightness"] < 90 or q["contrast"] < 35 or q["sharpness"] < 150
    return q


def prepare_image(blob: bytes) -> tuple[bytes, dict]:
    """Rotate per EXIF, fix poor lighting, shrink, re-encode as JPEG (drops EXIF/GPS)."""
    img = Image.open(io.BytesIO(blob))
    img = ImageOps.exif_transpose(img).convert("RGB")
    q = photo_quality(img)
    if q["poor"]:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        q["enhanced"] = True
    img.thumbnail((config.MAX_IMAGE_EDGE, config.MAX_IMAGE_EDGE))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=88)
    return out.getvalue(), q


def transcribe(images: list[bytes], model: str | None = None):
    msgs = [{"role": "user", "content": TRANSCRIBE_PROMPT, "media": images}]
    try:
        res = chat(msgs, model=model, temperature=0.0, extra={"num_predict": 3000})
    except OllamaError as e:
        # Greedy decoding occasionally loops on repetitive layouts (tables, dashed stubs).
        # One retry with a little sampling and a repeat penalty gets past it.
        if "repeat" not in str(e):
            raise
        res = chat(msgs, model=model, temperature=0.3,
                   extra={"num_predict": 3000, "repeat_penalty": 1.15, "repeat_last_n": 256})
    return res.text.strip(), res


def analyse(transcript: str, lang: str, helper_lang: str = "en",
            today: date | None = None, model: str | None = None):
    today = today or date.today()
    hits = redflags.scan(transcript)
    flags = "\n".join(f"- {h['why']} (found: \"{h['evidence']}\")" for h in hits) or "- none"
    prompt = ANALYSIS_PROMPT.format(
        lang=lang_name(lang), helper_lang=lang_name(helper_lang),
        today=today.isoformat(), flags=flags, transcript=transcript)
    res = chat([{"role": "user", "content": prompt}], model=model, schema=ANALYSIS_SCHEMA)
    result = postprocess(res.as_json(), hits, today)
    return result, res


def _parse_date(s) -> date | None:
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(*map(int, m.groups()))
        except ValueError:
            return None
    return None


def postprocess(a: dict, hits: list[dict], today: date) -> dict:
    """Code, not the model, owns date maths and the scam override."""
    deadlines = []
    for d in a.get("deadlines", []):
        parsed = _parse_date(d.get("date"))
        if parsed:
            deadlines.append({"date": parsed.isoformat(), "what": d.get("what", ""),
                              "days_left": (parsed - today).days})
    deadlines.sort(key=lambda d: d["date"])
    a["deadlines"] = deadlines

    for s in a.get("steps", []):
        p = _parse_date(s.get("by_date"))
        s["by_date"] = p.isoformat() if p else None

    model_verdict = a.get("verdict") if a.get("verdict") in VERDICTS else "action_needed"
    verdict = model_verdict
    reasons = []

    if redflags.has_strong(hits):
        verdict = "scam_warning"
        if model_verdict != "scam_warning":
            reasons.append("strong_scam_rule")
    elif verdict in ("file_it", "action_needed") and a.get("money", {}).get("direction") != "you_receive":
        upcoming = [d for d in deadlines if d["days_left"] >= 0]
        if verdict == "file_it" and upcoming and a.get("steps"):
            verdict = "action_needed"
            reasons.append("has_steps_and_deadline")
        if verdict == "action_needed" and upcoming and upcoming[0]["days_left"] <= 7:
            verdict = "urgent"
            reasons.append("deadline_within_7_days")

    if verdict == "scam_warning":
        # A scammer's "deadline" is pressure, not an appointment: keep it off the calendar.
        a["deadlines"] = []
        for s in a.get("steps", []):
            s["by_date"] = None

    a["model_verdict"] = model_verdict
    a["verdict"] = verdict
    a["overrides"] = reasons
    a["rule_flags"] = hits
    return a


def read_letter(images: list[bytes], lang: str, helper_lang: str = "en",
                model: str | None = None, today: date | None = None) -> dict:
    prepared, quality = zip(*(prepare_image(b) for b in images))
    transcript, r1 = transcribe(list(prepared), model=model)
    analysis, r2 = analyse(transcript, lang, helper_lang, today=today, model=model)
    if any(q["poor"] for q in quality):
        # A misread digit on a dark photo turns "due Oct 20, 2026" into "old bill from 2020".
        # Never let a bad photo produce a confident "nothing to do".
        analysis["confidence"] = "low"
        analysis["overrides"].append("poor_photo")
        if analysis["verdict"] == "file_it":
            analysis["verdict"] = "unsure"
    return {
        "transcript": transcript,
        "analysis": analysis,
        "photo_quality": list(quality),
        "timing": {
            "read_seconds": round(r1.seconds, 1),
            "explain_seconds": round(r2.seconds, 1),
            "output_tokens": r1.output_tokens + r2.output_tokens,
            "model": model or config.MODEL,
        },
    }


ASK_SCHEMA = {
    "type": "object",
    "properties": {"heard": {"type": "string"}, "answer": {"type": "string"}},
    "required": ["heard", "answer"],
}

ASK_PROMPT = """You help an older person with a letter they received. They speak {lang}. Today is {today}.
Answer their question in {lang}, in 1-4 short, kind, plain sentences, using ONLY the letter and the explanation below.
If the letter doesn't say, tell them so and suggest asking their family or calling the phone number printed on the official website (not one from a suspicious letter).
If the letter was judged a possible scam, never tell them to pay, call, or reply to it.
Put the question you understood in "heard" (in {lang}).

EXPLANATION ALREADY GIVEN: {headline} / verdict: {verdict}
LETTER TRANSCRIPT:
<<<
{transcript}
>>>"""


def ask(letter: dict, lang: str, question: str | None = None, audio_wav: bytes | None = None,
        history: list[dict] | None = None, model: str | None = None) -> dict:
    a = letter["analysis"]
    system = ASK_PROMPT.format(lang=lang_name(lang), today=date.today().isoformat(),
                               headline=a.get("headline", ""), verdict=a.get("verdict", ""),
                               transcript=letter["transcript"])
    msgs = [{"role": "system", "content": system}]
    for turn in history or []:
        msgs.append({"role": "user", "content": turn["question"]})
        msgs.append({"role": "assistant", "content": turn["answer"]})
    if audio_wav:
        msgs.append({"role": "user", "content": "(The question is in this voice recording.)", "media": [audio_wav]})
    else:
        msgs.append({"role": "user", "content": question or ""})
    res = chat(msgs, model=model, schema=ASK_SCHEMA, temperature=0.2)
    out = res.as_json()
    if not audio_wav and question:
        out["heard"] = question
    out["seconds"] = round(res.seconds, 1)
    return out
