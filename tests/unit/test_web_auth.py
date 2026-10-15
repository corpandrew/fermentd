"""Dashboard login, CSRF checks, bind safety, and the set-password command."""

import io
import stat
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient
from tests.conftest import service_bundle

from fermentd.cli import _set_password
from fermentd.cli import main as ctl_main
from fermentd.config import load_secrets
from fermentd.web import auth
from fermentd.web.app import create_app

PASSWORD = "correct horse battery"
TOKEN = "t" * 32
FAST = {"n": 2**4, "r": 1, "p": 1}


def _form(key: str) -> dict:
    return {"name": "Ginger ale", "confirm": "yes", "idempotency_key": key}


def _client(tmp_path, *, password=True, token=False, base_url="http://testserver", **settings):
    service, _clock, _hw, _n = service_bundle(tmp_path)
    service.startup()
    cfg = auth.AuthSettings(
        password_hash=auth.hash_password(PASSWORD, **FAST) if password else None,
        token=TOKEN if token else None,
        **settings,
    )
    app = create_app(service.conn, service.clock, pump=service.tick, auth=cfg)
    return service, TestClient(app, base_url=base_url)


def _login(client, origin="http://testserver"):
    return client.post("/login", data={"password": PASSWORD, "next": "/vessels/vessel1"},
                       headers={"Origin": origin}, follow_redirects=False)


def test_hash_round_trip_and_rejects_bad_input():
    stored = auth.hash_password(PASSWORD)
    assert stored.startswith("scrypt$16384$8$1$") and PASSWORD not in stored
    assert auth.verify_password(PASSWORD, stored)
    assert not auth.verify_password("wrong", stored)
    assert not auth.verify_password(PASSWORD, "garbage")
    assert auth.hash_password(PASSWORD) != stored  # salted
    with pytest.raises(ValueError):
        auth.hash_password("")


def test_session_cookie_is_signed_and_expires():
    cfg = auth.AuthSettings(password_hash=auth.hash_password(PASSWORD, **FAST))
    value = auth.make_session(cfg, now=1000)
    assert auth.session_valid(cfg, value, now=1001)
    assert not auth.session_valid(cfg, value, now=1000 + auth.SESSION_TTL_S + 1)
    payload, sig = value.rsplit(".", 1)
    assert not auth.session_valid(cfg, payload + "." + sig[:-2] + "AA", now=1001)
    other = auth.AuthSettings(password_hash=auth.hash_password(PASSWORD, **FAST))
    assert not auth.session_valid(other, value, now=1001)  # new password logs everyone out


def test_without_auth_configured_writes_work_as_before(tmp_path):
    _service, client = _client(tmp_path, password=False)
    assert client.post("/vessels/vessel1/start", data=_form("a"), follow_redirects=False).status_code == 303
    assert "Log in" not in client.get("/").text
    assert client.get("/login", follow_redirects=False).status_code == 303


def test_writes_need_login_but_reads_stay_open(tmp_path):
    service, client = _client(tmp_path)
    assert client.get("/").status_code == 200
    assert client.get("/api/status").status_code == 200
    denied = client.post("/vessels/vessel1/start", data=_form("a"), follow_redirects=False)
    assert denied.status_code == 303 and denied.headers["location"].startswith("/login?next=")
    api = client.post("/vessels/vessel1/start", data=_form("a"), headers={"Accept": "application/json",
                      "Content-Type": "application/json"}, follow_redirects=False)
    assert api.status_code in {401, 422}
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 0
    assert "Log in" in client.get("/").text


def test_every_write_route_is_protected(tmp_path):
    _service, client = _client(tmp_path)
    for route in client.app.routes:
        methods = getattr(route, "methods", set()) or set()
        if "POST" in methods and route.path not in {"/login"}:
            path = route.path.replace("{", "").replace("}", "")
            r = client.post(path, headers={"Accept": "application/json"}, follow_redirects=False)
            assert r.status_code == 401, route.path


def test_login_sets_a_safe_cookie_and_allows_writes(tmp_path):
    service, client = _client(tmp_path)
    page = client.get("/login?next=/vessels/vessel1")
    assert page.status_code == 200 and 'type="password"' in page.text
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"] == "/vessels/vessel1"
    cookie = r.headers["set-cookie"]
    assert auth.COOKIE in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert "Secure" not in cookie  # plain http
    ok = client.post("/vessels/vessel1/start", data=_form("a"), headers={"Origin": "http://testserver"},
                     follow_redirects=False)
    assert ok.status_code == 303 and not ok.headers["location"].startswith("/login")
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 1
    assert "Log out" in client.get("/").text
    out = client.post("/logout", headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert out.status_code == 303
    client.cookies.clear()
    assert client.post("/alerts/1/ack", data={"confirm": "yes", "idempotency_key": "x"},
                       headers={"Origin": "http://testserver"}, follow_redirects=False).status_code == 303


def test_cookie_is_secure_over_https(tmp_path):
    _service, client = _client(tmp_path, base_url="https://fermentd.example.com")
    r = _login(client, origin="https://fermentd.example.com")
    assert r.status_code == 303 and "Secure" in r.headers["set-cookie"]


def test_wrong_password_and_throttle(tmp_path):
    _service, client = _client(tmp_path)
    for _ in range(5):
        r = client.post("/login", data={"password": "nope"}, headers={"Origin": "http://testserver"},
                        follow_redirects=False)
        assert "Wrong" in r.headers["location"] or "Wrong+password" in r.headers["location"]
        assert auth.COOKIE not in r.headers.get("set-cookie", "")
    blocked = _login(client)
    assert "Too+many" in blocked.headers["location"] and auth.COOKIE not in blocked.headers.get("set-cookie", "")


def test_open_redirect_is_refused(tmp_path):
    _service, client = _client(tmp_path)
    for bad in ("https://evil.example", "//evil.example", "/\\evil.example"):
        r = client.post("/login", data={"password": PASSWORD, "next": bad},
                        headers={"Origin": "http://testserver"}, follow_redirects=False)
        assert r.headers["location"] == "/"


def test_cross_site_posts_are_refused_even_when_logged_in(tmp_path):
    service, client = _client(tmp_path)
    _login(client)
    for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"},
                    {"Referer": "https://evil.example/page"}, {}):
        r = client.post("/vessels/vessel1/start", data=_form("x"), headers=headers, follow_redirects=False)
        assert r.status_code == 403, headers
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 0
    same = client.post("/vessels/vessel1/start", data=_form("y"),
                       headers={"Referer": "http://testserver/vessels/vessel1"}, follow_redirects=False)
    assert same.status_code == 303


