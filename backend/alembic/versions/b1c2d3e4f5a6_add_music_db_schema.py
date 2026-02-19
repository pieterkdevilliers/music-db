"""add music db schema

Revision ID: b1c2d3e4f5a6
Revises: 220cd69694ba
Create Date: 2026-02-19 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "220cd69694ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "record_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "musicians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_musicians_name", "musicians", ["name"], unique=True)

    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("artist", sa.String(), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("producer", sa.String(), nullable=True),
        sa.Column("record_label_id", sa.Integer(), nullable=True),
        sa.Column("tracks", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["record_label_id"],
            ["record_labels.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_collection_user_name"),
    )

    op.create_table(
        "album_musicians",
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("musician_id", sa.Integer(), nullable=False),
        sa.Column("instrument", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["musician_id"], ["musicians.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("album_id", "musician_id", "instrument"),
    )

    op.create_table(
        "collection_albums",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["album_id"], ["albums.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("collection_id", "album_id"),
    )


def downgrade() -> None:
    op.drop_table("collection_albums")
    op.drop_table("album_musicians")
    op.drop_table("collections")
    op.drop_table("albums")
    op.drop_index("ix_musicians_name", table_name="musicians")
    op.drop_table("musicians")
    op.drop_table("record_labels")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
