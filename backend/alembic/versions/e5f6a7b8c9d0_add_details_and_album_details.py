"""add details and album_details

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_details_name", "details", ["name"])

    op.create_table(
        "album_details",
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("detail_id", sa.Integer(), nullable=False),
        sa.Column("detail_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["detail_id"], ["details.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("album_id", "detail_id", "detail_type"),
    )


def downgrade() -> None:
    op.drop_table("album_details")
    op.drop_index("ix_details_name", table_name="details")
    op.drop_table("details")
