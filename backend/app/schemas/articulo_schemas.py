from marshmallow import fields, validates, validates_schema, ValidationError
from app.extensions import ma

from app.models.articulo import Articulo
from app.models.articulo_imagen import ArticuloImagen


class ArticuloImagenSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ArticuloImagen
        load_instance = True
        include_fk = True

    id = ma.auto_field()
    url_imagen = ma.auto_field()
    es_principal = ma.auto_field()
    orden = ma.auto_field()


class ArticuloListadoSchema(ma.SQLAlchemyAutoSchema):
    """
    Esquema pensado para el listado de artículos.
    Incluye campos principales, propietario simplificado e imagen principal.
    """

    class Meta:
        model = Articulo
        load_instance = True
        include_fk = True
        exclude = (
            "descripcion",
            "id_articulo",
        )

    # ✅ Tu API devuelve "id" pero internamente lee Articulo.id_articulo
    id = fields.Integer(attribute="id_articulo")

    titulo = ma.auto_field()

    precio_base = fields.Method("get_precio_base")
    unidad_precio = fields.String()

    # Compatibilidad con el frontend
    precio_renta_dia = fields.Method("get_precio_renta_dia")
    precio_renta_hora = fields.Method("get_precio_renta_hora")
    tarifa_por_dia = fields.Method("get_precio_renta_dia")
    tarifa_por_hora = fields.Method("get_precio_renta_hora")
    deposito_garantia = fields.Float(attribute="monto_deposito")

    propietario_nombre = fields.Method("get_propietario_nombre")
    propietario_correo = fields.Method("get_propietario_correo")

    imagen_principal_url = fields.Method("get_imagen_principal")

    def get_propietario_nombre(self, obj):
        if getattr(obj, "propietario", None):
            return f"{obj.propietario.nombre} {obj.propietario.apellidos}"
        return None

    def get_propietario_correo(self, obj):
        return obj.propietario.correo_electronico if getattr(obj, "propietario", None) else None

    def get_precio_base(self, obj):
        try:
            return float(getattr(obj, "precio_base", 0) or 0)
        except Exception:
            return 0.0

    def get_precio_renta_dia(self, obj):
        # Compat: BD real solo tiene precio_base + unidad_precio.
        if getattr(obj, "unidad_precio", None) != "por_dia":
            return None
        try:
            return float(getattr(obj, "precio_base", None))
        except Exception:
            return None

    def get_precio_renta_hora(self, obj):
        if getattr(obj, "unidad_precio", None) != "por_hora":
            return None
        try:
            return float(getattr(obj, "precio_base", None))
        except Exception:
            return None

    def get_imagen_principal(self, obj):
        imagenes = getattr(obj, "imagenes", None)
        if not imagenes:
            return None
        principal = next((img for img in imagenes if img.es_principal), imagenes[0])
        return principal.url_imagen


class ArticuloCreateSchema(ma.Schema):
    titulo = fields.String(required=True)
    descripcion = fields.String(required=True)
    id_categoria = fields.Integer(required=True)
    precio_renta_dia = fields.Float(required=False, allow_none=True)
    precio_renta_hora = fields.Float(required=False, allow_none=True)
    unidad_precio = fields.String(required=False, allow_none=True)
    deposito_garantia = fields.Float(required=False, allow_none=True)
    ubicacion_texto = fields.String(required=False, allow_none=True)
    urls_imagenes = fields.List(fields.String(), required=False)

    @validates("urls_imagenes")
    def validate_urls(self, value):
        if value is None:
            return
        if len(value) < 1:
            raise ValidationError("Debes enviar al menos una URL de imagen.")

    @validates("unidad_precio")
    def validate_unidad_precio(self, value):
        if value is None:
            return
        if value not in ("por_hora", "por_dia", "por_semana"):
            raise ValidationError("unidad_precio inválida. Usa: por_hora, por_dia, por_semana")

    @validates_schema
    def validate_tarifas(self, data, **kwargs):
        dia = data.get("precio_renta_dia")
        hora = data.get("precio_renta_hora")
        if (dia is None or float(dia) <= 0) and (hora is None or float(hora) <= 0):
            raise ValidationError("Debes indicar un precio por día y/o por hora.")


class ArticuloDetalleSchema(ArticuloListadoSchema):
    """
    Esquema para detalle.
    Mantiene compatibilidad (id) y agrega campos extra sin romper el listado.
    """

    class Meta(ArticuloListadoSchema.Meta):
        # En el listado excluimos la descripción para ahorrar payload, pero en detalle sí se requiere.
        exclude = (
            "id_articulo",
        )

    id_articulo = fields.Integer(attribute="id_articulo")
    descripcion = fields.String()
    ubicacion_texto = fields.String(allow_none=True)
    id_propietario = fields.Integer(attribute="id_propietario")

    imagenes = fields.Method("get_imagenes")

    def get_imagenes(self, obj):
        imagenes = getattr(obj, "imagenes", None)
        if not imagenes:
            return []
        # Ordenar por 'orden' cuando exista
        ordered = sorted(
            imagenes,
            key=lambda i: (i.orden if i.orden is not None else 10**9),
        )
        return [
            {
                "id": img.id,
                "url_imagen": img.url_imagen,
                "es_principal": bool(img.es_principal),
                "orden": img.orden,
            }
            for img in ordered
        ]


class ArticuloUpdateSchema(ma.Schema):
    titulo = fields.String(required=False)
    descripcion = fields.String(required=False)
    precio_renta_dia = fields.Float(required=False, allow_none=True)
    precio_renta_hora = fields.Float(required=False, allow_none=True)
    unidad_precio = fields.String(required=False, allow_none=True)
    deposito_garantia = fields.Float(required=False, allow_none=True)
    estado_publicacion = fields.String(required=False, allow_none=True)

    @validates("estado_publicacion")
    def validate_estado_publicacion(self, value):
        if value is None:
            return
        if value not in ("publicado", "pausado"):
            raise ValidationError("estado_publicacion inválido. Usa: publicado, pausado")

    @validates("unidad_precio")
    def validate_unidad_precio(self, value):
        if value is None:
            return
        if value not in ("por_hora", "por_dia", "por_semana"):
            raise ValidationError("unidad_precio inválida. Usa: por_hora, por_dia, por_semana")

    @validates_schema
    def validate_tarifas(self, data, **kwargs):
        # Si el payload toca tarifas, exigir al menos una modalidad activa.
        touched = ("precio_renta_dia" in data) or ("precio_renta_hora" in data)
        if not touched:
            return

        dia = data.get("precio_renta_dia")
        hora = data.get("precio_renta_hora")

        dia_ok = (dia is not None) and (float(dia) > 0)
        hora_ok = (hora is not None) and (float(hora) > 0)
        if not dia_ok and not hora_ok:
            raise ValidationError("Debes indicar un precio por día y/o por hora.")
