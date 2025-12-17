from datetime import datetime

from app.extensions import db


class Renta(db.Model):
    __tablename__ = "rentas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ✅ FK a articulos.id_articulo (tu BD usa id_articulo)
    id_articulo = db.Column(
        db.Integer,
        db.ForeignKey("articulos.id_articulo", ondelete="RESTRICT"),
        nullable=False,
    )

    # ✅ FK a usuarios.id_usuario (ajusta si tu tabla realmente usa "id")
    id_arrendatario = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    # ✅ FK a usuarios.id_usuario (propietario del artículo)
    id_propietario = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)

    # Compatibilidad con BD real: NO mapear modalidad si la columna no existe.
    # Exponemos 'modalidad' como propiedad calculada (horas|dias).

    @property
    def modalidad(self) -> str | None:
        art = getattr(self, "articulo", None)
        unidad = getattr(art, "unidad_precio", None) if art is not None else None
        if unidad == "por_hora":
            return "horas"
        if unidad == "por_dia":
            return "dias"
        return None

    precio_total_renta = db.Column(db.Numeric(10, 2), nullable=False)
    monto_deposito = db.Column(db.Numeric(10, 2), nullable=False)

    # Enum en BD: 'pendiente_pago','pagada','confirmada','en_curso',
    # 'completada','cancelada','con_incidente'
    estado_renta = db.Column(
        db.String(50),
        nullable=False,
        default="pendiente_pago",
    )

    entregado = db.Column(db.Boolean, default=False)
    fecha_entrega = db.Column(db.DateTime, nullable=True)

    devuelto = db.Column(db.Boolean, default=False)
    fecha_devolucion = db.Column(db.DateTime, nullable=True)

    deposito_liberado = db.Column(db.Boolean, default=False)
    fecha_liberacion_deposito = db.Column(db.DateTime, nullable=True)

    notas_entrega = db.Column(db.Text, nullable=True)
    notas_devolucion = db.Column(db.Text, nullable=True)

    # Coordinación de entrega/devolución (MVP realista)
    modo_entrega = db.Column(db.String(20), nullable=True)  # 'arrendador' (default) | 'neutral'
    zona_publica = db.Column(db.String(120), nullable=True)
    direccion_entrega = db.Column(db.Text, nullable=True)

    ventanas_entrega_propuestas = db.Column(db.Text, nullable=True)  # JSON string (list[str])
    ventana_entrega_elegida = db.Column(db.String(120), nullable=True)

    ventanas_devolucion_propuestas = db.Column(db.Text, nullable=True)  # JSON string (list[str])
    ventana_devolucion_elegida = db.Column(db.String(120), nullable=True)

    coordinacion_confirmada = db.Column(db.Boolean, default=False)

    # OTP (solo arrendatario lo ve; el dueño lo valida)
    codigo_entrega = db.Column(db.String(6), nullable=True)
    codigo_devolucion = db.Column(db.String(6), nullable=True)

    checklist_entrega = db.Column(db.Text, nullable=True)
    checklist_devolucion = db.Column(db.Text, nullable=True)

    fecha_creacion = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow,
    )
    fecha_actualizacion = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relaciones
    articulo = db.relationship("Articulo", backref="rentas", lazy="joined")
    arrendatario = db.relationship(
        "Usuario",
        foreign_keys=[id_arrendatario],
        lazy="joined",
    )
    propietario = db.relationship(
        "Usuario",
        foreign_keys=[id_propietario],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Renta id={self.id} articulo={self.id_articulo} estado={self.estado_renta}>"
