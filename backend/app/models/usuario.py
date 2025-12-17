from app.extensions import db
from sqlalchemy import func


class Usuario(db.Model):
    __tablename__ = "usuarios"

    # ✅ PK como en tu BD
    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)

    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    correo_electronico = db.Column(db.String(255), unique=True, nullable=False)
    hash_contrasena = db.Column(db.String(255), nullable=False)

    telefono = db.Column(db.String(20))
    ciudad = db.Column(db.String(100))
    estado = db.Column(db.String(100))
    pais = db.Column(db.String(100), default="México")
    direccion_completa = db.Column(db.Text)
    foto_perfil = db.Column(db.String(500))

    fecha_registro = db.Column(
        db.TIMESTAMP,
        server_default=func.current_timestamp()
    )

    estado_cuenta = db.Column(
        db.Enum("activo", "suspendido", "eliminado", name="estado_cuenta_enum"),
        default="activo",
    )

    verificado = db.Column(db.Boolean, default=False)

    # Compatibilidad: en la BD real existe `usuarios.verificado`.
    # No dependemos de columnas adicionales (email_verificado/token/sent_at), porque podrían no existir.
    @property
    def email_verificado(self) -> bool:
        return bool(self.verificado)

    @email_verificado.setter
    def email_verificado(self, value: bool) -> None:
        self.verificado = bool(value)

    ultima_conexion = db.Column(db.TIMESTAMP)

    roles = db.relationship(
        "UsuarioRol",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"
