"""add puntos entrega

Revision ID: 20251217_0007
Revises: 20251217_0006
Create Date: 2025-12-17

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20251217_0007"
down_revision = "20251217_0006"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "puntos_entrega" not in tables:
        op.create_table(
            "puntos_entrega",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("nombre", sa.String(length=120), nullable=False),
            sa.Column("direccion", sa.Text(), nullable=True),
            sa.Column("activo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
        op.create_index("ix_puntos_entrega_activo", "puntos_entrega", ["activo"], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "puntos_entrega" in tables:
        try:
            op.drop_index("ix_puntos_entrega_activo", table_name="puntos_entrega")
        except Exception:
            pass
        op.drop_table("puntos_entrega")
