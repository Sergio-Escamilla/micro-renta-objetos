from app.extensions import db


class Rol(db.Model):
    __tablename__ = "roles"

    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    usuarios = db.relationship(
        "UsuarioRol",
        back_populates="rol",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Rol id_rol={self.id_rol} nombre={self.nombre}>"
