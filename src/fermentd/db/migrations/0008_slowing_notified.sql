-- Fermentation-slowing alert fires once per batch.
ALTER TABLE BATCH ADD COLUMN slowing_notified_at TEXT;
