from datetime import datetime

from app.extensions import db


class Notificacion(db.Model):
	__tablename__ = "notificaciones"

	id = db.Column(db.Integer, primary_key=True, autoincrement=True)
	id_usuario = db.Column(
		db.Integer,
		db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
		nullable=False,
		index=True,
	)

	tipo = db.Column(db.String(60), nullable=False)
	mensaje = db.Column(db.String(300), nullable=False)
	leida = db.Column(db.Boolean, default=False, nullable=False, index=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
	meta_json = db.Column(db.Text, nullable=True)

	usuario = db.relationship("Usuario", lazy="joined")

	def __repr__(self) -> str:
		return f"<Notificacion id={self.id} usuario={self.id_usuario} tipo={self.tipo} leida={self.leida}>"
