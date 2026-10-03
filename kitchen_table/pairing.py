"""Only paired devices may talk to the API.

The server listens on the home Wi-Fi, and everyone on that Wi-Fi (guests, a smart TV,
a neighbour who knows the password) would otherwise be able to read every letter.
At startup the computer shows a QR code holding a secret key; the phone scans it
once, gets a long-lived HttpOnly cookie, and is paired. The computer itself
(localhost) never needs pairing.
"""

import hmac
import secrets

from . import config

COOKIE = "kt_key"
LOCAL = {"127.0.0.1", "::1"}


def key_path():
    return config.DATA_DIR / "pairing.key"


def get_key(rotate: bool = False) -> str:
    p = key_path()
    if p.exists() and not rotate:
        return p.read_text().strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(18)
    p.write_text(key)
    p.chmod(0o600)
    return key


def is_paired(client_host: str | None, cookie: str | None) -> bool:
    if client_host in LOCAL:
        return True
    return bool(cookie) and hmac.compare_digest(cookie, get_key())
