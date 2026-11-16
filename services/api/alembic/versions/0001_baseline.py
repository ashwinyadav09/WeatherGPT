"""0001_baseline

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-11-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension if Postgres
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # Places table
    op.create_table(
        "places",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("district", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Place names table
    op.create_table(
        "place_names",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("place_id", sa.String(length=64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
    )

    # Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("sender", sa.String(length=128), nullable=False),
        sa.Column("sent", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("msg_type", sa.String(length=32), nullable=False),
        sa.Column("hazard", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("urgency", sa.String(length=32), nullable=False),
        sa.Column("certainty", sa.String(length=32), nullable=False),
        sa.Column("onset", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("authority_tier", sa.Integer(), nullable=False, default=1),
        sa.Column("text_by_language", sa.JSON(), nullable=False),
        sa.Column("areas", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Evidence table
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("authority_tier", sa.Integer(), nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("place_id", sa.String(length=64), nullable=False),
        sa.Column("place_data", sa.JSON(), nullable=False),
        sa.Column("values_data", sa.JSON(), nullable=False),
        sa.Column("uncertainty", sa.JSON(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Answers table
    op.create_table(
        "answers",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Licence register table
    op.create_table(
        "licence_register",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), unique=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column("limits", sa.String(length=128), nullable=False),
        sa.Column("attribution_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Push subscriptions table
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("endpoint", sa.Text(), unique=True, nullable=False),
        sa.Column("auth", sa.String(length=128), nullable=False),
        sa.Column("p256dh", sa.String(length=256), nullable=False),
        sa.Column("places", sa.JSON(), nullable=False),
        sa.Column("severities", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Audit log table
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("push_subscriptions")
    op.drop_table("licence_register")
    op.drop_table("answers")
    op.drop_table("evidence")
    op.drop_table("alerts")
    op.drop_table("place_names")
    op.drop_table("places")
