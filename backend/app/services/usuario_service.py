from typing import Optional
from sqlalchemy.exc import IntegrityError
from app.extensions import db, bcrypt
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.utils.errors import ApiError


def obtener_usuario_por_id(user_id: int) -> Optional[Usuario]:
    return Usuario.query.get(user_id)


def crear_usuario(data: dict) -> Usuario:
    correo = data["correo_electronico"].lower().strip()

    if Usuario.query.filter_by(correo_electronico=correo).first():
        raise ApiError("El correo ya está registrado", 400)

    hash_contrasena = bcrypt.generate_password_hash(
        data["contrasena"]
    ).decode("utf-8")

    usuario = Usuario(
        nombre=data["nombre"].strip(),
        apellidos=data["apellidos"].strip(),
        correo_electronico=correo,
        hash_contrasena=hash_contrasena,
        telefono=data.get("telefono"),
        ciudad=data.get("ciudad"),
        estado=data.get("estado"),
        pais=data.get("pais") or "México",
        direccion_completa=data.get("direccion_completa"),
    )

    db.session.add(usuario)
    db.session.flush()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Error al crear usuario", 500)

    rol_cliente = Rol.query.filter_by(nombre="CLIENTE").first()
    if not rol_cliente:
        raise ApiError("No existe el rol CLIENTE en la base de datos", 500)

    usuario_rol = UsuarioRol(id_usuario=usuario.id_usuario, id_rol=rol_cliente.id_rol)
    db.session.add(usuario_rol)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Error al crear usuario", 500)

    return usuario


def usuario_to_dict(usuario: Usuario) -> dict:
    roles = [ur.rol.nombre for ur in usuario.roles]
    email_verificado = bool(getattr(usuario, "email_verificado", False)) or bool(getattr(usuario, "verificado", False))
    return {
        "id": usuario.id_usuario,
        "nombre": usuario.nombre,
        "apellidos": usuario.apellidos,
        "correo_electronico": usuario.correo_electronico,
        "telefono": usuario.telefono,
        "ciudad": usuario.ciudad,
        "estado": usuario.estado,
        "pais": usuario.pais,
        "direccion_completa": usuario.direccion_completa,
        "foto_perfil": usuario.foto_perfil,
        "roles": roles,
        "estado_cuenta": usuario.estado_cuenta,
        "verificado": bool(getattr(usuario, "verificado", False)) or email_verificado,
        "email_verificado": email_verificado,
    }
