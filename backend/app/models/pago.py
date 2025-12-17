from app.extensions import db


class Pago(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)

    # Relación con renta
    id_renta = db.Column(
        db.Integer,
        db.ForeignKey("rentas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Montos (según tu DDL: decimal(10,2))
    monto_renta = db.Column(db.Numeric(10, 2), nullable=False)
    monto_deposito = db.Column(db.Numeric(10, 2), nullable=False)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)

    # Método de pago (tarjeta, etc.)
    metodo_pago = db.Column(db.String(50), default="tarjeta")

    # Estado del pago (en la BD es un ENUM, aquí lo manejamos como string)
    # valores posibles en tu SQL: 'pendiente','procesando','confirmado',
    # 'fallido','reembolsado_parcial','reembolsado_total'
    estado_pago = db.Column(db.String(50), default="pendiente")

    # Info adicional
    referencia_transaccion = db.Column(db.String(255), nullable=True)
    detalles_pago = db.Column(db.JSON, nullable=True)

    # Fechas
    fecha_pago = db.Column(db.DateTime, nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, nullable=True)

    # Nota: más adelante podemos agregar relación con Renta:
    # renta = db.relationship("Renta", back_populates="pagos")
    # pero por ahora lo dejamos solo con el FK para evitar más cambios.
