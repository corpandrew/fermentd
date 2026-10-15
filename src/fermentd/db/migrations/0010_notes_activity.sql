-- Batch notes with optional photos, and a batch link on AUDIT_LOG for the per-batch activity log.
ALTER TABLE NOTE ADD COLUMN photo TEXT;        -- file name under data/photos (<=1600 px JPEG)
ALTER TABLE NOTE ADD COLUMN thumb TEXT;        -- file name under data/photos (<=320 px JPEG)
ALTER TABLE NOTE ADD COLUMN command_id INTEGER REFERENCES COMMAND(id);
ALTER TABLE AUDIT_LOG ADD COLUMN batch_id INTEGER;
CREATE INDEX IF NOT EXISTS audit_log_batch ON AUDIT_LOG(batch_id, ts);
CREATE INDEX IF NOT EXISTS note_batch ON NOTE(batch_id, ts);

-- Backfill. Batch ids can be reused after a delete, so every link also checks the batch was
-- running at that time (a 2-minute grace covers the end_batch row itself).
UPDATE AUDIT_LOG SET batch_id = (
    SELECT b.id FROM BATCH b
    WHERE b.id = COALESCE(
            CASE WHEN json_valid(AUDIT_LOG.new_value) THEN json_extract(AUDIT_LOG.new_value, '$.batch_id') END,
            CASE WHEN AUDIT_LOG.target LIKE 'batch:%' THEN CAST(substr(AUDIT_LOG.target, 7) AS INTEGER) END)
      AND b.started_at <= AUDIT_LOG.ts
      AND (b.ended_at IS NULL OR AUDIT_LOG.ts <= strftime('%Y-%m-%dT%H:%M:%SZ', b.ended_at, '+2 minutes'))
)
WHERE batch_id IS NULL;

-- Target changes are logged against a vessel or zone: link them to the batch running there.
UPDATE AUDIT_LOG SET batch_id = (
    SELECT b.id FROM BATCH b JOIN VESSEL v ON v.id = b.vessel_id
    WHERE (b.vessel_id = AUDIT_LOG.target
           OR v.temp_zone_id = CASE WHEN AUDIT_LOG.target LIKE 'zone:%' THEN substr(AUDIT_LOG.target, 6) ELSE AUDIT_LOG.target END
           OR v.temp_zone_id = CASE WHEN json_valid(AUDIT_LOG.new_value) THEN json_extract(AUDIT_LOG.new_value, '$.zone') END)
      AND b.started_at <= AUDIT_LOG.ts AND (b.ended_at IS NULL OR AUDIT_LOG.ts <= b.ended_at)
    ORDER BY b.id DESC LIMIT 1
)
WHERE batch_id IS NULL AND action = 'set_target_temp';
