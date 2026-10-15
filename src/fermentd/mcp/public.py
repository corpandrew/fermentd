"""Public, read-only MCP endpoint with a built-in OAuth 2.1 authorization server.

    fermentd-mcp-public --issuer https://<pi>.<tailnet>.ts.net:8443 --host 127.0.0.1 --port 8766 \\
        --db data/fermentd.db --oauth-db data/mcp-oauth.db --secrets config/secrets.yaml

Meant to sit behind Tailscale Funnel for cloud MCP clients (Gemini's custom connector) that cannot
reach the tailnet. Only read tools are registered (``build_server(read_only=True)``), so nothing
reachable here can change the Pi. Every MCP request needs an OAuth access token:

* one pre-registered confidential client (``mcp_public.client_id`` + sha256 of the secret in
  secrets.yaml; ``init-client`` generates both). No dynamic client registration.
* ``/authorize`` asks for the dashboard password (``web.password_hash``) on a login + consent page,
  rate limited per IP and globally.
* ``/token``: ``authorization_code`` (PKCE S256, single-use codes) and ``refresh_token`` (rotating;
  reusing an old refresh token revokes the whole chain). Access tokens live one hour.
* tokens and codes are stored only as sha256 hashes, in their own sqlite file.
* redirect URIs: Gemini's callbacks, other https URLs on google.com / googleusercontent.com, and any
  listed in ``mcp_public.redirect_uris``. Rejected ones are logged.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import html
import json
import logging
import secrets as _secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from fermentd.web.auth import LoginThrottle, verify_password

log = logging.getLogger("fermentd.mcp.public")

SCOPE = "fermentd.read"
ACCESS_TTL_S = 3600
REFRESH_TTL_S = 30 * 24 * 3600
CODE_TTL_S = 300
FORM_TTL_S = 600
GEMINI_REDIRECTS = (
    "https://vertexaisearch.cloud.google.com/oauth-redirect",
    "https://vertexaisearch.cloud.google.com/static/oauth/oauth.html",
)
GOOGLE_DOMAINS = ("google.com", "googleusercontent.com")
NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
PAGE_HEADERS = {**NO_STORE, "X-Frame-Options": "DENY", "Content-Security-Policy":
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'",
                "Referrer-Policy": "no-referrer"}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def pkce_s256(verifier: str) -> str:
    return _b64(hashlib.sha256(verifier.encode()).digest())


# --- settings --------------------------------------------------------------------------

@dataclass
class PublicSettings:
    issuer: str
    client_id: str
    client_secret_sha256: str = field(repr=False)
    password_hash: str = field(repr=False)
    form_key: bytes = field(repr=False)
    redirect_uris: tuple[str, ...] = ()
    require_pkce: bool = True

    @property
    def resource(self) -> str:
        return f"{self.issuer}/mcp"

    @property
    def resource_metadata_url(self) -> str:
        return f"{self.issuer}/.well-known/oauth-protected-resource/mcp"

    def client_ok(self, client_id: str | None, secret: str | None) -> bool:
        if not client_id or not secret:
            return False
        ok_id = hmac.compare_digest(client_id.encode(), self.client_id.encode())
        ok_secret = hmac.compare_digest(_sha(secret).encode(), self.client_secret_sha256.encode())
        return ok_id and ok_secret

    def redirect_ok(self, uri: str | None) -> bool:
        if not uri:
            return False
        if uri in GEMINI_REDIRECTS or uri in self.redirect_uris:
            return True
        parts = urlsplit(uri)
        host = (parts.hostname or "").lower()
        allowed = parts.scheme == "https" and not parts.username and not parts.password and not parts.fragment \
            and parts.port in (None, 443) and any(host == d or host.endswith("." + d) for d in GOOGLE_DOMAINS)
        if not allowed:
            log.warning("rejected OAuth redirect_uri %r", uri)
        return allowed


# --- storage ---------------------------------------------------------------------------

class OAuthStore:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS oauth_codes (
                  code_hash TEXT PRIMARY KEY, client_id TEXT NOT NULL, redirect_uri TEXT NOT NULL,
                  challenge TEXT, scope TEXT NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0,
                  family TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                  token_hash TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('access','refresh')),
                  client_id TEXT NOT NULL, scope TEXT NOT NULL, family TEXT NOT NULL,
                  expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS oauth_tokens_family ON oauth_tokens(family);
                """
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def new_code(self, client_id: str, redirect_uri: str, challenge: str | None, scope: str,
                 now: float | None = None) -> str:
        code = _secrets.token_urlsafe(32)
        now = now or time.time()
        with self._conn() as c:
            c.execute("DELETE FROM oauth_codes WHERE expires_at < ?", (now - 86400,))
            c.execute("INSERT INTO oauth_codes VALUES (?,?,?,?,?,?,0,?)",
                      (_sha(code), client_id, redirect_uri, challenge, scope, now + CODE_TTL_S,
                       _secrets.token_hex(8)))
        return code

    def take_code(self, code: str, now: float | None = None):
        """Mark the code used and return its row; on reuse revoke what it issued and return None."""
        now = now or time.time()
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM oauth_codes WHERE code_hash = ?", (_sha(code),)).fetchone()
            if row is None:
                c.execute("COMMIT")
                return None
            if row["used"]:
                c.execute("UPDATE oauth_tokens SET revoked = 1 WHERE family = ?", (row["family"],))
                c.execute("COMMIT")
                log.warning("authorization code reused; revoked its tokens")
                return None
            c.execute("UPDATE oauth_codes SET used = 1 WHERE code_hash = ?", (row["code_hash"],))
            c.execute("COMMIT")
            return row if row["expires_at"] >= now else None

    def issue(self, client_id: str, scope: str, family: str, now: float | None = None) -> dict:
        now = now or time.time()
        access, refresh = _secrets.token_urlsafe(32), _secrets.token_urlsafe(32)
        with self._conn() as c:
            c.execute("DELETE FROM oauth_tokens WHERE expires_at < ?", (now - 86400,))
            c.execute("INSERT INTO oauth_tokens VALUES (?,?,?,?,?,?,0,?)",
                      (_sha(access), "access", client_id, scope, family, now + ACCESS_TTL_S, now))
            c.execute("INSERT INTO oauth_tokens VALUES (?,?,?,?,?,?,0,?)",
                      (_sha(refresh), "refresh", client_id, scope, family, now + REFRESH_TTL_S, now))
        return {"access_token": access, "token_type": "Bearer", "expires_in": ACCESS_TTL_S,
                "refresh_token": refresh, "scope": scope}

    def rotate(self, refresh: str, client_id: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM oauth_tokens WHERE token_hash = ? AND kind = 'refresh'",
                            (_sha(refresh),)).fetchone()
            if row is None or row["client_id"] != client_id:
                c.execute("COMMIT")
                return None
            if row["revoked"]:
                c.execute("UPDATE oauth_tokens SET revoked = 1 WHERE family = ?", (row["family"],))
                c.execute("COMMIT")
                log.warning("revoked refresh token reused; revoked the whole token chain")
                return None
            if row["expires_at"] < now:
                c.execute("COMMIT")
                return None
            c.execute("UPDATE oauth_tokens SET revoked = 1 WHERE family = ?", (row["family"],))
            c.execute("COMMIT")
        return self.issue(client_id, row["scope"], row["family"], now)

    def access_ok(self, token: str, now: float | None = None) -> bool:
        now = now or time.time()
        with self._conn() as c:
            row = c.execute("SELECT expires_at, revoked FROM oauth_tokens WHERE token_hash = ? AND kind = 'access'",
                            (_sha(token),)).fetchone()
        return row is not None and not row["revoked"] and row["expires_at"] >= now


