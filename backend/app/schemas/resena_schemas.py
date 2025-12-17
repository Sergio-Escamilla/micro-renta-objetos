from marshmallow import Schema, fields, validate


class ResenaCreateSchema(Schema):
	estrellas = fields.Integer(
		required=True,
		validate=validate.Range(min=1, max=5, error="El rating debe estar entre 1 y 5."),
	)
	comentario = fields.String(
		required=False,
		allow_none=True,
		validate=validate.Length(max=300, error="El comentario no puede exceder 300 caracteres."),
	)

