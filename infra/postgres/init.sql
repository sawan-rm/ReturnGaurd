-- Runs once when the Postgres container first starts
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$ BEGIN RAISE NOTICE 'ReturnGuard DB initialized ✓'; END $$;
