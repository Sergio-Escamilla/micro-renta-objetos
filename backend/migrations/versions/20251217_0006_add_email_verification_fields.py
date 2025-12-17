"""add email verification fields

Revision ID: 20251217_0006
Revises: 20251217_0005
Create Date: 2025-12-17

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20251217_0006"
down_revision = "20251217_0005"
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

	if "usuarios" not in tables:
		return

	if not _has_column(insp, "usuarios", "email_verificado"):
		op.add_column("usuarios", sa.Column("email_verificado", sa.Boolean(), nullable=False, server_default=sa.text("0")))
		# quitar default server para no dejarlo permanente
		try:
			op.alter_column("usuarios", "email_verificado", server_default=None)
		except Exception:
			pass

	if not _has_column(insp, "usuarios", "email_verification_token"):
		op.add_column("usuarios", sa.Column("email_verification_token", sa.String(length=255), nullable=True))

	if not _has_column(insp, "usuarios", "email_verification_sent_at"):
		op.add_column("usuarios", sa.Column("email_verification_sent_at", sa.TIMESTAMP(), nullable=True))

	# best-effort: si existe `verificado`, copiar valor inicial a `email_verificado`
	try:
		if _has_column(insp, "usuarios", "verificado") and _has_column(insp, "usuarios", "email_verificado"):
			op.execute("UPDATE usuarios SET email_verificado = COALESCE(email_verificado, verificado)")
	except Exception:
		pass


def downgrade():
	bind = op.get_bind()
	insp = inspect(bind)
	tables = set(insp.get_table_names())

	if "usuarios" not in tables:
		return

	if _has_column(insp, "usuarios", "email_verification_sent_at"):
		try:
			op.drop_column("usuarios", "email_verification_sent_at")
		except Exception:
			pass

	if _has_column(insp, "usuarios", "email_verification_token"):
		try:
			op.drop_column("usuarios", "email_verification_token")
		except Exception:
			pass

	if _has_column(insp, "usuarios", "email_verificado"):
		try:
			op.drop_column("usuarios", "email_verificado")
		except Exception:
			pass
