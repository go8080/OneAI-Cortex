"""add_tool_auth_type

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-04-14 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auth_type column to tools table for Connected Services integration."""
    op.add_column(
        "tools",
        sa.Column(
            "auth_type",
            sa.String(30),
            server_default="api_key",
            nullable=False,
        ),
    )

    # Mark existing Gmail tools as google_oauth
    op.execute(
        "UPDATE tools SET auth_type = 'google_oauth' "
        "WHERE name IN ('gmail_send_message', 'gmail_search')"
    )


def downgrade() -> None:
    """Remove auth_type column from tools table."""
    op.drop_column("tools", "auth_type")
