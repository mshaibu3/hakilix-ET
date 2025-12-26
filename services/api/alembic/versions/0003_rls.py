from __future__ import annotations
from alembic import op

revision = "0003_rls"
down_revision = "0002_tscale"
branch_labels = None
depends_on = None

def upgrade():
    for t in ["agencies","users","residents","devices","telemetry","risk_events","audit_log"]:
        op.execute(f"ALTER TABLE hakilix.{t} ENABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS p_agencies ON hakilix.agencies;")
    op.execute("CREATE POLICY p_agencies ON hakilix.agencies USING (id = current_setting('app.tenant_id', true));")

    for t in ["users","residents","devices","telemetry","risk_events","audit_log"]:
        op.execute(f"DROP POLICY IF EXISTS p_{t} ON hakilix.{t};")
        op.execute(
            f"CREATE POLICY p_{t} ON hakilix.{t} "
            f"USING (agency_id = current_setting('app.tenant_id', true)) "
            f"WITH CHECK (agency_id = current_setting('app.tenant_id', true));"
        )

def downgrade():
    for t in ["agencies","users","residents","devices","telemetry","risk_events","audit_log"]:
        op.execute(f"ALTER TABLE hakilix.{t} DISABLE ROW LEVEL SECURITY;")
