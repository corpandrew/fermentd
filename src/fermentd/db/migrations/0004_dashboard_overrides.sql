-- fermentd.yaml seeds vessels and zones. Once a field is edited in the dashboard,
-- the database copy wins on every later start.
ALTER TABLE VESSEL ADD COLUMN user_edited INTEGER NOT NULL DEFAULT 0;
ALTER TABLE TEMP_ZONE ADD COLUMN user_named INTEGER NOT NULL DEFAULT 0;
