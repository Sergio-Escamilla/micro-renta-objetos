from marshmallow import fields, validates_schema, ValidationError, validate

from app.extensions.ma import ma


class RentaCreateSchema(ma.Schema):
    """
    Datos necesarios para solicitar una renta.
    El precio total y el depósito se calculan en el servicio
    a partir del artículo y el rango de fechas.
    """

    id_articulo = fields.Integer(required=True)
    fecha_inicio = fields.DateTime(required=True)  # ISO 8601
    fecha_fin = fields.DateTime(required=True)
    modalidad = fields.String(
        required=False,
        load_default=None,
        validate=validate.OneOf(["horas", "dias"]),
    )

    @validates_schema
    def validar_fechas(self, data, **kwargs):
        inicio = data.get("fecha_inicio")
        fin = data.get("fecha_fin")
        if inicio and fin and fin <= inicio:
            raise ValidationError(
                "La fecha_fin debe ser mayor que fecha_inicio",
                field_name="fecha_fin",
            )
