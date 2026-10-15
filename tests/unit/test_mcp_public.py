"""Public read-only MCP endpoint: OAuth 2.1 flow, PKCE, refresh rotation, expiry, read-only tools."""

import hashlib
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient
from tests.unit.test_mcp import TOOLS, WRITE_TOOLS, world  # noqa: F401  (fixture)

from fermentd.config import load_secrets
from fermentd.mcp import public as pub
from fermentd.mcp.server import build_server
from fermentd.web.auth import LoginThrottle, hash_password

ISSUER = "https://fermentd.example.ts.net"
REDIRECT = "https://vertexaisearch.cloud.google.com/oauth-redirect"
PASSWORD = "correct horse battery"
CLIENT_SECRET = "s3cret-" + "x" * 30
HOST = "fermentd.example.ts.net"


def _verifier():
    v = secrets.token_urlsafe(48)
    return v, pub.pkce_s256(v)


@pytest.fixture
def app(world, tmp_path):  # noqa: F811
    _s, _c, ro, _p = world
    settings = pub.PublicSettings(
        issuer=ISSUER, client_id="fermentd-test",
        client_secret_sha256=hashlib.sha256(CLIENT_SECRET.encode()).hexdigest(),
        password_hash=hash_password(PASSWORD, n=2**10), form_key=b"k" * 32)
    from mcp.server.transport_security import TransportSecuritySettings
    server = build_server(conn=ro, read_only=True, stateless_http=True, json_response=True,
                          transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    store = pub.OAuthStore(tmp_path / "oauth.db")
    a = pub.create_public_app(settings, store, server.streamable_http_app(), throttle=LoginThrottle(3, 300))
    with TestClient(a, base_url=f"https://{HOST}") as client:
        yield client, store, settings


def _authorize(client, challenge, password=PASSWORD, redirect=REDIRECT, state="st", client_id="fermentd-test"):
    params = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect, "state": state,
              "scope": "fermentd.read", "code_challenge": challenge, "code_challenge_method": "S256"}
    page = client.get("/authorize", params=params)
    assert page.status_code == 200 and "read-only" in page.text
    assert page.headers["x-frame-options"] == "DENY"
    txn = page.text.split('name="txn" value="')[1].split('"')[0]
    return client.post("/authorize", data={"txn": txn.replace("&quot;", '"'), "password": password,
                                           "action": "allow"}, follow_redirects=False)


def _code_flow(client):
    verifier, challenge = _verifier()
    r = _authorize(client, challenge)
    assert r.status_code == 303
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert r.headers["location"].startswith(REDIRECT + "?") and q["state"] == ["st"] and q["iss"] == [ISSUER]
    tok = client.post("/token", data={"grant_type": "authorization_code", "code": q["code"][0],
                                      "redirect_uri": REDIRECT, "code_verifier": verifier},
                      auth=("fermentd-test", CLIENT_SECRET))
    assert tok.status_code == 200, tok.text
    return tok.json(), q["code"][0], verifier


def _rpc(client, token, method, params=None):
    return client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
                       headers={"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"})


def test_metadata(app):
    client, _s, _ = app
    prm = client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert prm["resource"] == ISSUER + "/mcp" and prm["authorization_servers"] == [ISSUER]
    assert client.get("/.well-known/oauth-protected-resource").json() == prm
    asm = client.get("/.well-known/oauth-authorization-server").json()
    assert asm["issuer"] == ISSUER and asm["code_challenge_methods_supported"] == ["S256"]
    assert asm["token_endpoint"] == ISSUER + "/token"


def test_unauthenticated_mcp_gets_401_with_resource_metadata(app):
    client, _s, _ = app
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    assert f'resource_metadata="{ISSUER}/.well-known/oauth-protected-resource/mcp"' in r.headers["www-authenticate"]
    r = _rpc(client, "bogus", "tools/list")
    assert r.status_code == 401 and 'error="invalid_token"' in r.headers["www-authenticate"]


