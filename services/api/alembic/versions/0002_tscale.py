from __future__ import annotations

from alembic import op

revision = "0002_tscale"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Analytics layer.

    This migration is *dual-mode*:
    - If TimescaleDB is available (self-managed Postgres / Timescale), it enables the extension,
      converts telemetry to a hypertable, and creates a continuous aggregate.
    - If TimescaleDB is NOT available (e.g. Cloud SQL for PostgreSQL), it falls back to standard
      PostgreSQL: indexes + a plain view for hourly rollups.

    Cloud SQL supports only a curated set of extensions; TimescaleDB is not supported there. citeturn0search0
    """

    # Ensure schema exists
    op.execute("CREATE SCHEMA IF NOT EXISTS hakilix;")

    # Detect whether TimescaleDB is available
    op.execute(
        """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS timescaledb';
  END IF;
END $$;
"""
    )

    # If TimescaleDB exists, convert telemetry table to hypertable (best-effort)
    op.execute(
        """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='create_hypertable') THEN
    BEGIN
      PERFORM create_hypertable('hakilix.telemetry', 'time', if_not_exists => TRUE);
    EXCEPTION WHEN others THEN
      NULL;
    END;
  END IF;
END $$;
"""
    )

    # Indexes (useful for both modes)
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_agency_resident_time ON hakilix.telemetry (agency_id, resident_id, time DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_risk_events_agency_resident_time ON hakilix.risk_events (agency_id, resident_id, time DESC);")

    # Continuous aggregate if TimescaleDB is present; otherwise create a plain view.
    # Timescale continuous aggregates are optional; the dashboard can query either.
    op.execute(
        """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='time_bucket') THEN
    -- Timescale continuous aggregate (refresh handled elsewhere)
    BEGIN
      EXECUTE $SQL$
        CREATE MATERIALIZED VIEW IF NOT EXISTS hakilix.vitals_1h
        WITH (timescaledb.continuous) AS
          SELECT
            time_bucket('1 hour', time) AS bucket,
            agency_id,
            resident_id,
            avg(hr) AS hr_avg,
            avg(spo2) AS spo2_avg,
            avg(rr) AS rr_avg,
            avg(temp_c) AS temp_avg
          FROM hakilix.telemetry
          GROUP BY bucket, agency_id, resident_id
        WITH NO DATA;
      $SQL$;
    EXCEPTION WHEN others THEN
      NULL;
    END;
  ELSE
    -- Standard PostgreSQL fallback: plain VIEW using date_trunc
    EXECUTE $SQL$
      CREATE OR REPLACE VIEW hakilix.vitals_1h AS
        SELECT
          date_trunc('hour', time) AS bucket,
          agency_id,
          resident_id,
          avg(hr) AS hr_avg,
          avg(spo2) AS spo2_avg,
          avg(rr) AS rr_avg,
          avg(temp_c) AS temp_avg
        FROM hakilix.telemetry
        GROUP BY date_trunc('hour', time), agency_id, resident_id;
    $SQL$;
  END IF;
END $$;
"""
    )


def downgrade() -> None:
    # Best-effort cleanup in both modes
    op.execute("DROP MATERIALIZED VIEW IF EXISTS hakilix.vitals_1h;")
    op.execute("DROP VIEW IF EXISTS hakilix.vitals_1h;")
