"""Status board. It inserts commands and does not touch hardware. See web/auth.py for the login."""

from __future__ import annotations

import argparse
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fermentd.clock import Clock, SystemClock
from fermentd.config import load_config, load_secrets
from fermentd.control.commands import database_now, enqueue
from fermentd.db.connection import connect
from fermentd.db.migrate import migrate
from fermentd.control import cutoff, notes, tweaks
from fermentd.timefmt import SITE_ZONE, format_local
from fermentd.web.auth import (
    COOKIE,
    LOGIN_PATH,
    AuthMiddleware,
    AuthSettings,
    LoginThrottle,
    check_bind,
    is_authenticated,
    safe_next,
    set_session_cookie,
    verify_password,
)
from fermentd.web.chart import render_temperature_chart
from fermentd.web.markdown import load_guide
from fermentd.web.scale_view import scale_panel
from fermentd.web.status import (
    batch_detail,
    heater_duty,
    batch_history,
    batch_temperature_history,
    gravity_summary,
    profile_catalog,
    profile_choices,
    reminder_when,
    snapshot,
    stage_label,
    target_control,
    temperature_history,
)

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
TEMPLATES.env.globals["stage_label"] = stage_label
TEMPLATES.env.globals["reminder_when"] = reminder_when
TEMPLATES.env.globals["logged_in"] = is_authenticated
TEMPLATES.env.globals["auth_enabled"] = lambda request: request.app.state.auth.enabled
STATIC = Path(__file__).parent / "static"
_NO_STORE = {"Cache-Control": "no-store"}


