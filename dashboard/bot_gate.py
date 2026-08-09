"""Session CAPTCHA gate helpers used to keep simple bots off public pages."""

from __future__ import annotations

import html
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

SESSION_OK_KEY = "bot_gate_ok_at"
SESSION_CODE_KEY = "bot_captcha_code"
SESSION_ISSUED_KEY = "bot_captcha_issued_at"
SESSION_FAILS_KEY = "bot_captcha_fails"

# Skip look-alikes: 0/O, 1/I/L
CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def gate_enabled() -> bool:
    return bool(getattr(settings, "BOT_GATE_ENABLED", True))


def ttl_seconds() -> int:
    return int(getattr(settings, "BOT_GATE_TTL_SECONDS", 60 * 60 * 24))


def max_attempts() -> int:
    return int(getattr(settings, "BOT_GATE_MAX_ATTEMPTS", 8))


def lockout_seconds() -> int:
    return int(getattr(settings, "BOT_GATE_LOCKOUT_SECONDS", 300))


def min_solve_seconds() -> float:
    return float(getattr(settings, "BOT_GATE_MIN_SOLVE_SECONDS", 1.5))


def is_verified(request: HttpRequest) -> bool:
    if not gate_enabled():
        return True
    stamped = request.session.get(SESSION_OK_KEY)
    if not stamped:
        return False
    try:
        ok_at = float(stamped)
    except (TypeError, ValueError):
        return False
    return (time.time() - ok_at) <= ttl_seconds()


def mark_verified(request: HttpRequest) -> None:
    request.session[SESSION_OK_KEY] = time.time()
    request.session.pop(SESSION_CODE_KEY, None)
    request.session.pop(SESSION_ISSUED_KEY, None)
    request.session.pop(SESSION_FAILS_KEY, None)
    request.session.modified = True


def issue_captcha(request: HttpRequest) -> str:
    code = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(5))
    request.session[SESSION_CODE_KEY] = code
    request.session[SESSION_ISSUED_KEY] = time.time()
    request.session.modified = True
    return code


def captcha_code(request: HttpRequest) -> str | None:
    code = request.session.get(SESSION_CODE_KEY)
    return code if isinstance(code, str) else None


def client_ip(request: HttpRequest) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.META.get("REMOTE_ADDR") or "unknown"


def _lock_key(request: HttpRequest) -> str:
    return f"bot_gate_lock:{client_ip(request)}"


def is_locked(request: HttpRequest) -> bool:
    return bool(cache.get(_lock_key(request)))


def register_failure(request: HttpRequest) -> None:
    fails = int(request.session.get(SESSION_FAILS_KEY) or 0) + 1
    request.session[SESSION_FAILS_KEY] = fails
    request.session.modified = True
    if fails >= max_attempts():
        cache.set(_lock_key(request), 1, timeout=lockout_seconds())
        request.session[SESSION_FAILS_KEY] = 0


def check_answer(request: HttpRequest, answer: str, honeypot: str) -> tuple[bool, str]:
    if is_locked(request):
        return False, "Too many attempts. Try again in a few minutes."

    if honeypot.strip():
        register_failure(request)
        return False, "Verification failed. Try again."

    expected = captcha_code(request)
    issued_at = request.session.get(SESSION_ISSUED_KEY)
    if not expected or issued_at is None:
        return False, "CAPTCHA expired. Refresh and try again."

    try:
        age = time.time() - float(issued_at)
    except (TypeError, ValueError):
        return False, "CAPTCHA expired. Refresh and try again."

    if age < min_solve_seconds():
        register_failure(request)
        return False, "That was too fast. Please solve the CAPTCHA."

    cleaned = "".join(ch for ch in answer.upper() if ch.isalnum())
    if cleaned != expected.upper():
        register_failure(request)
        issue_captcha(request)
        return False, "Incorrect CAPTCHA. Try again."

    mark_verified(request)
    return True, ""


def safe_next_url(request: HttpRequest, candidate: str | None) -> str:
    fallback = reverse("home")
    if not candidate:
        return fallback
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


def render_captcha_svg(code: str) -> str:
    """Build a lightweight SVG CAPTCHA (no image library required)."""
    width, height = 200, 70
    lines = []
    for _ in range(10):
        x1, y1 = secrets.randbelow(width), secrets.randbelow(height)
        x2, y2 = secrets.randbelow(width), secrets.randbelow(height)
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#c8beaa" stroke-width="1"/>'
        )

    dots = []
    for _ in range(40):
        cx, cy = secrets.randbelow(width), secrets.randbelow(height)
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="1" fill="#8a8274"/>')

    chars = []
    x = 22
    for ch in code:
        y = 42 + secrets.randbelow(8) - 4
        rot = secrets.randbelow(21) - 10
        chars.append(
            f'<text x="{x}" y="{y}" transform="rotate({rot} {x} {y})" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="28" '
            f'font-weight="700" fill="#1c2430">{html.escape(ch)}</text>'
        )
        x += 34

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="CAPTCHA">'
        f'<rect width="100%" height="100%" fill="#f3efe6"/>'
        f'{"".join(lines)}{"".join(dots)}{"".join(chars)}'
        f"</svg>"
    )
