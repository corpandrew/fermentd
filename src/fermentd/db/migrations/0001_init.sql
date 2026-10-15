-- Design section 9. reminder_key, repeat_seconds, and last_notified_at
-- are extra columns the ginger-ale timer needs to repeat and complete one reminder.

CREATE TABLE TEMP_ZONE (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capability TEXT NOT NULL,
    actuator_driver TEXT NOT NULL,
    device_ref TEXT,
    target_f REAL NOT NULL,
    hysteresis_f REAL NOT NULL,
    learned_overshoot_f REAL NOT NULL DEFAULT 0,
    mode TEXT NOT NULL DEFAULT 'auto',
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE VESSEL (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    vessel_type TEXT NOT NULL,
    capacity_l REAL,
    hx711_dout_gpio INTEGER,
    hx711_sck_gpio INTEGER,
    probe_rom_id TEXT,
    scale_factor REAL,
    tare_offset REAL,
    temp_zone_id TEXT REFERENCES TEMP_ZONE(id),
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE BEVERAGE_PROFILE (
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    extends TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (id, version)
);

CREATE TABLE BATCH (
    id INTEGER PRIMARY KEY,
    vessel_id TEXT NOT NULL REFERENCES VESSEL(id),
    profile_id TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    profile_snapshot_json TEXT NOT NULL,
    overrides_json TEXT,
    tracking_mode TEXT NOT NULL,
    name TEXT NOT NULL,
    base TEXT,
    yeast TEXT,
    og REAL,
    start_weight_g REAL,
    container_mass_g REAL,
    volume_l REAL,
    target_temp_f REAL,
    stage TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    final_sg REAL,
    final_abv REAL,
    k_points_per_gl REAL,
    recipe_json TEXT
);

CREATE TABLE DIGEST_LOG (
    digest_id TEXT PRIMARY KEY,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    sent_by TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    late INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE READING (
    ts TEXT NOT NULL,
    vessel_id TEXT NOT NULL REFERENCES VESSEL(id),
    batch_id INTEGER REFERENCES BATCH(id),
    weight_g REAL,
    vessel_temp_f REAL,
    ambient_temp_f REAL,
    heater_on INTEGER NOT NULL,
    flags INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ts, vessel_id)
);

CREATE TABLE READING_HOURLY (
    hour_ts TEXT NOT NULL,
    vessel_id TEXT NOT NULL,
    batch_id INTEGER,
    weight_avg_g REAL,
    weight_min_g REAL,
    weight_max_g REAL,
    vessel_temp_avg_f REAL,
    vessel_temp_min_f REAL,
    vessel_temp_max_f REAL,
    ambient_avg_f REAL,
    heater_duty REAL,
    PRIMARY KEY (hour_ts, vessel_id)
);

CREATE TABLE GRAVITY_READING (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    ts TEXT NOT NULL,
    sg REAL NOT NULL,
    source TEXT NOT NULL,
    sample_temp_f REAL,
    sample_removed_g REAL
);

CREATE TABLE BASELINE_SEGMENT (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    started_at TEXT NOT NULL,
    base_weight_g REAL NOT NULL,
    base_sg REAL,
    volume_l REAL,
    reason TEXT NOT NULL
);

CREATE TABLE NOTE (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE EVENT (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    batch_id INTEGER REFERENCES BATCH(id),
    vessel_id TEXT,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    actor TEXT NOT NULL,
    detail_json TEXT
);

CREATE TABLE ALERT (
    id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES EVENT(id),
    dedupe_key TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    acked_at TEXT,
    acked_by TEXT,
    resolved_at TEXT
);

CREATE TABLE REMINDER (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    reminder_key TEXT NOT NULL,
    due_at TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    repeat_seconds INTEGER,
    last_notified_at TEXT
);

CREATE TABLE SETTING (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE TABLE COMMAND (
    id INTEGER PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    actor TEXT NOT NULL,
    type TEXT NOT NULL,
    params_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    executed_at TEXT,
    expires_at TEXT NOT NULL
);

CREATE TABLE AUDIT_LOG (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    command_id INTEGER REFERENCES COMMAND(id)
);

CREATE TABLE API_KEY (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    scope TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE UNIQUE INDEX command_actor_idempotency ON COMMAND(actor, idempotency_key);
CREATE INDEX command_status ON COMMAND(status);
CREATE INDEX alert_status ON ALERT(status);
CREATE INDEX batch_vessel ON BATCH(vessel_id, ended_at);
CREATE UNIQUE INDEX alert_open_dedupe ON ALERT(dedupe_key) WHERE status != 'resolved';
