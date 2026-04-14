"""add_tool_catalog_columns

Revision ID: a1b2c3d4e5f6
Revises: 3ddce77f678e
Create Date: 2026-04-10 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "3ddce77f678e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add categorization, LangChain metadata, and playground test columns to tools table."""
    # Categorization
    op.add_column("tools", sa.Column("category", sa.String(30), nullable=True))
    op.add_column("tools", sa.Column("langchain_class", sa.String(200), nullable=True))
    op.add_column(
        "tools",
        sa.Column(
            "required_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )

    # Playground test results
    op.add_column(
        "tools",
        sa.Column("test_status", sa.String(20), server_default="untested", nullable=False),
    )
    op.add_column(
        "tools",
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tools",
        sa.Column("test_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Indexes for category browsing
    op.create_index(
        "ix_tools_category",
        "tools",
        ["category"],
        postgresql_where=sa.text("category IS NOT NULL"),
    )
    op.create_index(
        "ix_tools_builtin_category",
        "tools",
        ["category", "tool_type"],
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Remove catalog and playground columns from tools table."""
    op.drop_index("ix_tools_builtin_category", table_name="tools")
    op.drop_index("ix_tools_category", table_name="tools")
    op.drop_column("tools", "test_detail")
    op.drop_column("tools", "last_tested_at")
    op.drop_column("tools", "test_status")
    op.drop_column("tools", "input_schema")
    op.drop_column("tools", "required_keys")
    op.drop_column("tools", "langchain_class")
    op.drop_column("tools", "category")
