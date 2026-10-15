-- One-time "target reached" notifications. armed_* is the target being approached and when it was
-- set; reached_f is the last target already announced, so a restart never repeats the alert.
ALTER TABLE BATCH ADD COLUMN target_armed_f REAL;
ALTER TABLE BATCH ADD COLUMN target_armed_at TEXT;
ALTER TABLE BATCH ADD COLUMN target_reached_f REAL;
ALTER TABLE BATCH ADD COLUMN target_reached_at TEXT;
UPDATE BATCH SET target_armed_at = started_at WHERE target_armed_at IS NULL;
