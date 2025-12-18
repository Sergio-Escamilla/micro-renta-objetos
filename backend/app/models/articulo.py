from app.extensions import db


class Articulo(db.Model):
    __tablename__ = "articulos"

    # =========================
    # Columnas reales en MySQL
    # =========================

    id_articulo = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # FK real en BD
    id_dueno = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    id_categoria = db.Column(
        db.Integer,
        db.ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    # Precios reales (BD)
    precio_por_hora = db.Column(db.Numeric(10, 2), nullable=True)
    precio_por_dia = db.Column(db.Numeric(10, 2), nullable=False)
    precio_por_semana = db.Column(db.Numeric(10, 2), nullable=True)

    deposito = db.Column(db.Numeric(10, 2), nullable=False)

    ubicacion = db.Column(db.String(255), nullable=False)

    estado = db.Column(
        db.Enum("borrador", "publicado", "pausado", "eliminado"),
        default="borrador",
    )

    destacado = db.Column(db.Boolean, default=False)

    politica_uso = db.Column(db.Text, nullable=True)

    rating_promedio = db.Column(db.Numeric(3, 2), default=0)
    total_resenas = db.Column(db.Integer, default=0)

    creado_en = db.Column(db.DateTime)
    actualizado_en = db.Column(db.DateTime)

    # =========================
    # Relaciones
    # =========================

    dueno = db.relationship(
        "Usuario",
        foreign_keys=[id_dueno],
        lazy="joined",
    )

    categoria = db.relationship(
        "Categoria",
        back_populates="articulos",
    )

    imagenes = db.relationship(
        "ArticuloImagen",
        back_populates="articulo",
        cascade="all, delete-orphan",
    )

    # ✅ IMPORTANTE: esto evita el crash del mapper
    disponibilidades = db.relationship(
        "DisponibilidadArticulo",
        back_populates="articulo",
        cascade="all, delete-orphan",
    )

    # =========================
    # Compatibilidad (NO columnas)
    # =========================

    @property
    def id_propietario(self):
        return self.id_dueno

    @property
    def monto_deposito(self):
        return self.deposito

    @property
    def ubicacion_texto(self):
        return self.ubicacion

    @property
    def estado_publicacion(self):
        return self.estado

    @property
    def es_destacado(self):
        return self.destacado

    @property
    def fecha_creacion(self):
        return self.creado_en

    @property
    def fecha_actualizacion(self):
        return self.actualizado_en
