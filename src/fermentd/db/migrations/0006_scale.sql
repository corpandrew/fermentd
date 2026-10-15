-- Load-cell scales: calibration and status per vessel, and 5-minute weight samples.
CREATE TABLE SCALE (
    vessel_id TEXT PRIMARY KEY REFERENCES VESSEL(id),
    driver TEXT NOT NULL,
    tare_offset REAL,
    counts_per_gram REAL,
    cal_weight_g REAL,
    tared_at TEXT,
    calibrated_at TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    status_detail TEXT,
    status_at TEXT,
    last_raw REAL
);

CREATE TABLE WEIGHT_READING (
    ts TEXT NOT NULL,
    vessel_id TEXT NOT NULL REFERENCES VESSEL(id),
    batch_id INTEGER REFERENCES BATCH(id),
    raw REAL NOT NULL,
    grams REAL,
    PRIMARY KEY (ts, vessel_id)
);
CREATE INDEX weight_reading_batch ON WEIGHT_READING (batch_id, ts);
