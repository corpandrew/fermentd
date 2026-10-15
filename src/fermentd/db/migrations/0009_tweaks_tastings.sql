-- Per-batch recipe tweaks, tasting notes, and saved "my version" recipe variants.
CREATE TABLE BATCH_TWEAK (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    kind TEXT NOT NULL CHECK (kind IN ('change', 'add', 'remove', 'note')),
    ingredient_id TEXT,
    item TEXT,
    from_amount TEXT,
    to_amount TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    removed_at TEXT
);
CREATE INDEX batch_tweak_batch ON BATCH_TWEAK (batch_id);

CREATE TABLE TASTING (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES BATCH(id),
    tasted_at TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    carbonation INTEGER CHECK (carbonation BETWEEN 1 AND 5),
    sweetness INTEGER CHECK (sweetness BETWEEN 1 AND 5),
    dryness INTEGER CHECK (dryness BETWEEN 1 AND 5),
    flavor INTEGER CHECK (flavor BETWEEN 1 AND 5),
    notes TEXT,
    make_again INTEGER,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL
);
CREATE INDEX tasting_batch ON TASTING (batch_id);

CREATE TABLE PROFILE_VARIANT (
    id INTEGER PRIMARY KEY,
    profile_id TEXT NOT NULL,
    name TEXT NOT NULL,
    tweaks_json TEXT NOT NULL,
    source_batch_id INTEGER REFERENCES BATCH(id),
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL
);

ALTER TABLE BATCH ADD COLUMN variant_id INTEGER REFERENCES PROFILE_VARIANT(id);
