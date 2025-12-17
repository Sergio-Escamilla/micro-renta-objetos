from app.extensions import db


class Resena(db.Model):
	"""Mapeo a la tabla existente `resenas` (sin cambiar esquema)."""

	__tablename__ = "resenas"

	id_resenas = db.Column(db.Integer, primary_key=True, autoincrement=True)

	id_renta = db.Column(
		db.Integer,
		db.ForeignKey("rentas.id", ondelete="RESTRICT"),
		nullable=False,
	)

	# En la BD real estos campos existen con estos nombres
	id_revisor = db.Column(
		db.Integer,
		db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
		nullable=False,
	)

	id_usuario_resenado = db.Column(
		db.Integer,
		db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
		nullable=False,
	)

	calificacion = db.Column(db.Integer, nullable=False)
	comentario = db.Column(db.String(300), nullable=True)

	# Campo extra existente en BD (lo dejamos tal cual)
	tipo_resena = db.Column(db.String(50), nullable=True)

	fecha_resena = db.Column(db.DateTime, nullable=True)

