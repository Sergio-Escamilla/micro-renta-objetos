from datetime import datetime

from app.extensions import db


class MensajeRenta(db.Model):
    __tablename__ = "mensajes_renta"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_renta = db.Column(
        db.Integer,
        db.ForeignKey("rentas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    id_emisor = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    mensaje = db.Column(db.String(240), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    renta = db.relationship("Renta", lazy="joined")
    emisor = db.relationship("Usuario", lazy="joined")

    def __repr__(self) -> str:
        return f"<MensajeRenta id={self.id} renta={self.id_renta} emisor={self.id_emisor}>"
