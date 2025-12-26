from __future__ import annotations

"""Make devices.resident_id safe on resident delete.

The dashboard supports resident deletion for demo / admin flows. The original schema
used the default FK action (RESTRICT), which can produce 500 errors when a device is
assigned to the resident being deleted.

We change the FK to ON DELETE SET NULL so that devices can be safely re-assigned.
"""

from alembic import op


revision = "0006_devices_resident_fk"
down_revision = "0005_seq_privs"
branch_labels = None
depends_on = None


def upgrade():
    # Default constraint name for Postgres is typically <table>_<col>_fkey.
    op.execute("ALTER TABLE hakilix.devices DROP CONSTRAINT IF EXISTS devices_resident_id_fkey;")
    op.execute(
        "ALTER TABLE hakilix.devices "
        "ADD CONSTRAINT devices_resident_id_fkey "
        "FOREIGN KEY (resident_id) REFERENCES hakilix.residents(id) ON DELETE SET NULL;"
    )


def downgrade():
    op.execute("ALTER TABLE hakilix.devices DROP CONSTRAINT IF EXISTS devices_resident_id_fkey;")
    op.execute(
        "ALTER TABLE hakilix.devices "
        "ADD CONSTRAINT devices_resident_id_fkey "
        "FOREIGN KEY (resident_id) REFERENCES hakilix.residents(id);"
    )
