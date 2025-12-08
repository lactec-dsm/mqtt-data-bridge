"""create medicoes table with indexes

Revision ID: 2024_10_17_0001
Revises: 
Create Date: 2024-10-17
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2024_10_17_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "medicoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("measurement_id", sa.String(length=100), nullable=False),
        sa.Column("measurement_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("raw_payload", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_medicoes_device_id", "medicoes", ["device_id"], unique=False
    )
    op.create_index(
        "ix_medicoes_measurement_id", "medicoes", ["measurement_id"], unique=False
    )
    op.create_index(
        "ix_medicoes_timestamp", "medicoes", ["timestamp"], unique=False
    )
    op.create_index(
        "ix_medicoes_device_measure_ts",
        "medicoes",
        ["device_id", "measurement_id", "timestamp"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_medicoes_device_measure_ts", table_name="medicoes")
    op.drop_index("ix_medicoes_timestamp", table_name="medicoes")
    op.drop_index("ix_medicoes_measurement_id", table_name="medicoes")
    op.drop_index("ix_medicoes_device_id", table_name="medicoes")
    op.drop_table("medicoes")
