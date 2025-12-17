from app.extensions import db


class Articulo(db.Model):
    __tablename__ = "articulos"

    # ✅ PK real en BD
    id_articulo = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ✅ FK real en BD: articulos.id_dueno -> usuarios.id_usuario
    id_dueno = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )

    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    id_categoria = db.Column(
        db.Integer,
        db.ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ✅ Esquema real MySQL
    precio_base = db.Column(db.Numeric(10, 2), nullable=False)
    unidad_precio = db.Column(
        db.Enum("por_hora", "por_dia", "por_semana", name="unidad_precio_enum"),
        default="por_dia",
    )

    monto_deposito = db.Column(db.Numeric(10, 2), nullable=True)
    ubicacion_texto = db.Column(db.String(255), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)

    estado = db.Column(db.String(100), nullable=True)
    estado_publicacion = db.Column(
        db.Enum("borrador", "publicado", "pausado", "eliminado", name="estado_publicacion_enum"),
        default="borrador",
    )

    es_destacado = db.Column(db.Boolean, default=False)
    vistas = db.Column(db.Integer, default=0)

    fecha_creacion = db.Column(db.TIMESTAMP, nullable=True)
    fecha_actualizacion = db.Column(db.TIMESTAMP, nullable=True)

    # Relaciones
    categoria = db.relationship("Categoria", back_populates="articulos")

    dueno = db.relationship(
        "Usuario",
        foreign_keys=[id_dueno],
        lazy="joined",
    )

    imagenes = db.relationship(
        "ArticuloImagen",
        back_populates="articulo",
        cascade="all, delete-orphan",
    )

    disponibilidades = db.relationship(
        "DisponibilidadArticulo",
        back_populates="articulo",
        cascade="all, delete-orphan",
    )

    # --- Compat (NO columnas) ---
    # Tu BD real solo soporta 1 precio + 1 unidad por artículo.
    # Exponemos propiedades calculadas para no romper frontend/servicios legacy.

    @property
    def precio_renta_hora(self):
        if self.unidad_precio == "por_hora":
            return self.precio_base
        return None

    @precio_renta_hora.setter
    def precio_renta_hora(self, value):
        if value is None:
            return
        self.unidad_precio = "por_hora"
        self.precio_base = value

    @property
    def precio_renta_dia(self):
        if self.unidad_precio == "por_dia":
            return self.precio_base
        return None

    @precio_renta_dia.setter
    def precio_renta_dia(self, value):
        if value is None:
            return
        self.unidad_precio = "por_dia"
        self.precio_base = value

    @property
    def tarifa_por_hora(self):
        return self.precio_renta_hora

    @tarifa_por_hora.setter
    def tarifa_por_hora(self, value):
        self.precio_renta_hora = value

    @property
    def tarifa_por_dia(self):
        return self.precio_renta_dia

    @tarifa_por_dia.setter
    def tarifa_por_dia(self, value):
        self.precio_renta_dia = value

    # --- Backwards compatibility para código que todavía use "propietario" ---
    @property
    def id_propietario(self):
        return self.id_dueno

    @id_propietario.setter
    def id_propietario(self, value):
        self.id_dueno = value

    @property
    def propietario(self):
        return self.dueno

