# Evaluation

**Question:** if my parent photographs a letter on the kitchen table, does Kitchen Table tell them the right thing, in their language, without ever saying "nothing to do" about something that matters?

## The letters

30 letters, all from **invented** organisations (phone numbers in the reserved 555-01xx range), written as HTML, rendered with headless Chrome, then turned into "phone photos": placed on a wood-grain table, rotated a few degrees, perspective-skewed, shadowed, slightly blurred, JPEG-compressed. Ground truth lives in `eval/letters/truth.json`; the eval pretends today is 2026-10-03.

| Set | n | What's in it | Answer language |
|---|---|---|---|
| core | 15 | water bill, shut-off notice, insurance EOB ("this is not a bill"), clinic bill, jury summons, SSN-suspension scam, lottery-fee scam, car-warranty "FINAL NOTICE" ad, pharmacy pickup, property tax, plan change notice, refund check, appointment reminder, "account locked" phishing letter, CD maturity | Russian |
| hard | 9 | a $89 "certified deed copy" mailer, a deadline that only appears on **page 2**, a legitimate debt-collection validation notice, a coverage-ending deadline hidden in **fine print** under a friendly newsletter, a **Spanish** school letter, a private "tax resolution" firm dressed as a levy notice, a benefits-card phishing letter, a **dark and blurry** photo, a photo taken **sideways** | Russian |
| holdout | 6 | written **after** all prompt and rule changes, run once, not tuned on: a homestead-exemption filing service, an HOA violation notice, a Cash App "rebate" scam, a state revenue adjustment (refund), lab results needing a re-test "within 5 days", a library book-sale flyer | Ukrainian |

## Scoring

- **Verdict**: the final verdict is in the set of acceptable verdicts for that letter (e.g. a jury summons may be *urgent* or *action needed*; a refund may be *file it* or *action needed*).
- **Safe**: the verdict is acceptable, or it's *unsure* (asks for a new photo), or it errs toward more caution than needed. "Nothing to do" on a real bill is unsafe.
- **Model-only**: the same metric using the model's own verdict, before the code-level overrides (scam rules, ≤7-day escalation, bad-photo guard).
- **Scam recall**: share of the 8 scam / predatory letters that end as a scam warning. The car-warranty ad is excluded (either *file it* or *scam* is fine).
- **Deadline recall**: share of must-act-by dates extracted exactly, for letters that have one.
- **Amount + direction**: exact amount *and* whether the parent owes it or receives it.
- **Right language**: headline + summary are ≥60% in the expected script (Cyrillic for ru/uk).

## Results

| Model | Set (n, answer language) | Verdict | Safe | Model-only verdict | Scam recall | Model-only scam recall | False scam alarms | Deadline recall | Amount + direction | Answer in right language | Median time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma4:e2b | core (15, ru) | 87% | 87% | 80% | 100% | 100% | 0 | 92% | 100% | 7% | 2.0s |
| gemma4:e2b | hard (9, ru) | 89% | 89% | 56% | 67% | 0% | 0 | 83% | 75% | 0% | 2.1s |
| gemma4:e2b | holdout (6, uk) | 67% | 67% | 83% | 50% | 50% | 0 | 100% | 100% | 0% | 2.2s |
| gemma4:e4b | core (15, ru) | 100% | 100% | 87% | 100% | 100% | 0 | 100% | 100% | 100% | 2.5s |
| gemma4:e4b | hard (9, ru) | 89% | 100% | 78% | 100% | 100% | 0 | 83% | 100% | 100% | 2.6s |
| gemma4:e4b | holdout (6, uk) | 100% | 100% | 100% | 100% | 100% | 0 | 100% | 100% | 100% | 2.9s |
| gemma4:26b | core (15, ru) | 100% | 100% | 100% | 100% | 100% | 0 | 100% | 100% | 100% | 3.5s |
| gemma4:26b | hard (9, ru) | 100% | 100% | 89% | 100% | 100% | 0 | 100% | 100% | 100% | 3.6s |
| gemma4:26b | holdout (6, uk) | 100% | 100% | 100% | 100% | 100% | 0 | 100% | 100% | 100% | 3.5s |

Timing is end to end (read + explain) on an RTX 5090. With the GPU disabled, `gemma4:e4b` took ~39 s per letter on a 16-core Ryzen 9 9950X; expect a minute or more on a laptop.

## What the numbers say

1. **26b is right on all 30.** e4b is right on 29 and *safe* on all 30. The one miss is the dark, blurry photo, where e4b read "2026" as "2020" and "$84.17" as "$64.17" and confidently called it an old bill. The photo-quality gate (brightness < 90, contrast < 35 or edge variance < 150) caught that photo and only that photo out of 31; the verdict became *unsure: please take another photo* instead of *nothing to do*. Auto-contrast fixed the amount but not the year.
2. **The scam rules are a seatbelt, not the engine, for e4b/26b.** Both models flagged every scam on their own in the final runs. On e2b they matter: e2b alone caught **0 of 3** hard-set scams; with the rules it caught 2.
3. **One rule was added because of this eval.** e4b initially called the $89 deed-copy mailer *action needed*. These mailers are legal, so none of the money-transfer rules fire; their tell is the required disclaimer ("not affiliated with any county or government agency") next to a fee. I added that rule (`lookalike_official`), then wrote the holdout set, which includes a new look-alike (homestead filing service) that both models + rule handled. The hard-set numbers above include the rule, so they are partly tuned; the holdout numbers are not.
4. **Overrides can hurt a weak model.** On the holdout set e2b scored *better* model-only (5/6) than with overrides (4/6): it invented deadlines for a library flyer, and the "file it + steps + upcoming deadline ⇒ action needed / urgent" rule amplified that. With e4b/26b the overrides only ever corrected verdicts.
5. **e2b doesn't follow the language instruction.** 3% of its answers were in Russian/Ukrainian; it explains in English. That alone rules it out for this user.
6. **26b can't hear.** Gemma 4's 26B model accepts images but not audio; the edge models (e2b/e4b) take both. Kitchen Table transcribes spoken questions with e4b and answers with whichever model reads the letters.

## Caveats

- 30 letters, one run each, synthetic and typeset. Real mail has logos, colour, creases, handwriting and window envelopes; none of that is tested.
- The ground-truth "acceptable verdict" sets are my judgement.
- The holdout set is small (6). It is the only number here that wasn't seen while tuning.
- Language check is script-based (Cyrillic share), not a fluency judgement.

Raw per-letter outputs are written to `eval/results/*.raw.json` (git-ignored); summaries to `eval/results/*.json`.
