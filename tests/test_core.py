"""Model-free tests: scam rules, the code-owned verdict logic, and the API with a fake model."""

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kitchen_table import config, reader, redflags
from kitchen_table.ollama_client import ChatResult

TODAY = date(2026, 10, 3)


@pytest.mark.parametrize("text,strong", [
    ("Pay the balance with Google Play gift cards and read us the codes.", True),
    ("Deposit cash at any Bitcoin ATM.", True),
    ("Your Social Security number has been suspended.", True),
    ("Do not tell anyone about this call, including your bank teller.", True),
    ("A warrant for your arrest will be issued.", True),
    ("Get a free $10 gift card when you open an account.", False),
    ("Never share your PIN or password with anyone, including bank employees.", False),
    ("Do not share your PIN with anyone.", False),
    ("We accept Zelle and checks.", False),
    ("FINAL NOTICE. Act now, last chance.", False),
])
def test_strong_flags(text, strong):
    assert redflags.has_strong(redflags.scan(text)) is strong


def _analysis(**kw):
    base = {"letter_type": "bill", "sender": "X", "verdict": "action_needed", "headline": "h", "summary": "s",
            "steps": [{"text": "pay", "by_date": "2026-10-20"}], "deadlines": [{"date": "2026-10-20", "what": "pay"}],
            "money": {"amount": 10, "currency": "USD", "direction": "you_owe", "already_paid_or_autopay": False},
            "scam_signals": [], "contacts": [], "glossary": [], "family_note": "n", "confidence": "high"}
    base.update(kw)
    return base


def test_strong_rule_overrides_model():
    hits = redflags.scan("pay with gift cards")
    a = reader.postprocess(_analysis(verdict="action_needed"), hits, TODAY)
    assert a["verdict"] == "scam_warning" and a["model_verdict"] == "action_needed"
    assert "strong_scam_rule" in a["overrides"]


def test_deadline_within_week_escalates():
    a = reader.postprocess(_analysis(deadlines=[{"date": "October 8, 2026", "what": "x"}]), [], TODAY)
    assert a["deadlines"][0] == {"date": "2026-10-08", "what": "x", "days_left": 5}
    assert a["verdict"] == "urgent"


def test_far_deadline_stays_action_needed():
    a = reader.postprocess(_analysis(), [], TODAY)
    assert a["verdict"] == "action_needed" and a["deadlines"][0]["days_left"] == 17


def test_refund_never_escalated():
    a = reader.postprocess(_analysis(verdict="file_it", money={"amount": 63.5, "currency": "USD",
                           "direction": "you_receive", "already_paid_or_autopay": False},
                           deadlines=[{"date": "2026-10-05", "what": "deposit"}]), [], TODAY)
    assert a["verdict"] == "file_it"


def test_bad_dates_dropped_and_sorted():
    a = reader.postprocess(_analysis(deadlines=[{"date": "2026-11-15", "what": "b"}, {"date": "soon", "what": "?"},
                                                {"date": "10/12/2026", "what": "a"}]), [], TODAY)
    assert [d["date"] for d in a["deadlines"]] == ["2026-10-12", "2026-11-15"]


# ---------- API with a fake model ----------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.sqlite3")

    def fake_chat(messages, **kw):
        if kw.get("schema") is reader.ANALYSIS_SCHEMA:
            return ChatResult(json.dumps(_analysis(deadlines=[{"date": "2099-01-01", "what": "pay"}])), 0.1, 1, 1)
        if kw.get("schema") is reader.ASK_SCHEMA:
            return ChatResult(json.dumps({"heard": "q", "answer": "Yes."}), 0.1, 1, 1)
        return ChatResult("WATER BILL Amount due $10.00", 0.1, 1, 1)

    monkeypatch.setattr(reader, "chat", fake_chat)
    from kitchen_table.app import app
    return TestClient(app)


def _jpeg():
    import io
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (40, 60), "white").save(b, "JPEG")
    return b.getvalue()


def test_read_ask_calendar_flow(client):
    r = client.post("/api/letters", files=[("pages", ("a.jpg", _jpeg(), "image/jpeg"))], data={"lang": "ru"})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    assert client.get("/api/letters").json()[0]["id"] == lid
    ans = client.post(f"/api/letters/{lid}/ask", data={"lang": "ru", "question": "Платить?"}).json()
    assert ans["question"] == "Платить?" and ans["answer"] == "Yes."
    assert client.get(f"/api/letters/{lid}").json()["qa"][0]["answer"] == "Yes."
    ics = client.get(f"/api/letters/{lid}/calendar.ics").text
    assert "DTSTART;VALUE=DATE:20990101" in ics and ics.endswith("END:VCALENDAR\r\n")
    client.post(f"/api/letters/{lid}/handled", json={"handled": True})
    assert client.get(f"/api/letters/{lid}").json()["handled"] is True
    client.delete(f"/api/letters/{lid}")
    assert client.get(f"/api/letters/{lid}").status_code == 404


def test_builtin_ui_strings(client):
    ru = client.get("/api/ui/ru").json()
    en = client.get("/api/ui/en").json()
    assert set(ru) == set(en) and ru["read_letter"] == "Прочитать письмо"


def test_rejects_too_many_pages(client):
    files = [("pages", (f"{i}.jpg", _jpeg(), "image/jpeg")) for i in range(7)]
    assert client.post("/api/letters", files=files).status_code == 400
