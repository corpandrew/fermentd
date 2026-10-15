"""fermentd MCP server (read-only).

    python -m fermentd.mcp                       # stdio (for `ssh fermentd ... -m fermentd.mcp`)
    python -m fermentd.mcp --http --host <tailscale-ip> --port 8765   # streamable HTTP + bearer token

The database is opened with sqlite URI mode=ro and PRAGMA query_only, so no tool can write. Secrets
(plug keys, the ntfy topic, the MCP token) are never read into any tool result.
"""

from __future__ import annotations

import argparse
import hmac
import os
import sqlite3
from pathlib import Path
from typing import Annotated

from pydantic import Field

from fermentd.mcp import diary as d
from fermentd.mcp import queries as q

VesselId = Annotated[str, Field(description="A vessel_id returned by list_vessels.")]
BatchId = Annotated[int, Field(description="A batch_id returned by list_batches.")]
DEFAULT_DB = Path(os.environ.get("FERMENTD_DB", "data/fermentd.db"))


def build_server(
    db_path: Path | str = DEFAULT_DB,
    conn: sqlite3.Connection | None = None,
    writer=None,
    **settings,
):
    from mcp.server.fastmcp import FastMCP

    from fermentd.mcp import writes as w

    state = {"conn": conn, "writer": writer}

    def wr() -> w.Writer:
        if state["writer"] is None:
            state["writer"] = w.Writer(db_path)
        return state["writer"]

    def db() -> sqlite3.Connection:
        if state["conn"] is None:
            state["conn"] = q.connect_ro(db_path)
        return state["conn"]

    mcp = FastMCP(
        "fermentd",
        instructions=(
            "Read-only view of Andrew's fermentation controller: vessels, batches, temperatures, heat mat, "
            "scale weight, hydrometer readings and alerts. Temperatures are °F. Times are given in UTC and "
            "America/New_York. All tools are read-only except start_batch and end_batch, which change state "
            "on the Pi (through the controller, audited as 'mcp')."
        ),
        **settings,
    )
    ro = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

    @mcp.tool(annotations=ro)
    def list_vessels() -> dict:
        """All enabled vessels: id, name, type, current batch, latest temperature, target, heat mat on/off
        and the number of open alerts."""
        return q.list_vessels(db())

    @mcp.tool(annotations=ro)
    def get_vessel_status(vessel_id: VesselId) -> dict:
        """One vessel: its batch, temperature, heat mat and open alerts."""
        return q.get_vessel_status(db(), vessel_id)

    @mcp.tool(annotations=ro)
    def get_vessel_temperature(vessel_id: VesselId) -> dict:
        """Current vessel temperature, target, delta (temp - target), room temperature and reading age."""
        return q.get_vessel_temperature(db(), vessel_id)

    @mcp.tool(annotations=ro)
    def get_vessel_temperature_history(
        vessel_id: VesselId,
        hours: Annotated[float | None, Field(description="Look back this many hours (default 24).")] = 24,
        start: Annotated[str | None, Field(description="ISO 8601 start; overrides hours.")] = None,
        end: Annotated[str | None, Field(description="ISO 8601 end (default now).")] = None,
        bucket_minutes: Annotated[int | None, Field(description="Bucket size; default about 96 buckets.")] = None,
    ) -> dict:
        """Temperature min/max/avg per time bucket, with room average and heat-mat percent on."""
        return q.get_vessel_temperature_history(db(), vessel_id, hours, start, end, bucket_minutes)

    @mcp.tool(annotations=ro)
    def get_vessel_heater(vessel_id: VesselId) -> dict:
        """Heat mat on/off, when it last changed, and duty cycle (percent on) for 24 h and for the batch."""
        return q.get_vessel_heater(db(), vessel_id)

    @mcp.tool(annotations=ro)
    def get_vessel_weight(vessel_id: VesselId) -> dict:
        """Scale weight, CO2 lost, loss rate and estimated ABV. Says has_scale=false when there is none."""
        return q.get_vessel_weight(db(), vessel_id)

    @mcp.tool(annotations=ro)
    def list_batches(
        status: Annotated[str, Field(description="'active' (default), 'ended' or 'all'.")] = "active",
    ) -> dict:
        """Batches with vessel, profile, stage and day count."""
        return q.list_batches(db(), status)

    @mcp.tool(annotations=ro)
    def get_batch(batch_id: BatchId) -> dict:
        """One batch: profile, stage schedule, current and next temperature step, upcoming reminders."""
        return q.get_batch(db(), batch_id)

    @mcp.tool(annotations=ro)
    def get_batch_gravity(batch_id: BatchId) -> dict:
        """Hydrometer readings with estimated ABV and attenuation."""
        return q.get_batch_gravity(db(), batch_id)

    @mcp.tool(annotations=ro)
    def list_alerts(
        status: Annotated[str, Field(description="'open' (default), 'resolved' or 'all'.")] = "open",
        limit: Annotated[int, Field(description="Max alerts (default 50).")] = 50,
    ) -> dict:
        """Alerts, newest first, with type, severity, plain-English text and times."""
        return q.list_alerts(db(), status, limit)

    from fermentd.mcp import guide as g

    @mcp.tool(annotations=ro)
    def list_profiles(
        include_legacy: Annotated[bool, Field(description="Also show stale profiles from older builds.")] = False,
    ) -> dict:
        """Concise profile summary: id, name, drink type, default target and allowed range, batch sizes
        (gallons), and which vessel types and vessels each profile is allowed for. Use get_profile for
        the full guide."""
        return w.list_profiles(db(), include_legacy)

    @mcp.tool(annotations=ro)
    def get_profile(profile_id: Annotated[str, Field(description="A profile_id returned by list_profiles.")]) -> dict:
        """Full profile: drink type, description, stage schedule with temperature steps and per-stage
        guide steps, recommended/allowed ranges, reminders template, allowed vessel types, ingredients
        for 1 gal and 0.5 gal, equipment, guide sections and expected timeline."""
        return g.get_profile(db(), profile_id)

    @mcp.tool(annotations=ro)
    def get_next_actions(
        batch_id: Annotated[int | None, Field(description="A batch_id; omit for all active batches.")] = None,
    ) -> dict:
        """What's next: current stage and what it means, the guide's next steps for this stage, pending
        reminders (ids, due times, overdue flag), what triggers moving on, and the next stage id."""
        return g.next_actions(db(), batch_id)

    write = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}

    @mcp.tool(annotations=write)
    def start_batch(
        vessel_id: VesselId,
        profile_id: Annotated[str, Field(description="A profile_id returned by list_profiles.")],
        name: Annotated[str, Field(description="Batch name, e.g. 'Brut cider #2'.")],
        batch_size: Annotated[float | None, Field(description="Gallons: 1 (default) or 0.5.")] = None,
        target_f: Annotated[float | None, Field(description="Optional target °F within the profile range.")] = None,
        variant_id: Annotated[int | None, Field(description="Start from a saved 'my version' (list_variants).")] = None,
        copy_tweaks_from_batch_id: Annotated[
            int | None, Field(description="Copy the recipe changes from an earlier batch of the same profile.")
        ] = None,
        stage: Annotated[str | None, Field(
            description="Stage to start in. 'prep' = Making it (brewing or mixing; no temperature control "
                        "until you advance). Default: the profile's usual starting stage.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Starts a batch on an idle vessel and starts heating to its
        target (unless it starts in 'prep', or the vessel has no heater zone, which is monitor-only).
        Rejected if the vessel already has an active batch, the profile is unknown or not allowed for
        the vessel, or target_f is outside the profile range. Returns the batch like get_batch."""
        return w.start_batch(db(), wr(), vessel_id, profile_id, name, batch_size, target_f, variant_id,
                             copy_tweaks_from_batch_id, stage)

    @mcp.tool(annotations=write)
    def advance_stage(
        batch_id: BatchId,
        to_stage: Annotated[str | None, Field(description="Stage id from the schedule; default the next one.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Moves a batch to the next stage (or to_stage), which may change
        the target temperature and schedules that stage's reminders. Returns the batch like get_batch."""
        return w.advance_stage(db(), wr(), batch_id, to_stage)

    @mcp.tool(annotations=write)
    def complete_reminder(
        reminder_id: Annotated[int | None, Field(description="reminder_id from get_next_actions/get_batch.")] = None,
        batch_id: Annotated[int | None, Field(description="With reminder: the batch it belongs to.")] = None,
        reminder: Annotated[str | None, Field(description="With batch_id: the reminder key, e.g. 'squeeze'.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Marks a pending reminder done (and clears its alert)."""
        return w.complete_reminder(db(), wr(), reminder_id, batch_id, reminder)

    @mcp.tool(annotations=write)
    def log_gravity(
        batch_id: BatchId,
        sg: Annotated[float, Field(description="Hydrometer reading, 0.980-1.200.")],
        temp_f: Annotated[float | None, Field(description="Sample temperature °F; corrects to 60 °F.")] = None,
        note: Annotated[str | None, Field(description="Optional note saved with the batch.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Logs a hydrometer reading (temperature-corrected when temp_f is
        given) and returns the updated gravity log with estimated ABV."""
        return w.log_gravity(db(), wr(), batch_id, sg, temp_f, note)

    @mcp.tool(annotations={**write, "destructiveHint": True})
    def end_batch(batch_id: BatchId) -> dict:
        """WRITE: Changes state on the Pi. Ends an active batch (cancels its reminders; the heat mat
        turns off if nothing else in the zone needs heat). Cannot be undone. Returns the final state."""
        return w.end_batch(db(), wr(), batch_id)

    from fermentd.mcp import tastes as t

    @mcp.tool(annotations=ro)
    def get_batch_tweaks(batch_id: BatchId) -> dict:
        """A batch's recipe next to the written recipe: each ingredient with 'recipe says' vs 'you used'
        (changed / added / left out), process notes, and the saved version it started from."""
        return t.get_batch_tweaks(db(), batch_id)

    @mcp.tool(annotations=ro)
    def list_tastings(
        batch_id: Annotated[int | None, Field(description="A batch_id; omit for every tasting.")] = None,
    ) -> dict:
        """Tasting log entries (newest first): date, 1-5 rating, 1-5 sliders, notes, would-make-again."""
        return t.list_tastings(db(), batch_id)

    @mcp.tool(annotations=ro)
    def get_best_batches(
        profile_id: Annotated[str | None, Field(description="Limit to one profile, e.g. soda_ginger_ale.")] = None,
        drink_type: Annotated[str | None, Field(description="Or limit to a drink type, e.g. soda, cider.")] = None,
        limit: Annotated[int, Field(description="How many (default 10).")] = 10,
    ) -> dict:
        """Batches ranked by average tasting rating, with each batch's recipe changes and latest note.
        Answers 'what was my best ginger ale and what did I change?'."""
        return t.get_best_batches(db(), profile_id, drink_type, limit)

    @mcp.tool(annotations=ro)
    def list_variants(
        profile_id: Annotated[str | None, Field(description="Limit to one profile.")] = None,
    ) -> dict:
        """Saved 'my version' recipes (a profile plus your changes) that start_batch can use."""
        return t.list_variants(db(), profile_id)

    @mcp.tool(annotations=write)
    def add_batch_tweak(
        batch_id: BatchId,
        kind: Annotated[str, Field(description="'change' (amount), 'add', 'remove', or 'note' (process).")],
        ingredient: Annotated[str | None, Field(description="Recipe ingredient id or name (change/remove).")] = None,
        amount: Annotated[str | None, Field(description="New amount, e.g. '4 oz' (change/add).")] = None,
        item: Annotated[str | None, Field(description="Name of an added ingredient.")] = None,
        note: Annotated[str | None, Field(description="Note, e.g. 'steeped ginger 20 min'.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Records a recipe change for this batch (amount change, added or
        left-out ingredient, or a process note). Returns the batch's recipe with changes."""
        return t.add_batch_tweak(db(), wr(), batch_id, kind, ingredient, amount, item, note)

    @mcp.tool(annotations=write)
    def remove_batch_tweak(
        tweak_id: Annotated[int, Field(description="tweak_id from get_batch_tweaks.")],
        batch_id: Annotated[int | None, Field(description="Optional check that it belongs to this batch.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Undoes one recorded recipe change (kept in history)."""
        return t.remove_batch_tweak(db(), wr(), tweak_id, batch_id)

    @mcp.tool(annotations=write)
    def log_tasting(
        batch_id: BatchId,
        rating: Annotated[int, Field(description="Overall 1-5.")],
        date: Annotated[str | None, Field(description="Date tasted, e.g. 2026-10-20 (default now).")] = None,
        carbonation: Annotated[int | None, Field(description="1 flat - 5 very fizzy.")] = None,
        sweetness: Annotated[int | None, Field(description="1 not sweet - 5 very sweet.")] = None,
        dryness: Annotated[int | None, Field(description="1 sweet - 5 bone dry.")] = None,
        flavor: Annotated[int | None, Field(description="1 mild - 5 strong flavor.")] = None,
        notes: Annotated[str | None, Field(description="Free-text notes.")] = None,
        make_again: Annotated[bool | None, Field(description="Would make it again?")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Adds a tasting entry to a batch (active or ended)."""
        return t.log_tasting(db(), wr(), batch_id, rating, date, carbonation, sweetness, dryness, flavor, notes,
                             make_again)

    @mcp.tool(annotations=write)
    def save_tweaks_as_variant(
        batch_id: BatchId,
        name: Annotated[str | None, Field(description="Name for your version, e.g. 'Spicy ginger ale'.")] = None,
    ) -> dict:
        """WRITE: Changes state on the Pi. Saves this batch's recipe changes as a reusable 'my version'
        that start_batch can start from (variant_id)."""
        return t.save_tweaks_as_variant(db(), wr(), batch_id, name)

    @mcp.tool(annotations=ro)
    def list_batch_notes(batch_id: BatchId) -> dict:
        """Timestamped notes for a batch, newest first, with links to any photos (full size and thumbnail)
        on the dashboard."""
        return d.list_batch_notes(db(), batch_id)

    @mcp.tool(annotations=ro)
    def get_batch_activity(
        batch_id: BatchId,
        limit: Annotated[int | None, Field(description="Most recent entries to return (default 50, max 500).")] = 50,
    ) -> dict:
        """What was done to a batch, newest first, in plain English: start and end, stage changes, target
        changes, reminders done, gravity readings, recipe changes, tastings and notes, each with its time and
        source (Dashboard or Grok Bot via MCP). Automatic heat mat switching is not included."""
        return d.get_batch_activity(db(), batch_id, limit)

    @mcp.tool(annotations=write)
    def add_batch_note(
        batch_id: BatchId,
        text: Annotated[str, Field(description="The note, e.g. 'Lots of bubbles, smells gingery'. Max 2000 characters.")],
    ) -> dict:
        """WRITE: Changes state on the Pi. Adds a timestamped text note to a batch (active or ended).
        Photos can only be added from the dashboard."""
        return d.add_batch_note(db(), wr(), batch_id, text)

    # Report a server version that changes whenever the tool set does, so a client that caches the
    # tool list per server version can tell it is stale (FastMCP 1.x has no tools/list_changed push).
    import hashlib
    import importlib.metadata

    names = sorted(t.name for t in mcp._tool_manager.list_tools())
    try:
        base = importlib.metadata.version("fermentd")
    except importlib.metadata.PackageNotFoundError:
        base = "0"
    digest = hashlib.sha1(",".join(names).encode()).hexdigest()[:8]
    mcp._mcp_server.version = f"{base}+tools{len(names)}.{digest}"
    return mcp


class BearerAuth:
    """ASGI middleware: every request needs `Authorization: Bearer <token>` (constant-time compare)."""

    def __init__(self, app, token: str) -> None:
        if not token or len(token) < 24:
            raise ValueError("MCP token missing or too short")
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            got = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(got, self.expected):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain"), (b"www-authenticate", b"Bearer")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await self.app(scope, receive, send)


def _token(secrets_path: Path) -> str:
    from fermentd.config import load_secrets

    secrets = load_secrets(secrets_path)
    if secrets.mcp is None:
        raise SystemExit(f"no mcp.token in {secrets_path}")
    return secrets.mcp.token


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fermentd.mcp")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--http", action="store_true", help="streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--secrets", type=Path, default=Path("config/secrets.yaml"))
    args = parser.parse_args(argv)
    if not args.http:
        build_server(args.db, log_level="WARNING").run("stdio")
        return
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[args.host, f"{args.host}:{args.port}", "fermentd", f"fermentd:{args.port}"],
    )
    server = build_server(args.db, host=args.host, port=args.port, transport_security=security, log_level="WARNING")
    app = BearerAuth(server.streamable_http_app(), _token(args.secrets))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
