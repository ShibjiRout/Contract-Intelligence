"""0001_initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playbook_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clause_type", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "rule_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("changed_by", sa.String(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["playbook_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jurisdictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "clause_type_registry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clause_type", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clause_type"),
    )

    op.create_table(
        "rule_weights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("postgresql_weight", sa.Float(), nullable=False),
        sa.Column("qdrant_weight", sa.Float(), nullable=False),
        sa.Column("neo4j_weight", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jurisdiction"),
    )


def downgrade() -> None:
    op.drop_table("rule_weights")
    op.drop_table("clause_type_registry")
    op.drop_table("jurisdictions")
    op.drop_table("rule_versions")
    op.drop_table("playbook_rules")
