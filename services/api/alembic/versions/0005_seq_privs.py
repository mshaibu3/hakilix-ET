from __future__ import annotations
from alembic import op

revision = "0005_seq_privs"
down_revision = "0004_privs"
branch_labels = None
depends_on = None

def upgrade():
    # Sequence privileges are required for SERIAL/IDENTITY inserts (nextval()).
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA hakilix TO hakilix_app, hakilix_ingest;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT USAGE, SELECT ON SEQUENCES TO hakilix_app, hakilix_ingest;")

    # Readonly does not need sequence usage.
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA hakilix TO hakilix_migrator;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA hakilix GRANT ALL PRIVILEGES ON SEQUENCES TO hakilix_migrator;")

def downgrade():
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA hakilix FROM hakilix_app, hakilix_ingest, hakilix_migrator;")
