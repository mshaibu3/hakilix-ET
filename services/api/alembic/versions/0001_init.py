from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS hakilix")

    op.create_table(
        "agencies",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="hakilix",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agency_id", sa.String(64), sa.ForeignKey("hakilix.agencies.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="hakilix",
    )

    op.create_table(
        "residents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agency_id", sa.String(64), sa.ForeignKey("hakilix.agencies.id"), nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="hakilix",
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("agency_id", sa.String(64), sa.ForeignKey("hakilix.agencies.id"), nullable=False, index=True),
        sa.Column("resident_id", sa.String(64), sa.ForeignKey("hakilix.residents.id"), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_cert_serial", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="hakilix",
    )

    op.create_table(
        "telemetry",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("agency_id", sa.String(64), nullable=False, index=True),
        sa.Column("resident_id", sa.String(64), nullable=False, index=True),
        sa.Column("device_id", sa.String(64), nullable=False, index=True),
        sa.Column("hr", sa.Float(), nullable=True),
        sa.Column("spo2", sa.Float(), nullable=True),
        sa.Column("rr", sa.Float(), nullable=True),
        sa.Column("temp_c", sa.Float(), nullable=True),
        sa.Column("gait_instability", sa.Float(), nullable=True),
        sa.Column("orthostatic_hypotension", sa.Float(), nullable=True),
        sa.Column("night_wandering", sa.Float(), nullable=True),
        sa.Column("intake_ml", sa.Float(), nullable=True),
        sa.Column("sleep_fragmentation", sa.Float(), nullable=True),
        sa.Column("agitation", sa.Float(), nullable=True),
        sa.Column("toileting_freq", sa.Float(), nullable=True),
        schema="hakilix",
    )

    op.create_table(
        "risk_events",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("agency_id", sa.String(64), nullable=False, index=True),
        sa.Column("resident_id", sa.String(64), nullable=False, index=True),
        sa.Column("falls_risk", sa.Float(), nullable=False),
        sa.Column("resp_risk", sa.Float(), nullable=False),
        sa.Column("dehydration_risk", sa.Float(), nullable=False),
        sa.Column("delirium_uti_risk", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("explain", sa.Text(), nullable=True),
        schema="hakilix",
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("agency_id", sa.String(64), nullable=True, index=True),
        sa.Column("actor_user_id", sa.String(64), nullable=True),
        sa.Column("actor_device_id", sa.String(64), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource", sa.String(128), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        schema="hakilix",
    )

def downgrade():
    op.drop_table("audit_log", schema="hakilix")
    op.drop_table("risk_events", schema="hakilix")
    op.drop_table("telemetry", schema="hakilix")
    op.drop_table("devices", schema="hakilix")
    op.drop_table("residents", schema="hakilix")
    op.drop_table("users", schema="hakilix")
    op.drop_table("agencies", schema="hakilix")