def test_full_flow_lists_only_read_tools_and_writes_are_unreachable(app):
    client, _s, _ = app
    tokens, _code, _v = _code_flow(client)
    assert tokens["token_type"] == "Bearer" and tokens["expires_in"] == pub.ACCESS_TTL_S
    init = _rpc(client, tokens["access_token"], "initialize",
                {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert init.status_code == 200, init.text
    names = {t["name"] for t in _rpc(client, tokens["access_token"], "tools/list").json()["result"]["tools"]}
    assert names == TOOLS - WRITE_TOOLS
    ok = _rpc(client, tokens["access_token"], "tools/call", {"name": "list_vessels", "arguments": {}}).json()
    assert ok["result"].get("isError") is not True
    for name in WRITE_TOOLS:
        res = _rpc(client, tokens["access_token"], "tools/call",
                   {"name": name, "arguments": {"batch_id": 1, "text": "x"}}).json()
        assert res.get("error") or res["result"]["isError"] is True, name


def test_read_only_server_never_registers_write_tools(world):  # noqa: F811
    import asyncio
    _s, _c, ro, _p = world
    tools = asyncio.run(build_server(conn=ro, read_only=True).list_tools())
    assert {t.name for t in tools} == TOOLS - WRITE_TOOLS
    assert all(t.annotations.readOnlyHint for t in tools)


def test_code_is_single_use_and_reuse_revokes_tokens(app):
    client, _s, _ = app
    tokens, code, verifier = _code_flow(client)
    again = client.post("/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                        "code_verifier": verifier}, auth=("fermentd-test", CLIENT_SECRET))
    assert again.status_code == 400 and again.json()["error"] == "invalid_grant"
    assert _rpc(client, tokens["access_token"], "tools/list").status_code == 401


def test_pkce_wrong_verifier_and_missing_challenge(app):
    client, _s, _ = app
    _v, challenge = _verifier()
    r = _authorize(client, challenge)
    code = parse_qs(urlsplit(r.headers["location"]).query)["code"][0]
    bad = client.post("/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                      "code_verifier": _verifier()[0]}, auth=("fermentd-test", CLIENT_SECRET))
    assert bad.json()["error"] == "invalid_grant"
    no_pkce = client.get("/authorize", params={"response_type": "code", "client_id": "fermentd-test",
                                               "redirect_uri": REDIRECT}, follow_redirects=False)
    assert no_pkce.status_code == 303 and "error=invalid_request" in no_pkce.headers["location"]
    plain = client.get("/authorize", params={"response_type": "code", "client_id": "fermentd-test",
                                             "redirect_uri": REDIRECT, "code_challenge": "abc",
                                             "code_challenge_method": "plain"}, follow_redirects=False)
    assert "error=invalid_request" in plain.headers["location"]


def test_client_auth_required_basic_or_post(app):
    client, _s, _ = app
    verifier, challenge = _verifier()
    code = parse_qs(urlsplit(_authorize(client, challenge).headers["location"]).query)["code"][0]
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "code_verifier": verifier}
    assert client.post("/token", data=data, auth=("fermentd-test", "wrong")).status_code == 401
    assert client.post("/token", data=data).status_code == 401
    ok = client.post("/token", data={**data, "client_id": "fermentd-test", "client_secret": CLIENT_SECRET})
    assert ok.status_code == 200


def test_refresh_rotates_and_reuse_revokes_chain(app):
    client, _s, _ = app
    tokens, _c, _v = _code_flow(client)
    auth = ("fermentd-test", CLIENT_SECRET)
    new = client.post("/token", data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
                      auth=auth).json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert _rpc(client, tokens["access_token"], "tools/list").status_code == 401  # old access revoked
    assert _rpc(client, new["access_token"], "tools/list").status_code == 200
    reuse = client.post("/token", data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
                        auth=auth)
    assert reuse.json()["error"] == "invalid_grant"
    assert _rpc(client, new["access_token"], "tools/list").status_code == 401  # whole chain revoked


def test_access_token_expires(app):
    _client, store, _ = app
    out = store.issue("fermentd-test", pub.SCOPE, "fam")
    assert store.access_ok(out["access_token"])
    assert not store.access_ok(out["access_token"], now=time.time() + pub.ACCESS_TTL_S + 1)
    assert store.rotate(out["refresh_token"], "fermentd-test", now=time.time() + pub.REFRESH_TTL_S + 1) is None


def test_wrong_password_is_rate_limited(app):
    client, _s, _ = app
    _v, challenge = _verifier()
    for _ in range(3):
        assert _authorize(client, challenge, password="nope").status_code == 401
    assert _authorize(client, challenge).status_code == 429


def test_redirect_allowlist(app):
    client, _s, settings = app
    assert settings.redirect_ok(REDIRECT)
    assert settings.redirect_ok("https://gemini.google.com/oauth/callback")
    for bad in ("https://evil.com/cb", "http://gemini.google.com/cb", "https://google.com.evil.com/cb",
                "https://user@gemini.google.com/cb", None):
        assert not settings.redirect_ok(bad)
    r = client.get("/authorize", params={"response_type": "code", "client_id": "fermentd-test",
                                         "redirect_uri": "https://evil.com/cb", "code_challenge": "x" * 43,
                                         "code_challenge_method": "S256"}, follow_redirects=False)
    assert r.status_code == 400  # never redirects to an unknown URI
    assert client.get("/authorize", params={"client_id": "other", "redirect_uri": REDIRECT}).status_code == 400


def test_tampered_form_rejected(app):
    client, _s, _ = app
    r = client.post("/authorize", data={"txn": "abc.def", "password": PASSWORD, "action": "allow"})
    assert r.status_code == 400


def test_init_client_appends_hashed_secret(tmp_path):
    path = tmp_path / "secrets.yaml"
    path.write_text("# keep me\nmcp:\n  token: \"" + "t" * 30 + "\"\n")
    cid, secret = pub.init_client(path)
    text = path.read_text()
    assert "# keep me" in text and secret not in text
    s = load_secrets(path)
    assert s.mcp_public.client_id == cid
    assert s.mcp_public.client_secret_sha256 == hashlib.sha256(secret.encode()).hexdigest()
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    with pytest.raises(SystemExit):
        pub.init_client(path)



def test_metadata_advertises_registration_and_public_clients(app):
    client, _s, _ = app
    asm = client.get("/.well-known/oauth-authorization-server").json()
    assert asm["registration_endpoint"] == ISSUER + "/register"
    assert "none" in asm["token_endpoint_auth_methods_supported"]


def test_dynamic_registration_public_client_full_flow(app):
    client, _s, _ = app
    reg = client.post("/register", json={"redirect_uris": [REDIRECT], "client_name": "Gemini",
                                          "token_endpoint_auth_method": "none"})
    assert reg.status_code == 201, reg.text
    cid = reg.json()["client_id"]
    assert "client_secret" not in reg.json()
    verifier, challenge = _verifier()
    r = _authorize(client, challenge, client_id=cid)
    code = parse_qs(urlsplit(r.headers["location"]).query)["code"][0]
    tok = client.post("/token", data={"grant_type": "authorization_code", "code": code, "client_id": cid,
                                      "redirect_uri": REDIRECT, "code_verifier": verifier})
    assert tok.status_code == 200, tok.text
    assert _rpc(client, tok.json()["access_token"], "tools/list").status_code == 200
    new = client.post("/token", data={"grant_type": "refresh_token", "client_id": cid,
                                      "refresh_token": tok.json()["refresh_token"]})
    assert new.status_code == 200


def test_dynamic_registration_rejects_foreign_redirects(app):
    client, _s, _ = app
    for body in ({"redirect_uris": ["https://evil.example/cb"]}, {"redirect_uris": []}, {}, ["x"]):
        assert client.post("/register", json=body).status_code == 400
    cid = client.post("/register", json={"redirect_uris": [REDIRECT]}).json()["client_id"]
    other = "https://vertexaisearch.cloud.google.com/static/oauth/oauth.html"
    page = client.get("/authorize", params={"response_type": "code", "client_id": cid, "redirect_uri": other,
                                            "code_challenge": "x" * 43, "code_challenge_method": "S256"})
    assert page.status_code == 400


def test_preregistered_client_without_secret_needs_pkce_and_wrong_secret_fails(app):
    client, _s, _ = app
    verifier, challenge = _verifier()
    code = parse_qs(urlsplit(_authorize(client, challenge).headers["location"]).query)["code"][0]
    data = {"grant_type": "authorization_code", "code": code, "client_id": "fermentd-test",
            "redirect_uri": REDIRECT, "code_verifier": verifier}
    assert client.post("/token", data={**data, "client_secret": "nope"}).status_code == 401
    assert client.post("/token", data=data).status_code == 200


def test_registration_requires_pkce_for_public_client(app):
    client, _s, _ = app
    cid = client.post("/register", json={"redirect_uris": [REDIRECT],
                                         "token_endpoint_auth_method": "none"}).json()["client_id"]
    r = client.get("/authorize", params={"response_type": "code", "client_id": cid, "redirect_uri": REDIRECT},
                   follow_redirects=False)
    assert r.status_code == 303 and "error=invalid_request" in r.headers["location"]
