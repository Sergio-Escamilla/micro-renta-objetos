"""add resenas and incidentes_renta

Revision ID: 20251215_0001
Revises: 
Create Date: 2025-12-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251215_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # Tabla existente en algunos esquemas. Si no existe, la creamos con el mismo layout.
    if "resenas" not in tables:
        op.create_table(
            "resenas",
            sa.Column("id_resenas", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_renta", sa.Integer(), nullable=False),
            sa.Column("id_revisor", sa.Integer(), nullable=False),
            sa.Column("id_usuario_resenado", sa.Integer(), nullable=False),
            sa.Column("calificacion", sa.Integer(), nullable=False),
            sa.Column("comentario", sa.String(length=300), nullable=True),
            sa.Column("tipo_resena", sa.String(length=50), nullable=True),
            sa.Column("fecha_resena", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["id_renta"], ["rentas.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["id_revisor"], ["usuarios.id_usuario"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["id_usuario_resenado"], ["usuarios.id_usuario"], ondelete="RESTRICT"),
        )

    if "incidentes_renta" not in tables:
        op.create_table(
            "incidentes_renta",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id_renta", sa.Integer(), nullable=False),
            sa.Column("descripcion", sa.Text(), nullable=False),
            sa.Column("decision", sa.String(length=30), nullable=True),
            sa.Column("monto_retenido", sa.Numeric(10, 2), nullable=True),
            sa.Column("nota", sa.String(length=300), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["id_renta"], ["rentas.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("id_renta", name="uq_incidentes_renta_id_renta"),
        )
        op.create_index("ix_incidentes_renta_id_renta", "incidentes_renta", ["id_renta"], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "incidentes_renta" in tables:
        try:
            op.drop_index("ix_incidentes_renta_id_renta", table_name="incidentes_renta")
        except Exception:
            pass
        op.drop_table("incidentes_renta")

    # No eliminamos `resenas` en downgrade porque puede ser una tabla pre-existente del esquema.
