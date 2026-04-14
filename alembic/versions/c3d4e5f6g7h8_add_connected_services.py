"""add_connected_services

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-14 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create connected_services table for OAuth provider connections."""
    op.create_table(
        "connected_services",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("granted_scopes", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status", sa.String(20), server_default="active", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "provider", name="uq_connected_services_user_provider"
        ),
    )
    op.create_index(
        "ix_connected_services_user_id",
        "connected_services",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop connected_services table."""
    op.drop_index("ix_connected_services_user_id", table_name="connected_services")
    op.drop_table("connected_services")
