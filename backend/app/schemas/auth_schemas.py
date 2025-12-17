from marshmallow import fields, validates, ValidationError
from app.extensions import ma


class RegistroSchema(ma.Schema):
    nombre = fields.String(required=True)
    apellidos = fields.String(required=True)
    correo_electronico = fields.Email(required=True)
    contrasena = fields.String(required=True, load_only=True)
    telefono = fields.String(required=False, allow_none=True)
    ciudad = fields.String(required=False, allow_none=True)
    estado = fields.String(required=False, allow_none=True)
    pais = fields.String(required=False, allow_none=True)
    direccion_completa = fields.String(required=False, allow_none=True)

    @validates("contrasena")
    def validate_password(self, value):
        if len(value) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres.")


class LoginSchema(ma.Schema):
    correo_electronico = fields.Email(required=True)
    contrasena = fields.String(required=True, load_only=True)
