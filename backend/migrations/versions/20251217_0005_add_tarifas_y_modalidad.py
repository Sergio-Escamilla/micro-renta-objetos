"""add tarifas por hora/dia y modalidad en renta

Revision ID: 20251217_0005
Revises: 20251215_0004
Create Date: 2025-12-17

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20251217_0005"
down_revision = "20251215_0004"
branch_labels = None
depends_on = None


def _has_column(insp, table: str, col: str) -> bool:
    try:
        cols = insp.get_columns(table)
    except Exception:
        return False
    return any(c.get("name") == col for c in cols)


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "articulos" in tables:
        if not _has_column(insp, "articulos", "tarifa_por_hora"):
            op.add_column("articulos", sa.Column("tarifa_por_hora", sa.Numeric(10, 2), nullable=True))
        if not _has_column(insp, "articulos", "tarifa_por_dia"):
            op.add_column("articulos", sa.Column("tarifa_por_dia", sa.Numeric(10, 2), nullable=True))

    if "rentas" in tables:
        if not _has_column(insp, "rentas", "modalidad"):
            op.add_column("rentas", sa.Column("modalidad", sa.String(length=10), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "rentas" in tables and _has_column(insp, "rentas", "modalidad"):
        try:
            op.drop_column("rentas", "modalidad")
        except Exception:
            pass

    if "articulos" in tables and _has_column(insp, "articulos", "tarifa_por_dia"):
        try:
            op.drop_column("articulos", "tarifa_por_dia")
        except Exception:
            pass

    if "articulos" in tables and _has_column(insp, "articulos", "tarifa_por_hora"):
        try:
            op.drop_column("articulos", "tarifa_por_hora")
        except Exception:
            pass
