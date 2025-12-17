# backend/seed_articulos.py
from app import create_app
from app.extensions import db
from app.models.usuario import Usuario
from app.models.articulo import Articulo, ArticuloImagen

app = create_app()

with app.app_context():
    # Escoge un usuario propietario (usa tu admin o el que quieras)
    propietario = Usuario.query.filter_by(correo_electronico="sergio@test.com").first()

    if not propietario:
        raise RuntimeError("No encontré usuario 'sergio@test.com' para usar como propietario.")

    # Opcional: limpia artículos previos de ese user
    # Articulo.query.filter_by(propietario_id=propietario.id).delete()

    a1 = Articulo(
        titulo="Taladro inalámbrico Bosch 18V",
        descripcion="Taladro inalámbrico, incluye batería y cargador. Ideal para trabajos en casa y bricolaje.",
        precio_renta_dia=150.0,
        deposito_garantia=500.0,
        estado="disponible",
        propietario_id=propietario.id,
    )

    a2 = Articulo(
        titulo="Proyector Epson Full HD",
        descripcion="Proyector 1080p, ideal para presentaciones y noches de cine.",
        precio_renta_dia=300.0,
        deposito_garantia=1000.0,
        estado="disponible",
        propietario_id=propietario.id,
    )

    db.session.add_all([a1, a2])
    db.session.flush()  # para tener ids

    # Imágenes (de momento con URLs estáticas/externas)
    img1 = ArticuloImagen(
        articulo_id=a1.id,
        url="https://via.placeholder.com/400x250?text=Taladro",
        es_principal=True,
    )
    img2 = ArticuloImagen(
        articulo_id=a2.id,
        url="https://via.placeholder.com/400x250?text=Proyector",
        es_principal=True,
    )

    db.session.add_all([img1, img2])
    db.session.commit()

    print("✅ Artículos de prueba creados.")
