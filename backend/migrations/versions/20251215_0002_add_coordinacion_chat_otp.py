"""add coordinacion, chat y otp

Revision ID: 20251215_0002
Revises: 20251215_0001
Create Date: 2025-12-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251215_0002"
down_revision = "20251215_0001"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column, existing_cols: set[str]) -> None:
    if column.name in existing_cols:
        return
    op.add_column(table, column)


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    tables = set(insp.get_table_names())

    # Extender `rentas` solo si existe (en este proyecto siempre existe)
    if "rentas" in tables:
        cols = {c["name"] for c in insp.get_columns("rentas")}

        _add_column_if_missing("rentas", sa.Column("modo_entrega", sa.String(length=20), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("zona_publica", sa.String(length=120), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("direccion_entrega", sa.Text(), nullable=True), cols)

        _add_column_if_missing("rentas", sa.Column("ventanas_entrega_propuestas", sa.Text(), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("ventana_entrega_elegida", sa.String(length=120), nullable=True), cols)

        _add_column_if_missing("rentas", sa.Column("ventanas_devolucion_propuestas", sa.Text(), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("ventana_devolucion_elegida", sa.String(length=120), nullable=True), cols)

        _add_column_if_missing("rentas", sa.Column("coordinacion_confirmada", sa.Boolean(), server_default=sa.text("0"), nullable=True), cols)

        _add_column_if_missing("rentas", sa.Column("codigo_entrega", sa.String(length=6), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("codigo_devolucion", sa.String(length=6), nullable=True), cols)

        _add_column_if_missing("rentas", sa.Column("checklist_entrega", sa.Text(), nullable=True), cols)
        _add_column_if_missing("rentas", sa.Column("checklist_devolucion", sa.Text(), nullable=True), cols)

    if "mensajes_renta" not in tables:
        op.create_table(
            "mensajes_renta",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_renta", sa.Integer(), nullable=False),
            sa.Column("id_emisor", sa.Integer(), nullable=False),
            sa.Column("mensaje", sa.String(length=240), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["id_renta"], ["rentas.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["id_emisor"], ["usuarios.id_usuario"], ondelete="RESTRICT"),
        )
        op.create_index("ix_mensajes_renta_id_renta", "mensajes_renta", ["id_renta"], unique=False)
        op.create_index("ix_mensajes_renta_created_at", "mensajes_renta", ["created_at"], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "mensajes_renta" in tables:
        try:
            op.drop_index("ix_mensajes_renta_created_at", table_name="mensajes_renta")
        except Exception:
            pass
        try:
            op.drop_index("ix_mensajes_renta_id_renta", table_name="mensajes_renta")
        except Exception:
            pass
        op.drop_table("mensajes_renta")

    # No removemos columnas de `rentas` en downgrade: podrían existir previamente.
