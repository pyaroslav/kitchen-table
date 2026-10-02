"""Build EVAL.md's results table from eval/results/*.json."""

import json
from pathlib import Path

RES = Path(__file__).parent / "results"
ORDER = ["gemma4:e2b", "gemma4:e4b", "gemma4:26b"]
SETS = ["core", "hard", "holdout"]


def pct(v):
    if isinstance(v, list):
        v = v[0]
    return "—" if v is None else f"{v * 100:.0f}%"


rows = []
for model in ORDER:
    for st in SETS:
        f = next(iter(sorted(RES.glob(f"{model.replace(':', '_')}-photo-*-{st}.json"))), None)
        if not f:
            continue
        d = json.loads(f.read_text())
        s = d["summary"]
        rows.append(f"| {model} | {st} ({s['n']}, {d['lang']}) | {pct(s['verdict_acc'])} | {pct(s['safe_rate'])} | "
                    f"{pct(s['model_only_verdict_acc'])} | {pct(s['scam_recall'])} | {pct(s['model_only_scam_recall'])} | "
                    f"{s['scam_false_alarms']} | {pct(s['deadline_recall'])} | {pct(s['amount_acc'])} | "
                    f"{pct(s['in_language'])} | {s['median_seconds']:.1f}s |")

print("| Model | Set (n, answer language) | Verdict | Safe | Model-only verdict | Scam recall | Model-only scam recall | False scam alarms | Deadline recall | Amount + direction | Answer in right language | Median time |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
print("\n".join(rows))
