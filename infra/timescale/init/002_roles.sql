DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_migrator') THEN
    CREATE ROLE hakilix_migrator LOGIN PASSWORD 'hakilix' INHERIT;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_app') THEN
    CREATE ROLE hakilix_app LOGIN PASSWORD 'hakilix' INHERIT;
  END IF;
END $$;

GRANT CONNECT ON DATABASE hakilix TO hakilix_migrator, hakilix_app;

-- Required for Alembic migrations (schema/table creation).
-- Without this, the migrate job fails at 0001_init when executing
--   CREATE SCHEMA IF NOT EXISTS hakilix;
GRANT CREATE ON DATABASE hakilix TO hakilix_migrator;

