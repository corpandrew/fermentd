-- When the batch entered its current stage, for timed temperature steps.
ALTER TABLE BATCH ADD COLUMN stage_started_at TEXT;
UPDATE BATCH SET stage_started_at = started_at WHERE stage_started_at IS NULL;
