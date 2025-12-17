from app.extensions import db


class IncidenteRenta(db.Model):
    __tablename__ = "incidentes_renta"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    id_renta = db.Column(
        db.Integer,
        db.ForeignKey("rentas.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    descripcion = db.Column(db.Text, nullable=False)

    # decision: liberar | retener_parcial | retener_total
    decision = db.Column(db.String(30), nullable=True)
    monto_retenido = db.Column(db.Numeric(10, 2), nullable=True)
    nota = db.Column(db.String(300), nullable=True)

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=True,
    )

    resolved_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_incidentes_renta_id_renta", "id_renta"),
    )
