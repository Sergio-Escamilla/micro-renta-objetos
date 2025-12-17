# backend/app/models/incidente.py

from app.extensions import db


class Incidente(db.Model):
    __tablename__ = "incidentes"

    id = db.Column(db.Integer, primary_key=True)

    # FK a renta
    id_renta = db.Column(
        db.Integer,
        db.ForeignKey("rentas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # FK a usuario que reporta
    reportado_por = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    # ENUM tipo_incidente
    tipo_incidente = db.Column(
        db.Enum(
            "dano_menor",
            "dano_mayor",
            "perdida",
            "robo",
            "incumplimiento",
            "otro",
            name="tipo_incidente_enum",
        ),
        nullable=False,
    )

    descripcion = db.Column(db.Text, nullable=False)

    # JSON con URLs o datos de fotos
    evidencia_fotos = db.Column(db.JSON, nullable=True)

    fecha_reporte = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=True,
    )

    estado_incidente = db.Column(
        db.Enum(
            "abierto",
            "en_revision",
            "resuelto",
            "deposito_retenido_parcial",
            "deposito_retenido_total",
            "cerrado",
            name="estado_incidente_enum",
        ),
        server_default="abierto",
        nullable=True,
    )

    monto_retencion = db.Column(
        db.Numeric(10, 2),
        server_default="0.00",
        nullable=True,
    )

    resolucion = db.Column(db.Text, nullable=True)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    # Por ahora NO definimos relationships para evitar más errores
    # (si luego quieres, las agregamos en Renta y Usuario).
