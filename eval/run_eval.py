"""Score the pipeline on the 15 fictional letters.

    python eval/run_eval.py --models gemma4:e4b gemma4:26b --lang ru --variant photo

Writes eval/results/<model>-<variant>-<lang>.json and prints a summary table.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kitchen_table import reader  # noqa: E402

HERE = Path(__file__).parent
LETTERS = HERE / "letters"
RESULTS = HERE / "results"

SCRIPTS = {"ru": r"[А-Яа-яЁё]", "uk": r"[А-Яа-яІіЇїЄєҐґ]", "zh": r"[一-鿿]", "ko": r"[가-힯]",
           "ar": r"[؀-ۿ]", "hi": r"[ऀ-ॿ]"}


def in_language(text: str, lang: str) -> bool | None:
    pat = SCRIPTS.get(lang)
    if not pat or not text:
        return None
    letters = re.findall(r"\w", text)
    return len(re.findall(pat, text)) / max(1, len(letters)) > 0.6


def score(truth: dict, out: dict, lang: str) -> dict:
    a = out["analysis"]
    got_dates = {d["date"] for d in a["deadlines"]}
    want = set(truth["deadlines"])
    amount_ok = None
    if truth.get("amount") is not None:
        amount_ok = (a["money"].get("amount") is not None and abs(a["money"]["amount"] - truth["amount"]) < 0.01
                     and a["money"].get("direction") == truth["direction"])
    scam_pred = a["verdict"] == "scam_warning"
    return {
        "verdict": a["verdict"],
        "model_verdict": a["model_verdict"],
        "verdict_ok": a["verdict"] in truth["verdict"],
        # "unsure" (asks for a new photo) is a miss, but a safe one; "file_it" on a real bill is not.
        "safe": a["verdict"] in truth["verdict"] or a["verdict"] == "unsure"
                or (a["verdict"] in ("urgent", "scam_warning") and "file_it" not in truth["verdict"]),
        "model_verdict_ok": a["model_verdict"] in truth["verdict"],
        "scam_truth": truth["scam"],
        "scam_pred": scam_pred,
        "model_scam_pred": a["model_verdict"] == "scam_warning",
        "deadline_recall": (len(want & got_dates) / len(want)) if want and not truth.get("deadline_optional") else None,
        "deadlines_got": sorted(got_dates),
        "amount_ok": amount_ok,
        "in_language": in_language(a["headline"] + " " + a["summary"], lang),
        "seconds": out["timing"]["read_seconds"] + out["timing"]["explain_seconds"],
        "overrides": a["overrides"],
    }


def summarise(rows: list[dict]) -> dict:
    def rate(key, filt=lambda r: True):
        vals = [r[key] for r in rows if filt(r) and r[key] is not None]
        return (sum(1 for v in vals if v) / len(vals), len(vals)) if vals else (None, 0)

    scam_rows = [r for r in rows if r["scam_truth"] is not None]
    tp = sum(r["scam_pred"] and r["scam_truth"] for r in scam_rows)
    fn = sum((not r["scam_pred"]) and r["scam_truth"] for r in scam_rows)
    fp = sum(r["scam_pred"] and not r["scam_truth"] for r in scam_rows)
    mtp = sum(r["model_scam_pred"] and r["scam_truth"] for r in scam_rows)
    mfn = sum((not r["model_scam_pred"]) and r["scam_truth"] for r in scam_rows)
    recalls = [r["deadline_recall"] for r in rows if r["deadline_recall"] is not None]
    secs = sorted(r["seconds"] for r in rows)
    return {
        "n": len(rows),
        "verdict_acc": rate("verdict_ok"),
        "safe_rate": rate("safe"),
        "model_only_verdict_acc": rate("model_verdict_ok"),
        "scam_recall": tp / (tp + fn) if tp + fn else None,
        "model_only_scam_recall": mtp / (mtp + mfn) if mtp + mfn else None,
        "scam_false_alarms": fp,
        "deadline_recall": sum(recalls) / len(recalls) if recalls else None,
        "amount_acc": rate("amount_ok"),
        "in_language": rate("in_language"),
        "median_seconds": secs[len(secs) // 2] if secs else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gemma4:e4b"])
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--variant", choices=["photo", "png"], default="photo")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--set", choices=["core", "hard", "holdout", "all"], default="all")
    args = ap.parse_args()

    truth = json.loads((LETTERS / "truth.json").read_text())
    today = date.fromisoformat(truth["today"])
    RESULTS.mkdir(exist_ok=True)

    for model in args.models:
        rows = []
        for lid, t in truth["letters"].items():
            if args.only and lid not in args.only:
                continue
            if args.set != "all" and t["set"] != args.set:
                continue
            if args.variant == "photo":
                imgs = [(LETTERS / p).read_bytes() for p in t["photos"]]
            else:
                imgs = [(LETTERS / p.replace(".photo.jpg", ".png")).read_bytes() for p in t["photos"]]
            out = reader.read_letter(imgs, args.lang, "en", model=model, today=today)
            s = {"id": lid, "set": t["set"], **score(t, out, args.lang)}
            rows.append(s)
            print(f"{model:12} {lid:20} {s['verdict']:14} ok={s['verdict_ok']!s:5} "
                  f"dl={s['deadline_recall']} amt={s['amount_ok']} lang={s['in_language']} {s['seconds']:.1f}s"
                  + (f"  override={s['overrides']}" if s["overrides"] else ""), flush=True)
            (RESULTS / f"{model.replace(':', '_')}-{args.variant}-{args.lang}.raw.json").open("a").write(
                json.dumps({"id": lid, "out": out}, ensure_ascii=False) + "\n")
        summary = summarise(rows)
        (RESULTS / f"{model.replace(':', '_')}-{args.variant}-{args.lang}-{args.set}.json").write_text(
            json.dumps({"model": model, "variant": args.variant, "lang": args.lang, "summary": summary, "rows": rows},
                       ensure_ascii=False, indent=1))
        print(json.dumps({"model": model, **summary}, indent=1, default=str))


if __name__ == "__main__":
    main()
