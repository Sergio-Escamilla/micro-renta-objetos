from app.extensions import db

class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)

    articulos = db.relationship(
        "Articulo",
        back_populates="categoria"
    )