def test_cross_site_login_is_refused(tmp_path):
    _service, client = _client(tmp_path)
    r = client.post("/login", data={"password": PASSWORD}, headers={"Origin": "https://evil.example"},
                    follow_redirects=False)
    assert r.status_code == 403


def test_csrf_applies_without_auth_too(tmp_path):
    _service, client = _client(tmp_path, password=False)
    r = client.post("/vessels/vessel1/start", data=_form("x"), headers={"Origin": "https://evil.example"},
                    follow_redirects=False)
    assert r.status_code == 403


def test_reverse_proxy_origin_is_accepted(tmp_path):
    """Caddy passes Host through and uvicorn applies X-Forwarded-Proto, so origin matches."""
    _service, client = _client(tmp_path, base_url="https://fermentd.example.com")
    _login(client, origin="https://fermentd.example.com")
    r = client.post("/vessels/vessel1/start", data=_form("p"), headers={"Origin": "https://fermentd.example.com"},
                    follow_redirects=False)
    assert r.status_code == 303 and not r.headers["location"].startswith("/login")


def test_configured_extra_origin_is_accepted(tmp_path):
    _service, client = _client(tmp_path, allowed_origins=("https://dash.example.com",))
    r = _login(client, origin="https://dash.example.com")
    assert r.status_code == 303 and auth.COOKIE in r.headers["set-cookie"]


def test_bearer_token_allows_writes_without_cookie_or_origin(tmp_path):
    service, client = _client(tmp_path, password=False, token=True)
    bad = client.post("/vessels/vessel1/start", data=_form("b"), headers={"Authorization": "Bearer nope",
                      "Accept": "application/json"}, follow_redirects=False)
    assert bad.status_code == 401
    good = client.post("/vessels/vessel1/start", data=_form("b"), headers={"Authorization": f"Bearer {TOKEN}"},
                       follow_redirects=False)
    assert good.status_code == 303
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 1
    assert "API tokens" in client.get("/login").text


@pytest.mark.parametrize("host,ok", [
    ("127.0.0.1", True), ("::1", True), ("localhost", True), ("100.72.0.5", True),
    ("fd7a:115c:a1e0::1", True), ("0.0.0.0", False), ("192.168.1.20", False), ("::", False),
])
def test_bind_safety(host, ok):
    assert (auth.check_bind(host, auth.AuthSettings(), insecure=False) is None) is ok
    assert auth.check_bind(host, auth.AuthSettings(), insecure=True) is None
    assert auth.check_bind(host, auth.AuthSettings(token=TOKEN), insecure=False) is None


def test_web_main_refuses_public_bind_without_auth(tmp_path, monkeypatch):
    from fermentd.web import app as web_app

    cfg = SimpleNamespace(
        web=SimpleNamespace(bind="0.0.0.0", port=8080, url=None, allowed_origins=[], allow_insecure=False),
        secrets=str(tmp_path / "secrets.yaml"),
        database=SimpleNamespace(path=str(tmp_path / "x.db")),
    )
    monkeypatch.setattr(web_app, "load_config", lambda _p: cfg)
    ran = []
    import uvicorn
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: ran.append(k))
    with pytest.raises(SystemExit, match="refusing"):
        web_app.main(["--config", "x"])
    web_app.main(["--config", "x", "--insecure-no-auth"])
    assert ran and ran[0]["proxy_headers"] is True and ran[0]["forwarded_allow_ips"] == "127.0.0.1"


def test_set_password_writes_hash_keeps_other_keys_and_is_private(tmp_path, capsys):
    path = tmp_path / "secrets.yaml"
    path.write_text(yaml.safe_dump({"tuya": {"mat": {"device_id": "d", "local_key": "k"}}}))
    args = SimpleNamespace(stdin=True, secrets=str(path), config="unused")
    assert _set_password(args, stdin=io.StringIO(PASSWORD + "\n")) == 0
    text = path.read_text()
    assert PASSWORD not in text and PASSWORD not in capsys.readouterr().out
    secrets = load_secrets(path)
    assert secrets.tuya["mat"].local_key == "k"
    assert auth.verify_password(PASSWORD, secrets.web.password_hash)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert _set_password(args, stdin=io.StringIO("short\n")) == 1


def test_set_password_cli_entry(tmp_path, monkeypatch):
    path = tmp_path / "secrets.yaml"
    monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    assert ctl_main(["set-password", "--stdin", "--secrets", str(path)]) == 0
    assert auth.verify_password(PASSWORD, load_secrets(path).web.password_hash)