# --- the app ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _oauth_error(error: str, description: str, status: int = 400, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=status,
                        headers={**NO_STORE, **(headers or {})})


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>body{{font-family:system-ui,sans-serif;max-width:26rem;margin:3rem auto;
padding:0 1rem;line-height:1.45}}input,button{{font-size:1rem;padding:.5rem;width:100%;box-sizing:border-box;
margin:.3rem 0}}.err{{color:#b00}}</style></head><body><h1>{html.escape(title)}</h1>{body}</body></html>"""
    return HTMLResponse(doc, status_code=status, headers=PAGE_HEADERS)


AUTH_PARAMS = ("response_type", "client_id", "redirect_uri", "state", "scope", "code_challenge",
               "code_challenge_method", "resource")


def create_public_app(settings: PublicSettings, store: OAuthStore, mcp_app,
                      throttle: LoginThrottle | None = None, global_throttle: LoginThrottle | None = None):
    throttle = throttle or LoginThrottle()
    global_throttle = global_throttle or LoginThrottle(max_failures=20, window_s=900)

    def resource_metadata(request: Request) -> JSONResponse:
        return JSONResponse({
            "resource": settings.resource,
            "authorization_servers": [settings.issuer],
            "scopes_supported": [SCOPE],
            "bearer_methods_supported": ["header"],
            "resource_name": "fermentd (read-only)",
        })

    def as_metadata(request: Request) -> JSONResponse:
        return JSONResponse({
            "issuer": settings.issuer,
            "authorization_endpoint": f"{settings.issuer}/authorize",
            "token_endpoint": f"{settings.issuer}/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "scopes_supported": [SCOPE],
            "authorization_response_iss_parameter_supported": True,
        })

    def sign_form(params: dict, now: float | None = None) -> str:
        body = _b64(json.dumps({"p": params, "exp": int((now or time.time()) + FORM_TTL_S)},
                               sort_keys=True).encode())
        return body + "." + _b64(hmac.new(settings.form_key, body.encode(), hashlib.sha256).digest())

    def read_form(txn: str) -> dict | None:
        body, _, sig = (txn or "").rpartition(".")
        expect = _b64(hmac.new(settings.form_key, body.encode(), hashlib.sha256).digest())
        if not body or not hmac.compare_digest(sig.encode(), expect.encode()):
            return None
        try:
            data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        except ValueError:
            return None
        return data["p"] if data.get("exp", 0) >= time.time() else None

    def back_to_client(p: dict, **query) -> RedirectResponse:
        if p.get("state"):
            query["state"] = p["state"]
        query["iss"] = settings.issuer
        sep = "&" if "?" in p["redirect_uri"] else "?"
        return RedirectResponse(p["redirect_uri"] + sep + urlencode(query), status_code=303, headers=NO_STORE)

    def check_request(p: dict) -> tuple[Response | None, bool]:
        """(error response, redirect is safe). Client and redirect errors never redirect."""
        if p.get("client_id") != settings.client_id:
            return _page("Unknown app", "<p>This app is not registered with fermentd.</p>", 400), False
        if not settings.redirect_ok(p.get("redirect_uri")):
            return _page("Redirect not allowed", "<p>That redirect address is not allowed.</p>", 400), False
        if p.get("response_type") != "code":
            return back_to_client(p, error="unsupported_response_type"), True
        if p.get("code_challenge"):
            if p.get("code_challenge_method") != "S256":
                return back_to_client(p, error="invalid_request",
                                      error_description="code_challenge_method must be S256"), True
        elif settings.require_pkce:
            log.warning("authorization request without PKCE refused")
            return back_to_client(p, error="invalid_request", error_description="PKCE (S256) is required"), True
        res = p.get("resource")
        if res and res.rstrip("/") not in (settings.resource, settings.issuer):
            return back_to_client(p, error="invalid_target"), True
        return None, True

    def login_page(p: dict, error: str = "", status: int = 200) -> HTMLResponse:
        err = f'<p class="err">{html.escape(error)}</p>' if error else ""
        body = f"""{err}<p>An app (<b>{html.escape(p['client_id'])}</b>) wants <b>read-only</b> access to fermentd:
vessels, temperatures, batches, notes and alerts. It cannot start, end or change anything.</p>
<form method="post" action="/authorize"><input type="hidden" name="txn" value="{html.escape(sign_form(p))}">
<label>Dashboard password<input type="password" name="password" autocomplete="current-password" autofocus></label>
<button name="action" value="allow">Allow read-only access</button>
<button name="action" value="deny">Deny</button></form>"""
        return _page("Connect to fermentd", body, status)

    async def authorize(request: Request) -> Response:
        if request.method == "GET":
            p = {k: request.query_params.get(k) or "" for k in AUTH_PARAMS}
            err, _ = check_request(p)
            return err or login_page(p)
        form = await request.form()
        p = read_form(str(form.get("txn") or ""))
        if p is None:
            return _page("Expired", "<p>This sign-in page expired. Start again from the app.</p>", 400)
        err, _ = check_request(p)
        if err:
            return err
        if form.get("action") == "deny":
            return back_to_client(p, error="access_denied")
        ip = _client_ip(request)
        if throttle.blocked(ip) or global_throttle.blocked("all"):
            log.warning("login throttled for %s", ip)
            return login_page(p, "Too many attempts. Wait a few minutes and try again.", 429)
        if not verify_password(str(form.get("password") or ""), settings.password_hash):
            throttle.fail(ip)
            global_throttle.fail("all")
            log.warning("failed OAuth login from %s", ip)
            return login_page(p, "Wrong password.", 401)
        throttle.clear(ip)
        code = store.new_code(p["client_id"], p["redirect_uri"], p.get("code_challenge") or None, SCOPE)
        log.info("authorized client %s for %s", p["client_id"], p["redirect_uri"])
        return back_to_client(p, code=code)

    async def token(request: Request) -> Response:
        form = await request.form()
        client_id, secret = form.get("client_id"), form.get("client_secret")
        header = request.headers.get("authorization", "")
        if header.lower().startswith("basic "):
            try:
                raw = base64.b64decode(header[6:].strip()).decode()
                from urllib.parse import unquote
                cid, _, sec = raw.partition(":")
                client_id, secret = unquote(cid), unquote(sec)
            except (ValueError, UnicodeDecodeError):
                return _oauth_error("invalid_client", "bad basic auth", 401)
        if not settings.client_ok(client_id, secret):
            log.warning("token request with bad client credentials from %s", _client_ip(request))
            return _oauth_error("invalid_client", "client authentication failed", 401,
                                {"WWW-Authenticate": 'Basic realm="fermentd"'})
        grant = form.get("grant_type")
        if grant == "authorization_code":
            row = store.take_code(str(form.get("code") or ""))
            if row is None or row["client_id"] != client_id:
                return _oauth_error("invalid_grant", "code invalid, expired or already used")
            if row["redirect_uri"] != form.get("redirect_uri"):
                return _oauth_error("invalid_grant", "redirect_uri does not match")
            verifier = str(form.get("code_verifier") or "")
            if row["challenge"]:
                if not (43 <= len(verifier) <= 128) or not hmac.compare_digest(
                        pkce_s256(verifier).encode(), row["challenge"].encode()):
                    return _oauth_error("invalid_grant", "PKCE verification failed")
            elif verifier:
                return _oauth_error("invalid_grant", "code_verifier without code_challenge")
            return JSONResponse(store.issue(client_id, row["scope"], row["family"]), headers=NO_STORE)
        if grant == "refresh_token":
            out = store.rotate(str(form.get("refresh_token") or ""), client_id)
            if out is None:
                return _oauth_error("invalid_grant", "refresh token invalid, expired or revoked")
            return JSONResponse(out, headers=NO_STORE)
        return _oauth_error("unsupported_grant_type", "use authorization_code or refresh_token")

    async def mcp_endpoint(scope, receive, send):
        request = Request(scope)
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        if scheme.lower() != "bearer" or not store.access_ok(value.strip()):
            challenge = f'Bearer resource_metadata="{settings.resource_metadata_url}", scope="{SCOPE}"'
            if header:
                challenge += ', error="invalid_token"'
            resp = JSONResponse({"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": challenge})
            await resp(scope, receive, send)
            return
        await mcp_app(scope, receive, send)

    class _McpRoute(Route):
        def __init__(self) -> None:
            super().__init__("/mcp", endpoint=mcp_endpoint, methods=["GET", "POST", "DELETE"])
            self.app = mcp_endpoint  # raw ASGI, keep the MCP app's own request handling

    @asynccontextmanager
    async def lifespan(app):
        router = getattr(mcp_app, "router", None)
        if router is not None and getattr(router, "lifespan_context", None):
            async with router.lifespan_context(mcp_app):
                yield
        else:
            yield

    def health(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    routes = [
        Route("/.well-known/oauth-protected-resource", resource_metadata),
        Route("/.well-known/oauth-protected-resource/mcp", resource_metadata),
        Route("/.well-known/oauth-authorization-server", as_metadata),
        Route("/.well-known/oauth-authorization-server/mcp", as_metadata),
        Route("/authorize", authorize, methods=["GET", "POST"]),
        Route("/token", token, methods=["POST"]),
        Route("/healthz", health),
        _McpRoute(),
    ]
    return Starlette(routes=routes, lifespan=lifespan)


# --- CLI -------------------------------------------------------------------------------

def load_settings(secrets_path: Path, issuer: str) -> PublicSettings:
    from fermentd.config import load_secrets

    s = load_secrets(secrets_path)
    if s.mcp_public is None:
        raise SystemExit(f"no mcp_public block in {secrets_path}; run `fermentd-mcp-public init-client`")
    if s.web is None or not s.web.password_hash:
        raise SystemExit("the public MCP login needs a dashboard password (fermentd-ctl set-password)")
    p = s.mcp_public
    return PublicSettings(
        issuer=issuer.rstrip("/"), client_id=p.client_id, client_secret_sha256=p.client_secret_sha256,
        password_hash=s.web.password_hash,
        form_key=hashlib.sha256(b"fermentd-oauth-form\n" + p.client_secret_sha256.encode()).digest(),
        redirect_uris=tuple(p.redirect_uris), require_pkce=p.require_pkce,
    )


def init_client(secrets_path: Path) -> tuple[str, str]:
    """Generate a client id and secret, append the hashed secret to secrets.yaml, return both."""
    from fermentd.config import load_secrets

    if load_secrets(secrets_path).mcp_public is not None:
        raise SystemExit(f"{secrets_path} already has an mcp_public block; remove it to make a new client")
    client_id = "fermentd-" + _secrets.token_hex(8)
    secret = _secrets.token_urlsafe(32)
    text = secrets_path.read_text() if secrets_path.exists() else ""
    block = ("\n# Public read-only MCP (OAuth). Written by `fermentd-mcp-public init-client`.\n"
             f"mcp_public:\n  client_id: \"{client_id}\"\n  client_secret_sha256: \"{_sha(secret)}\"\n")
    secrets_path.write_text(text.rstrip("\n") + "\n" + block if text else block.lstrip("\n"))
    secrets_path.chmod(0o600)
    load_secrets(secrets_path)  # still valid
    return client_id, secret


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fermentd-mcp-public")
    parser.add_argument("command", nargs="?", choices=["serve", "init-client"], default="serve")
    parser.add_argument("--issuer", help="public https base URL, e.g. https://pi.tailnet.ts.net:8443")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--db", type=Path, default=Path("data/fermentd.db"))
    parser.add_argument("--oauth-db", type=Path, default=Path("data/mcp-oauth.db"))
    parser.add_argument("--secrets", type=Path, default=Path("config/secrets.yaml"))
    args = parser.parse_args(argv)
    if args.command == "init-client":
        cid, secret = init_client(args.secrets)
        print(f"client_id: {cid}\nclient_secret: {secret}\n(shown once; only its hash is stored)")
        return
    if not args.issuer or not args.issuer.startswith("https://"):
        raise SystemExit("--issuer must be the public https:// base URL")
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    from fermentd.mcp.server import build_server

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings(args.secrets, args.issuer)
    host = urlsplit(settings.issuer).netloc
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[host, host.rsplit(":", 1)[0], f"{args.host}:{args.port}"],
        allowed_origins=[settings.issuer],
    )
    server = build_server(args.db, read_only=True, host=args.host, port=args.port,
                          transport_security=security, log_level="WARNING", stateless_http=True)
    app = create_public_app(settings, OAuthStore(args.oauth_db), server.streamable_http_app())
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", proxy_headers=False)


if __name__ == "__main__":
    main()
