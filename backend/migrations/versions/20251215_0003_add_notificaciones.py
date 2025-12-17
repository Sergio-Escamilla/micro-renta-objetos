"""add notificaciones

Revision ID: 20251215_0003
Revises: 20251215_0002
Create Date: 2025-12-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20251215_0003"
down_revision = "20251215_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "notificaciones" not in tables:
        op.create_table(
            "notificaciones",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_usuario", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(length=60), nullable=False),
            sa.Column("mensaje", sa.String(length=300), nullable=False),
            sa.Column("leida", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"], ondelete="RESTRICT"),
        )
        op.create_index("ix_notificaciones_id_usuario", "notificaciones", ["id_usuario"], unique=False)
        op.create_index("ix_notificaciones_leida", "notificaciones", ["leida"], unique=False)
        op.create_index("ix_notificaciones_created_at", "notificaciones", ["created_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "notificaciones" in tables:
        try:
            op.drop_index("ix_notificaciones_created_at", table_name="notificaciones")
        except Exception:
            pass
        try:
            op.drop_index("ix_notificaciones_leida", table_name="notificaciones")
        except Exception:
            pass
        try:
            op.drop_index("ix_notificaciones_id_usuario", table_name="notificaciones")
        except Exception:
            pass
        op.drop_table("notificaciones")
