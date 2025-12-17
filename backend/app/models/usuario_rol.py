from app.extensions import db
from sqlalchemy import func


class UsuarioRol(db.Model):
    __tablename__ = "usuarios_roles"

    # 🔑 PK compuesta (tal como está en la BD)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        primary_key=True,
    )

    id_rol = db.Column(
        db.Integer,
        db.ForeignKey("roles.id_rol", ondelete="CASCADE"),
        primary_key=True,
    )

    asignado_en = db.Column(
        db.TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="roles",
    )

    rol = db.relationship(
        "Rol",
        back_populates="usuarios",
    )
