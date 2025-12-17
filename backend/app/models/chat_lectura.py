from datetime import datetime

from app.extensions import db


class ChatLectura(db.Model):
    __tablename__ = "chat_lecturas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    id_renta = db.Column(
        db.Integer,
        db.ForeignKey("rentas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    last_read_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("id_renta", "id_usuario", name="uq_chat_lecturas_renta_usuario"),
    )