def create_app(
    conn,
    clock: Clock | None = None,
    pump: Callable[[], None] | None = None,
    auth: AuthSettings | None = None,
) -> FastAPI:
    app = FastAPI(title="fermentd")
    app.state.auth = auth or AuthSettings()
    app.state.login_throttle = LoginThrottle()
    app.add_middleware(AuthMiddleware)
    app.state.conn = conn
    app.state.clock = clock or SystemClock()
    app.state.pump = pump
    templates = TEMPLATES

    @app.get("/api/commands/{command_id}")
    def command_status(command_id: int) -> JSONResponse:
        row = app.state.conn.execute(
            "SELECT status, result_json FROM COMMAND WHERE id = ? AND actor = 'web'", (command_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="command not found")
        outcome = {"status": row["status"], "result_json": row["result_json"]}
        body = {"status": row["status"]}
        if row["status"] not in {"done", "pending"}:
            body["message"] = _outcome_message(outcome)
        return JSONResponse(body, headers=_NO_STORE)

    @app.get(LOGIN_PATH, response_class=HTMLResponse)
    def login_page(request: Request, next: str = "/", error: str | None = None):
        if not app.state.auth.enabled:
            return RedirectResponse(safe_next(next), status_code=303)
        context = _page(app.state.conn)
        context.update({"next": safe_next(next), "error": error,
                        "has_password": bool(app.state.auth.password_hash)})
        return templates.TemplateResponse(request, "login.html", context, headers=_NO_STORE)

    @app.post(LOGIN_PATH)
    async def login(request: Request, password: str = Form(""), next: str = Form("/")):
        settings: AuthSettings = app.state.auth
        target = safe_next(next)
        if not settings.enabled:
            return RedirectResponse(target, status_code=303)
        client = request.client.host if request.client else "?"
        throttle: LoginThrottle = app.state.login_throttle
        if throttle.blocked(client):
            return RedirectResponse(
                f"{LOGIN_PATH}?{urlencode({'next': target, 'error': 'Too many tries. Wait a few minutes.'})}",
                status_code=303,
            )
        ok = bool(settings.password_hash) and await run_in_threadpool(
            verify_password, password, settings.password_hash
        )
        if not ok:
            throttle.fail(client)
            return RedirectResponse(
                f"{LOGIN_PATH}?{urlencode({'next': target, 'error': 'Wrong password.'})}", status_code=303
            )
        throttle.clear(client)
        response = RedirectResponse(target, status_code=303)
        set_session_cookie(response, request, settings)
        return response

    @app.post("/logout")
    def logout(request: Request):
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="lax",
                               secure=request.url.scheme == "https")
        return response

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/status")
    def api_status() -> JSONResponse:
        return JSONResponse(snapshot(app.state.conn), headers=_NO_STORE)

    @app.get("/api/vessels/{vessel_id}/chart", response_class=HTMLResponse)
    def vessel_chart(vessel_id: str) -> HTMLResponse:
        svg = _chart(app.state.conn, vessel_id)
        if svg is None:
            raise HTTPException(status_code=404, detail="vessel not found")
        return HTMLResponse(svg, headers=_NO_STORE)

    @app.get("/partials/alerts", response_class=HTMLResponse)
    def alerts_partial(request: Request) -> HTMLResponse:
        status = snapshot(app.state.conn)
        return templates.TemplateResponse(
            request,
            "_alerts.html",
            {"alerts": status["alerts"], "token": uuid.uuid4().hex},
            headers=_NO_STORE,
        )

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request, error: str | None = None):
        context = _board(app.state.conn)
        context["error"] = error
        return templates.TemplateResponse(request, "overview.html", context)

    @app.get("/vessels/{vessel_id}", response_class=HTMLResponse)
    def vessel(request: Request, vessel_id: str, error: str | None = None, show: str = "all"):
        context = _board(app.state.conn)
        match = next((item for item in context["status"]["vessels"] if item["id"] == vessel_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="vessel not found")
        context["vessel"] = match
        context["error"] = error
        if match.get("batch"):
            context["target_control"] = target_control(app.state.conn, match)
            context["gravity"] = gravity_summary(app.state.conn, match["batch"]["id"])
        context["duty"] = heater_duty(app.state.conn, vessel_id, match["batch"]["id"] if match.get("batch") else None)
        zone_row = app.state.conn.execute("SELECT temp_zone_id FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
        context["cutoff"] = cutoff.status(app.state.conn, zone_row["temp_zone_id"] if zone_row else None,
                                          app.state.clock.now())
        if match.get("batch"):
            context["extras"] = batch_extras(app.state.conn, match["batch"]["id"])
            context["timeline"] = batch_timeline(app.state.conn, match["batch"]["id"], show)
        context["scale"] = scale_panel(
            app.state.conn, vessel_id, match["batch"]["id"] if match.get("batch") else None
        )
        return templates.TemplateResponse(request, "vessel.html", context)

    @app.post("/vessels/{vessel_id}/start")
    def start_batch(
        vessel_id: str,
        name: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
        profile_id: str = Form("soda_ginger_ale"),
        batch_size_gal: str = Form("1"),
        start_from: str = Form(""),
        start_stage: str = Form(""),
    ):
        _require_confirm(confirm)
        params = {
            "vessel_id": vessel_id,
            "name": name.strip() or _default_batch_name(app.state.conn, profile_id),
            "profile_id": profile_id,
            "batch_size_gal": batch_size_gal,
        }
        if start_stage == "prep":
            params["stage"] = "prep"
        kind, _, ref = start_from.partition(":")
        if kind == "v" and ref.isdigit():
            params["variant_id"] = int(ref)
        elif kind == "b" and ref.isdigit():
            params["copy_tweaks_from_batch_id"] = int(ref)
        outcome = _submit(app, "start_batch", params, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/alerts/{alert_id}/ack")
    def ack(alert_id: int, confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "ack_alert", {"alert_id": alert_id}, idempotency_key)
        return _redirect("/", outcome)

    @app.post("/reminders/{reminder_id}/complete")
    def complete(
        reminder_id: int,
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
        vessel_id: str = Form(...),
    ):
        _require_confirm(confirm)
        outcome = _submit(app, "complete_reminder", {"reminder_id": reminder_id}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/stage")
    def set_stage(
        vessel_id: str,
        stage: str = Form(...),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        outcome = _submit(app, "set_stage", {"vessel_id": vessel_id, "stage": stage}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/target")
    def set_target(
        vessel_id: str,
        target_f: float = Form(...),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        outcome = _submit(app, "set_target_temp", {"vessel_id": vessel_id, "target_f": target_f}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/gravity")
    def add_gravity(
        vessel_id: str,
        sg: str = Form(...),
        sample_temp_f: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        params = {"vessel_id": vessel_id, "sg": sg.strip(), "sample_temp_f": sample_temp_f.strip() or None}
        outcome = _submit(app, "add_gravity", params, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/scale/tare")
    def scale_tare(vessel_id: str, confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "scale_tare", {"vessel_id": vessel_id}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/scale/calibrate")
    def scale_calibrate(
        vessel_id: str,
        grams: str = Form(...),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        outcome = _submit(app, "scale_calibrate", {"vessel_id": vessel_id, "grams": grams.strip()}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.post("/vessels/{vessel_id}/end")
    def end_batch(
        vessel_id: str,
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        outcome = _submit(app, "end_batch", {"vessel_id": vessel_id}, idempotency_key)
        return _redirect(f"/vessels/{vessel_id}", outcome)

    @app.get("/history", response_class=HTMLResponse)
    def history(request: Request, error: str | None = None):
        context = _page(app.state.conn)
        context["batches"] = batch_history(app.state.conn)
        context["error"] = error
        return templates.TemplateResponse(request, "history.html", context)

    @app.get("/history/{batch_id}", response_class=HTMLResponse)
    def history_detail(request: Request, batch_id: int, error: str | None = None, delete: int = 0, show: str = "all"):
        batch = batch_detail(app.state.conn, batch_id)
        if batch is None or batch["ended_at"] is None:
            raise HTTPException(status_code=404, detail="batch not found")
        context = _page(app.state.conn)
        context["batch"] = batch
        context["chart"] = render_temperature_chart(
            batch_temperature_history(app.state.conn, batch_id),
            target_f=batch["target_temp_f"],
            hysteresis_f=None,
        )
        context["confirm_delete"] = bool(delete)
        context["error"] = error
        context["extras"] = batch_extras(app.state.conn, batch_id)
        context["timeline"] = batch_timeline(app.state.conn, batch_id, show)
        return templates.TemplateResponse(request, "history_detail.html", context)

    def _batch_page(batch_id: int) -> str:
        row = app.state.conn.execute("SELECT vessel_id, ended_at FROM BATCH WHERE id = ?", (batch_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="batch not found")
        return f"/history/{batch_id}" if row["ended_at"] else f"/vessels/{row['vessel_id']}"

    @app.post("/batches/{batch_id}/notes")
    async def add_note(
        batch_id: int,
        text: str = Form(""),
        photo: UploadFile | None = File(None),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        target = _batch_page(batch_id) + "#timeline"
        params = {"batch_id": batch_id, "text": text}
        data = await photo.read() if photo is not None and photo.filename else b""
        if data:
            done = app.state.conn.execute(
                "SELECT 1 FROM COMMAND WHERE idempotency_key = ? AND actor = 'web'", (idempotency_key,)
            ).fetchone()
            if done is None:  # a resubmitted form must not save a second copy of the photo
                try:
                    params["photo"], params["thumb"] = await run_in_threadpool(
                        notes.save_photo, notes.photo_dir(app.state.conn), batch_id, data)
                except notes.PhotoRejected as exc:
                    return RedirectResponse(f"{target.split('#')[0]}?error={quote(str(exc))}#timeline", status_code=303)
        outcome = await run_in_threadpool(_submit, app, "add_note", params, idempotency_key)
        return _redirect(target, outcome)

    @app.get("/photos/{name}")
    def photo(name: str):
        if not notes.PHOTO_NAME.match(name):
            raise HTTPException(status_code=404, detail="photo not found")
        path = notes.photo_dir(app.state.conn) / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="photo not found")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=86400"})

    @app.post("/batches/{batch_id}/tweaks")
    def add_tweak(
        batch_id: int,
        kind: str = Form(...),
        ingredient_id: str = Form(""),
        item: str = Form(""),
        to_amount: str = Form(""),
        note: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        params = {"batch_id": batch_id, "kind": kind, "ingredient_id": ingredient_id, "item": item,
                  "to_amount": to_amount, "note": note}
        outcome = _submit(app, "add_tweak", params, idempotency_key)
        return _redirect(_batch_page(batch_id) + "#recipe", outcome)

    @app.post("/batches/{batch_id}/tweaks/{tweak_id}/remove")
    def remove_tweak(batch_id: int, tweak_id: int, confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "remove_tweak", {"batch_id": batch_id, "tweak_id": tweak_id}, idempotency_key)
        return _redirect(_batch_page(batch_id) + "#recipe", outcome)

    @app.post("/batches/{batch_id}/variant")
    def save_variant(batch_id: int, name: str = Form(""), confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "save_variant", {"batch_id": batch_id, "name": name}, idempotency_key)
        return _redirect(_batch_page(batch_id) + "#recipe", outcome)

    @app.post("/batches/{batch_id}/tastings")
    def log_tasting(
        batch_id: int,
        rating: str = Form(...),
        tasted_at: str = Form(""),
        carbonation: str = Form(""),
        sweetness: str = Form(""),
        dryness: str = Form(""),
        flavor: str = Form(""),
        notes: str = Form(""),
        make_again: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        params = {"batch_id": batch_id, "rating": rating, "tasted_at": tasted_at, "carbonation": carbonation,
                  "sweetness": sweetness, "dryness": dryness, "flavor": flavor, "notes": notes,
                  "make_again": make_again}
        outcome = _submit(app, "log_tasting", params, idempotency_key)
        return _redirect(_batch_page(batch_id) + "#tasting", outcome)

    @app.get("/tastings", response_class=HTMLResponse)
    def tasting_ranking(request: Request, type: str | None = None):
        context = _page(app.state.conn)
        rows = tweaks.ranking(app.state.conn, drink_type=type or None)
        for r in rows:
            r["stars"] = stars(r["avg_rating"])
            r["url"] = f"/history/{r['batch_id']}" if r["ended_at"] else None
        context["ranked"] = rows
        context["types"] = sorted({r["drink_type"] for r in tweaks.ranking(app.state.conn) if r["drink_type"]})
        context["type"] = type
        return templates.TemplateResponse(request, "tastings.html", context)

    @app.post("/history/{batch_id}/delete")
    def delete_batch(batch_id: int, confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "delete_batch", {"batch_id": batch_id}, idempotency_key)
        if outcome["status"] in {"done", "pending"}:
            return _redirect("/history", outcome)
        return _redirect(f"/history/{batch_id}", outcome)

    @app.get("/vessels", response_class=HTMLResponse)
    def vessels_page(request: Request, error: str | None = None):
        context = _board(app.state.conn)
        context["zones"] = [dict(row) for row in app.state.conn.execute("SELECT * FROM TEMP_ZONE ORDER BY id")]
        context["vessel_types"] = ["jug", "carboy", "bucket", "jar", "bottle_group"]
        context["error"] = error
        return templates.TemplateResponse(request, "vessels.html", context)

    @app.post("/vessels")
    def add_vessel(
        name: str = Form(...),
        vessel_type: str = Form(...),
        temp_zone: str = Form(""),
        probe_rom_id: str = Form(""),
        capacity_l: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        params = {
            "name": name,
            "vessel_type": vessel_type,
            "temp_zone": temp_zone,
            "probe_rom_id": probe_rom_id,
            "capacity_l": capacity_l,
        }
        outcome = _submit(app, "add_vessel", params, idempotency_key)
        return _redirect("/vessels", outcome)

    @app.post("/vessels/{vessel_id}/edit")
    def edit_vessel(
        vessel_id: str,
        name: str = Form(""),
        vessel_type: str = Form("jug"),
        temp_zone: str = Form(""),
        probe_rom_id: str = Form(""),
        capacity_l: str = Form(""),
        remove: str = Form(""),
        confirm: str = Form(...),
        idempotency_key: str = Form(...),
    ):
        _require_confirm(confirm)
        params = {
            "vessel_id": vessel_id,
            "name": name,
            "vessel_type": vessel_type,
            "temp_zone": temp_zone,
            "probe_rom_id": probe_rom_id,
            "capacity_l": capacity_l,
            "remove": remove == "yes",
        }
        outcome = _submit(app, "update_vessel", params, idempotency_key)
        return _redirect("/vessels", outcome)

    @app.post("/zones/{zone_id}/rename")
    def rename_zone(zone_id: str, name: str = Form(...), confirm: str = Form(...), idempotency_key: str = Form(...)):
        _require_confirm(confirm)
        outcome = _submit(app, "rename_zone", {"zone": zone_id, "name": name}, idempotency_key)
        return _redirect("/vessels", outcome)

    @app.get("/profiles", response_class=HTMLResponse)
    def profiles_page(request: Request, error: str | None = None):
        context = _page(app.state.conn)
        context["profiles"] = profile_catalog(app.state.conn)
        context["error"] = error
        return templates.TemplateResponse(request, "profiles.html", context)

    @app.get("/profiles/{profile_id}", response_class=HTMLResponse)
    def profile_detail(request: Request, profile_id: str, error: str | None = None, edit: int = 0):
        profile = next((p for p in profile_catalog(app.state.conn) if p["id"] == profile_id), None)
        if profile is None:
            raise HTTPException(status_code=404, detail="profile not found")
        context = _page(app.state.conn)
        context["profile"] = profile
        context["p"] = profile["definition"]
        context["edit"] = bool(edit)
        context["guide"] = None if edit else load_guide(profile["definition"].get("recipe"))
        context["error"] = error
        return templates.TemplateResponse(request, "profile_detail.html", context)

    @app.get("/profiles/{profile_id}/guide", response_class=HTMLResponse)
    def profile_guide(request: Request, profile_id: str, size: str = "1"):
        profile = next((p for p in profile_catalog(app.state.conn) if p["id"] == profile_id), None)
        if profile is None:
            raise HTTPException(status_code=404, detail="profile not found")
        guide = load_guide(profile["definition"].get("recipe"), size=size)
        if guide is None:
            raise HTTPException(status_code=404, detail="this profile has no guide")
        context = _page(app.state.conn)
        context["profile"] = profile
        context["guide"] = guide
        context["batch_name"] = request.query_params.get("batch")
        return templates.TemplateResponse(request, "guide.html", context)

    @app.post("/profiles/{profile_id}")
    async def save_profile(request: Request, profile_id: str):
        form = await request.form()
        _require_confirm(str(form.get("confirm", "")))
        key = str(form.get("idempotency_key") or "")
        if not key:
            raise HTTPException(status_code=400, detail="idempotency_key is required")
        skip = {"confirm", "idempotency_key"}
        edits = {k: str(v) for k, v in form.items() if k not in skip}
        outcome = await run_in_threadpool(_submit, app, "save_profile", {"profile_id": profile_id, "edits": edits}, key)
        if outcome["status"] == "done":
            saved = json.loads(outcome["result_json"])["profile_id"]
            return RedirectResponse(f"/profiles/{saved}", status_code=303)
        if outcome["status"] == "pending":
            return _redirect("/profiles", outcome)
        return _redirect(f"/profiles/{profile_id}?edit=1", outcome)

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    return app


def _board(conn) -> dict:
    status = snapshot(conn)
    charts = {}
    for vessel in status["vessels"]:
        history = temperature_history(conn, vessel["id"])
        vessel["chart_ready"] = any(
            point["vessel_temp_f"] is not None or point["ambient_temp_f"] is not None for point in history
        )
        charts[vessel["id"]] = render_temperature_chart(
            history,
            target_f=vessel["target_f"] if vessel.get("batch") else None,
            hysteresis_f=vessel["hysteresis_f"],
        )
    catalog = profile_catalog(conn)
    for vessel in status["vessels"]:
        vessel["profile_choices"] = profile_choices(catalog, vessel)
        available = [choice for choice in vessel["profile_choices"] if choice["available"]]
        preferred = next((choice for choice in available if choice["id"] == "soda_ginger_ale"), None)
        vessel["default_choice"] = preferred or (available[0] if available else None)
        vessel["guide_url"] = None
        batch = vessel.get("batch")
        if batch:
            entry = next((item for item in catalog if item["id"] == batch["profile_id"]), None)
            if entry is not None and entry["definition"].get("recipe"):
                query = {"batch": batch["name"]}
                row = conn.execute(
                    "SELECT volume_l FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL", (vessel["id"],)
                ).fetchone()
                if row is not None and row["volume_l"] is not None and row["volume_l"] < 2.5:
                    query["size"] = "0.5"
                vessel["guide_url"] = f"/profiles/{batch['profile_id']}/guide?{urlencode(query)}"
    return {
        "status": status,
        "alerts": status["alerts"],
        "charts": charts,
        "as_of_label": status["as_of_label"],
        "token": uuid.uuid4().hex,
        "start_sources": start_sources(conn),
    }


def stars(value: float | None) -> str:
    if value is None:
        return ""
    full = int(round(value))
    return "★" * full + "☆" * (5 - full)


def start_sources(conn) -> list[dict]:
    """Choices for 'Start from' on the new-batch form: saved versions and batches that had changes."""
    out = [{"value": f"v:{v['variant_id']}", "label": f"My version: {v['name']}", "profile_id": v["profile_id"]}
           for v in tweaks.variants(conn)]
    for row in conn.execute(
        "SELECT DISTINCT BATCH.id, BATCH.name, BATCH.profile_id FROM BATCH JOIN BATCH_TWEAK ON BATCH_TWEAK.batch_id = BATCH.id "
        "WHERE BATCH_TWEAK.removed_at IS NULL ORDER BY BATCH.id DESC LIMIT 20"
    ):
        out.append({"value": f"b:{row['id']}", "label": f"Same changes as {row['name']}", "profile_id": row["profile_id"]})
    return out


def batch_timeline(conn, batch_id: int, show: str = "all") -> dict:
    only = show == "notes"
    items = notes.timeline(conn, batch_id, only_notes=only)
    icons = {"note": "✎", "start_batch": "▶", "end_batch": "■", "set_stage": "→", "set_target_temp": "°",
             "complete_reminder": "✓", "add_gravity": "⚖", "add_tweak": "±", "remove_tweak": "↺",
             "log_tasting": "★", "save_variant": "⎘"}
    for item in items:
        item["when"] = format_local(item["ts"])
        item["icon"] = icons.get(item["kind"], "•")
    return {"batch_id": batch_id, "show": "notes" if only else "all", "items": items}


def batch_extras(conn, batch_id: int) -> dict | None:
    from datetime import UTC, datetime

    batch = conn.execute("SELECT * FROM BATCH WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        return None
    profile = json.loads(batch["profile_snapshot_json"] or "{}")
    category = profile.get("category")
    view = tweaks.recipe_view(conn, batch)
    sliders = tweaks.sliders_for(category)
    entries = []
    for t in tweaks.tastings(conn, batch_id):
        entries.append({
            "id": t["id"], "date": format_local(t["tasted_at"]), "rating": t["rating"], "stars": stars(t["rating"]),
            "notes": t["notes"], "make_again": t["make_again"],
            "scores": [{"label": sl["label"], "value": t[sl["key"]], "low": sl["low"], "high": sl["high"]}
                       for sl in sliders if t[sl["key"]] is not None],
        })
    avg = round(sum(e["rating"] for e in entries) / len(entries), 1) if entries else None
    return {
        "batch_id": batch_id, "ended": batch["ended_at"] is not None, "category": category,
        "recipe": view, "sliders": sliders, "tastings": entries, "avg": avg, "avg_stars": stars(avg),
        "today": datetime.now(UTC).astimezone(SITE_ZONE).date().isoformat(),
    }


def _default_batch_name(conn, profile_id: str) -> str:
    choice = next((item for item in profile_catalog(conn) if item["id"] == profile_id), None)
    if choice is None:
        return "Batch"
    return f"{choice['name']} #{choice['batch_count'] + 1}"


def _page(conn) -> dict:
    status = snapshot(conn)
    return {"alerts": status["alerts"], "as_of_label": status["as_of_label"], "token": uuid.uuid4().hex}


def _chart(conn, vessel_id: str) -> str | None:
    row = conn.execute("SELECT temp_zone_id FROM VESSEL WHERE id = ? AND enabled = 1", (vessel_id,)).fetchone()
    if row is None:
        return None
    target = None
    hysteresis = None
    if row["temp_zone_id"]:
        zone = conn.execute(
            "SELECT target_f, hysteresis_f FROM TEMP_ZONE WHERE id = ?",
            (row["temp_zone_id"],),
        ).fetchone()
        running = conn.execute(
            "SELECT 1 FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL", (vessel_id,)
        ).fetchone()
        if zone is not None and running is not None:
            target = zone["target_f"]
            hysteresis = zone["hysteresis_f"]
    return render_temperature_chart(
        temperature_history(conn, vessel_id),
        target_f=target,
        hysteresis_f=hysteresis,
    )


_ERROR_TEXT = {
    "NOT_FOUND": "That item is no longer there.",
}


def _redirect(location: str, outcome: dict) -> RedirectResponse:
    joiner = "&" if "?" in location else "?"
    if outcome["status"] == "done":
        return RedirectResponse(location, status_code=303)
    if outcome["status"] == "pending" and outcome.get("command_id") is not None:
        query = urlencode({"notice": "Saved, applying…", "pending": outcome["command_id"]})
        return RedirectResponse(f"{location}{joiner}{query}", status_code=303)
    message = _outcome_message(outcome)
    return RedirectResponse(f"{location}{joiner}{urlencode({'error': message})}", status_code=303)


def _outcome_message(outcome: dict) -> str:
    if outcome.get("status") == "expired":
        return "The controller did not pick that up in time. Check that fermentd-control is running."
    message = "The controller did not apply that action."
    raw = outcome.get("result_json")
    if raw:
        parsed = json.loads(raw)
        code = parsed.get("message") or parsed.get("error")
        if isinstance(code, str) and code in _ERROR_TEXT:
            message = _ERROR_TEXT[code]
        elif isinstance(code, str) and " " in code:
            message = code
    return message


def _require_confirm(confirm: str) -> None:
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="confirm=yes is required")


class _ControllerClock:
    """Stamp web commands with the controller's last write, not the wall clock."""

    def __init__(self, conn, fallback: Clock) -> None:
        self.conn = conn
        self.fallback = fallback

    def now(self):
        return database_now(self.conn, self.fallback.now())

    def monotonic(self) -> float:
        return self.fallback.monotonic()


SUBMIT_WAIT_S = 15.0


def _submit(app: FastAPI, command_type: str, params: dict, idempotency_key: str) -> dict:
    command_id = enqueue(
        app.state.conn,
        _ControllerClock(app.state.conn, app.state.clock),
        actor="web",
        command_type=command_type,
        params=params,
        idempotency_key=idempotency_key,
    )
    deadline = time.monotonic() + SUBMIT_WAIT_S
    while True:
        if app.state.pump is not None:
            app.state.pump()
        row = app.state.conn.execute("SELECT status, result_json FROM COMMAND WHERE id = ?", (command_id,)).fetchone()
        if row is None:
            return {"status": None, "result_json": None, "command_id": command_id}
        if row["status"] != "pending" or app.state.pump is not None or time.monotonic() >= deadline:
            return {"status": row["status"], "result_json": row["result_json"], "command_id": command_id}
        time.sleep(0.1)


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    parser = argparse.ArgumentParser(prog="fermentd-web")
    parser.add_argument("--config", default="config/fermentd.example.yaml")
    parser.add_argument(
        "--insecure-no-auth",
        action="store_true",
        help="serve on a non-loopback, non-Tailscale address without a login (not recommended)",
    )
    args = parser.parse_args(argv)
    config = load_config(Path(args.config))
    auth = auth_settings(config)
    problem = check_bind(config.web.bind, auth, args.insecure_no_auth or config.web.allow_insecure)
    if problem:
        raise SystemExit(f"fermentd-web: {problem}")
    conn = connect(Path(config.database.path))
    migrate(conn)
    app = create_app(conn, auth=auth)
    # Trust X-Forwarded-Proto only from a local reverse proxy (Caddy), so https is detected.
    uvicorn.run(app, host=config.web.bind, port=config.web.port, proxy_headers=True,
                forwarded_allow_ips="127.0.0.1")


def auth_settings(config) -> AuthSettings:
    web = load_secrets(Path(config.secrets)).web
    allowed = list(config.web.allowed_origins)
    if config.web.url:
        allowed.append(config.web.url)
    if web is None:
        return AuthSettings(allowed_origins=tuple(allowed))
    return AuthSettings(
        password_hash=web.password_hash,
        token=web.token,
        session_secret=web.session_secret,
        allowed_origins=tuple(allowed),
    )
