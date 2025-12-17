"""add chat_lecturas

Revision ID: 20251215_0004
Revises: 20251215_0003
Create Date: 2025-12-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20251215_0004"
down_revision = "20251215_0003"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "chat_lecturas" not in tables:
        op.create_table(
            "chat_lecturas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_renta", sa.Integer(), nullable=False),
            sa.Column("id_usuario", sa.Integer(), nullable=False),
            sa.Column(
                "last_read_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["id_renta"], ["rentas.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["id_usuario"], ["usuarios.id_usuario"], ondelete="RESTRICT"),
            sa.UniqueConstraint("id_renta", "id_usuario", name="uq_chat_lecturas_renta_usuario"),
        )
        op.create_index("ix_chat_lecturas_id_renta", "chat_lecturas", ["id_renta"], unique=False)
        op.create_index("ix_chat_lecturas_id_usuario", "chat_lecturas", ["id_usuario"], unique=False)
        op.create_index("ix_chat_lecturas_last_read_at", "chat_lecturas", ["last_read_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "chat_lecturas" in tables:
        try:
            op.drop_index("ix_chat_lecturas_last_read_at", table_name="chat_lecturas")
        except Exception:
            pass
        try:
            op.drop_index("ix_chat_lecturas_id_usuario", table_name="chat_lecturas")
        except Exception:
            pass
        try:
            op.drop_index("ix_chat_lecturas_id_renta", table_name="chat_lecturas")
        except Exception:
            pass
        op.drop_table("chat_lecturas")
