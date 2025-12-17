from app.extensions import db


class DisponibilidadArticulo(db.Model):
    __tablename__ = "disponibilidad_articulo"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ✅ FK como en tu BD: articulos.id_articulo
    id_articulo = db.Column(
        db.Integer,
        db.ForeignKey("articulos.id_articulo", ondelete="CASCADE"),
        nullable=False,
    )

    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    disponible = db.Column(db.Boolean, default=True)
    motivo = db.Column(db.String(255))

    articulo = db.relationship("Articulo", back_populates="disponibilidades")
