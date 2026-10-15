"""Optional dashboard login.

When ``web`` is set in secrets.yaml (a scrypt password hash and/or a bearer token), every
write (POST/PUT/PATCH/DELETE) needs a signed session cookie or ``Authorization: Bearer``.
Reads stay open, so the dashboard should still live on localhost or a private network.

Every unsafe request is also checked for CSRF: a browser ``Origin`` (or, failing that,
``Referer``) must match the site the request was sent to. The session cookie is
``SameSite=Lax`` and ``HttpOnly``, and ``Secure`` when the request came in over https.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import secrets as _secrets
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

COOKIE = "fermentd_session"
SESSION_TTL_S = 30 * 24 * 3600
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
LOGIN_PATH = "/login"
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
_MAX_FAILURES = 5
_FAILURE_WINDOW_S = 300.0


# --- password hashing (stdlib scrypt) -------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, *, n: int = _SCRYPT_N, r: int = _SCRYPT_R, p: int = _SCRYPT_P) -> str:
    """Return ``scrypt$n$r$p$salt$hash`` for storing in secrets.yaml."""
    if not password:
        raise ValueError("password must not be empty")
    salt = _secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def is_password_hash(value: str) -> bool:
    parts = value.split("$")
    return len(parts) == 6 and parts[0] == "scrypt" and all(x.isdigit() for x in parts[1:4])


# --- settings --------------------------------------------------------------------------

@dataclass
class AuthSettings:
    password_hash: str | None = None
    token: str | None = field(default=None, repr=False)
    session_secret: str | None = field(default=None, repr=False)
    allowed_origins: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return bool(self.password_hash or self.token)

    def signing_key(self) -> bytes:
        # Without an explicit secret the key follows the credentials, so changing the
        # password or token logs every browser out.
        material = self.session_secret or f"{self.password_hash or ''}\n{self.token or ''}"
        return hashlib.sha256(b"fermentd-session\n" + material.encode()).digest()


def make_session(settings: AuthSettings, now: float | None = None) -> str:
    payload = _b64(json.dumps({"exp": int((now or time.time()) + SESSION_TTL_S)}).encode())
    sig = _b64(hmac.new(settings.signing_key(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def session_valid(settings: AuthSettings, value: str | None, now: float | None = None) -> bool:
    if not value or "." not in value:
        return False
    payload, sig = value.rsplit(".", 1)
    expected = _b64(hmac.new(settings.signing_key(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        exp = json.loads(_unb64(payload))["exp"]
    except (ValueError, KeyError, TypeError):
        return False
    return float(exp) > (now or time.time())


def bearer_valid(settings: AuthSettings, header: str | None) -> bool:
    if not settings.token or not header:
        return False
    scheme, _, value = header.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(value.strip().encode(), settings.token.encode())


def is_authenticated(request: Request) -> bool:
    settings: AuthSettings = request.app.state.auth
    if not settings.enabled:
        return True
    return bearer_valid(settings, request.headers.get("authorization")) or session_valid(
        settings, request.cookies.get(COOKIE)
    )


# --- CSRF ------------------------------------------------------------------------------

def _origin_of(url: str) -> str | None:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def own_origin(request: Request) -> str:
    """scheme://host the browser used. Behind a proxy uvicorn applies X-Forwarded-Proto."""
    host = (request.headers.get("host") or request.url.netloc).lower()
    return f"{request.url.scheme}://{host}"


def _default_port_variants(origin: str) -> set[str]:
    out = {origin}
    if origin.startswith("https://") and origin.endswith(":443"):
        out.add(origin[: -len(":443")])
    if origin.startswith("http://") and origin.endswith(":80"):
        out.add(origin[: -len(":80")])
    return out


