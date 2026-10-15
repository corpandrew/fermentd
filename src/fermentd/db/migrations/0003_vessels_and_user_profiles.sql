-- Vessels added from the dashboard are stored here with source 'dashboard'.
-- Config vessels keep source 'config' and are still owned by fermentd.yaml.
ALTER TABLE VESSEL ADD COLUMN source TEXT NOT NULL DEFAULT 'config';
CREATE INDEX beverage_profile_source ON BEVERAGE_PROFILE(source, id, version);
