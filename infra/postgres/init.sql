-- Runs once when the Postgres container first starts
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

ALTER TABLE decisions ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64);

DO $$ BEGIN RAISE NOTICE 'ReturnGuard DB initialized ✓'; END $$;
