CREATE TABLE NOTIFICATION_OUTBOX (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL,
    sent_at TEXT
);
