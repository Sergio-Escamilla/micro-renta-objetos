from app.extensions import db


class ArticuloImagen(db.Model):
    __tablename__ = "articulos_imagenes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    url_imagen = db.Column(db.String(500), nullable=False)
    es_principal = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, nullable=True)

    id_articulo = db.Column(
        db.Integer,
        db.ForeignKey("articulos.id_articulo", ondelete="CASCADE"),
        nullable=False,
    )

    articulo = db.relationship(
        "Articulo",
        back_populates="imagenes",
    )