def csrf_ok(request: Request, allowed: Iterable[str] = (), require_header: bool = False) -> bool:
    trusted = _default_port_variants(own_origin(request))
    for extra in allowed:
        normalized = _origin_of(extra)
        if normalized:
            trusted |= _default_port_variants(normalized)
    origin = request.headers.get("origin")
    if origin is not None:
        return origin.lower() != "null" and (_origin_of(origin) or "") in trusted
    referer = request.headers.get("referer")
    if referer is not None:
        return (_origin_of(referer) or "") in trusted
    # No Origin and no Referer: not something a browser sends for a cross-site form post.
    # Still refuse it when a session cookie is what would authorize it.
    return not require_header


# --- login rate limit ----------------------------------------------------------------

class LoginThrottle:
    def __init__(self, max_failures: int = _MAX_FAILURES, window_s: float = _FAILURE_WINDOW_S) -> None:
        self.max_failures = max_failures
        self.window_s = window_s
        self._failures: dict[str, list[float]] = {}

    def blocked(self, key: str, now: float | None = None) -> bool:
        now = now or time.monotonic()
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_s]
        self._failures[key] = recent
        return len(recent) >= self.max_failures

    def fail(self, key: str, now: float | None = None) -> None:
        self._failures.setdefault(key, []).append(now or time.monotonic())

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)


# --- middleware ----------------------------------------------------------------------

class AuthMiddleware:
    """CSRF check on every unsafe request; login required for writes when auth is on."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in UNSAFE:
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        settings: AuthSettings = request.app.state.auth
        has_bearer = bearer_valid(settings, request.headers.get("authorization"))
        # Bearer requests carry no ambient browser credential, so CSRF does not apply.
        if not has_bearer:
            needs_header = settings.enabled and COOKIE in request.cookies
            if not csrf_ok(request, settings.allowed_origins, require_header=needs_header):
                await _deny(request, 403, "cross-site request refused")(scope, receive, send)
                return
        if settings.enabled and request.url.path != LOGIN_PATH and not has_bearer:
            if not session_valid(settings, request.cookies.get(COOKIE)):
                await _deny(request, 401, "login required")(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _wants_html(request: Request) -> bool:
    if request.headers.get("authorization"):
        return False
    accept = request.headers.get("accept", "")
    return "text/html" in accept or request.headers.get("hx-request") == "true" or (
        request.headers.get("content-type", "").startswith(("application/x-www-form-urlencoded", "multipart/"))
    )


def _deny(request: Request, status: int, message: str) -> Response:
    if status == 401 and _wants_html(request):
        back = request.headers.get("referer")
        target = urlsplit(back).path if back and _origin_of(back) == own_origin(request) else "/"
        location = f"{LOGIN_PATH}?next={quote(target or '/')}"
        if request.headers.get("hx-request") == "true":
            return Response(status_code=401, headers={"HX-Redirect": location})
        return RedirectResponse(location, status_code=303)
    return JSONResponse({"detail": message}, status_code=status)


def safe_next(target: str | None) -> str:
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


def set_session_cookie(response: Response, request: Request, settings: AuthSettings) -> None:
    response.set_cookie(
        COOKIE,
        make_session(settings),
        max_age=SESSION_TTL_S,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )


# --- bind safety -----------------------------------------------------------------------

_TAILNET_V4 = ipaddress.ip_network("100.64.0.0/10")
_TAILNET_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")


def private_bind(host: str) -> bool:
    """True for loopback and Tailscale (CGNAT / tailnet ULA) addresses."""
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    return (ip.version == 4 and ip in _TAILNET_V4) or (ip.version == 6 and ip in _TAILNET_V6)


def check_bind(host: str, settings: AuthSettings, insecure: bool) -> str | None:
    """Return an error message if the dashboard would be exposed without a login."""
    if settings.enabled or insecure or private_bind(host):
        return None
    return (
        f"refusing to serve the dashboard on {host!r} without a login. Bind to 127.0.0.1 or a "
        "Tailscale address, set a password with `fermentd-ctl set-password`, or pass "
        "--insecure-no-auth (or web.allow_insecure: true) if you really mean it."
    )
