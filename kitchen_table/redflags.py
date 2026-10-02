"""Deterministic scam red flags.

The model is good at reading letters, but "is this a scam?" is the one question
where I don't want to depend on a single probabilistic answer. These rules run
on the transcript before and after Gemma, and a *strong* flag always wins:
no real bank, utility or government office asks for gift cards or Bitcoin.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    strong: bool
    pattern: re.Pattern
    why: str  # English; Gemma rewrites it into the reader's language


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.IGNORECASE)


# A demand for money must sit next to the payment method for the strong rules.
PAY = r"\b(pay|payment|paid|purchase|buy|send|deposit|settle|transfer)\b"

RULES = [
    Rule("gift_cards", True,
         _r(PAY + r"[^.]{0,60}\b(gift ?cards?|google play|itunes|steam cards?)\b|\b(gift ?cards?|google play cards?|itunes cards?)[^.]{0,40}\b(codes?|numbers? on the back|to settle|as payment)\b"),
         "Asks for payment with gift cards. Real companies and governments never do this."),
    Rule("crypto", True,
         _r(PAY + r"[^.]{0,60}\b(bitcoin|btc|crypto ?currency|crypto|usdt|tether|ethereum)\b|\bbitcoin atm\b"),
         "Asks for cryptocurrency or a Bitcoin ATM. This is a classic scam."),
    Rule("wire_or_p2p", False,
         _r(r"\b(western union|moneygram|wire (the )?(money|funds|payment) to|zelle|cash ?app|venmo)\b"),
         "Asks you to send money by wire or a person-to-person app, which can't be reversed."),
    Rule("secrecy", True,
         _r(r"\b(do not|don't) (tell|inform|discuss this with) (anyone|your family|family members|your bank|bank (staff|tellers?))\b|\bkeep this (matter |call |letter )?(a )?secret\b"),
         "Tells you to keep it secret from family or your bank. Real offices never do."),
    Rule("arrest_threat", True,
         _r(r"\b(warrant (for|of) (your )?arrest|will be arrested|arrest warrant|police will|deportation|deported)\b"),
         "Threatens arrest or deportation to scare you into paying."),
    Rule("ssn_suspended", True,
         _r(r"\bsocial security (number|card) (has been |is |will be )?(suspended|blocked|frozen|cancell?ed)\b"),
         "Says your Social Security number is 'suspended'. That does not happen."),
    Rule("extreme_urgency", False,
         _r(r"\b(within 24 hours|within 48 hours|immediately or|final notice|act now|today only|last chance)\b"),
         "Uses extreme urgency to rush you."),
    Rule("personal_email", False,
         _r(r"[\w.+-]+@(gmail|yahoo|outlook|hotmail|aol|proton(mail)?)\.(com|me)\b"),
         "An 'official' sender is using a free personal email address."),
    Rule("prize", False,
         _r(r"\b(you (have )?won|winner|lottery|sweepstakes|claim your prize|unclaimed (funds|inheritance))\b"),
         "Promises a prize or money you didn't expect."),
    Rule("fee_to_receive", False,
         _r(r"\b(processing|release|transfer|clearance) fee\b"),
         "Asks for a fee before you can receive money."),
]


def scan(text: str) -> list[dict]:
    hits = []
    for rule in RULES:
        m = rule.pattern.search(text or "")
        if m:
            hits.append({"id": rule.id, "strong": rule.strong, "why": rule.why, "evidence": m.group(0)})
    return hits


def has_strong(hits: list[dict]) -> bool:
    return any(h["strong"] for h in hits)
