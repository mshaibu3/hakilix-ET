from __future__ import annotations
from alembic import op

revision = "0004_privs"
down_revision = "0003_rls"
branch_labels = None
depends_on = None

def upgrade():
    # Create roles if they don't exist (Cloud SQL supports CREATE ROLE by an admin user)
    op.execute("""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_app') THEN
    CREATE ROLE hakilix_app;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_ingest') THEN
    CREATE ROLE hakilix_ingest;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_readonly') THEN
    CREATE ROLE hakilix_readonly;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='hakilix_migrator') THEN
    CREATE ROLE hakilix_migrator;
  END IF;
END $$;
""")

    # Schema usage
    op.execute("GRANT USAGE ON SCHEMA hakilix TO hakilix_app, hakilix_ingest, hakilix_readonly, hakilix_migrator;")

    # App role: full CRUD on tenant-scoped tables
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA hakilix TO hakilix_app;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hakilix_app;")

    # Ingest role: write-only for telemetry + audit, read residents/devices for validation.
    op.execute("GRANT SELECT ON hakilix.agencies, hakilix.residents, hakilix.devices TO hakilix_ingest;")
    op.execute("GRANT INSERT ON hakilix.telemetry, hakilix.risk_events, hakilix.audit_log TO hakilix_ingest;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT INSERT ON TABLES TO hakilix_ingest;")

    # Readonly role: read access for analytics consumers (optional)
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA hakilix TO hakilix_readonly;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT SELECT ON TABLES TO hakilix_readonly;")

    # Migrator: full privileges for schema evolution
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA hakilix TO hakilix_migrator;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT ALL PRIVILEGES ON TABLES TO hakilix_migrator;")

def downgrade():
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA hakilix FROM hakilix_app, hakilix_ingest, hakilix_readonly, hakilix_migrator;")
