
import pytest

from sqlalchemy.pool import StaticPool
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import TestConfig as BaseTestConfig
from app.extensions import db, bcrypt

# Importar modelos para que SQLAlchemy registre mappers/tablas
import app.models  # noqa: F401
from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol  # noqa: F401
from app.models.categoria import Categoria
from app.models.articulo import Articulo


class PytestConfig(BaseTestConfig):
	SQLALCHEMY_DATABASE_URI = "sqlite://"
	SQLALCHEMY_ENGINE_OPTIONS = {
		"connect_args": {"check_same_thread": False},
		"poolclass": StaticPool,
	}
	JWT_SECRET_KEY = "test-secret"


@pytest.fixture(scope="session")
def app():
	app = create_app(PytestConfig)
	with app.app_context():
		db.create_all()
		yield app
		db.session.remove()
		db.drop_all()


@pytest.fixture()
def client(app):
	return app.test_client()


@pytest.fixture()
def db_session(app):
	with app.app_context():
		yield db.session
		db.session.rollback()


@pytest.fixture()
def make_user(db_session):
	def _make_user(
		email: str,
		nombre: str = "Test",
		apellidos: str = "User",
		password: str = "Passw0rd!",
		verificado: bool = True,
		telefono: str = "5512345678",
		ciudad: str = "CDMX",
		estado: str = "CDMX",
		pais: str = "MX",
	):
		u = Usuario(
			nombre=nombre,
			apellidos=apellidos,
			correo_electronico=email,
			hash_contrasena=bcrypt.generate_password_hash(password).decode("utf-8"),
			estado_cuenta="activo",
			verificado=verificado,
			telefono=telefono,
			ciudad=ciudad,
			estado=estado,
			pais=pais,
		)
		db_session.add(u)
		db_session.commit()
		return u

	return _make_user


@pytest.fixture()
def make_token(app):
	def _make_token(user_id: int, roles: list[str] | None = None) -> str:
		roles = roles or []
		with app.app_context():
			return create_access_token(identity=str(user_id), additional_claims={"roles": roles})

	return _make_token


@pytest.fixture()
def auth_header(make_token):
	def _auth_header(user_id: int, roles: list[str] | None = None) -> dict:
		token = make_token(user_id, roles=roles)
		return {"Authorization": f"Bearer {token}"}

	return _auth_header


@pytest.fixture()
def make_categoria(db_session):
	def _make_categoria(nombre: str = "CategoriaTest"):
		existente = Categoria.query.filter_by(nombre=nombre).first()
		if existente is not None:
			return existente
		c = Categoria(nombre=nombre)
		db_session.add(c)
		db_session.commit()
		return c

	return _make_categoria


@pytest.fixture()
def make_articulo(db_session, make_categoria):
	def _make_articulo(id_propietario: int, titulo: str = "Articulo", unidad: str = "por_dia"):
		cat = make_categoria(nombre="CategoriaTest")
		a = Articulo(
			id_propietario=id_propietario,
			titulo=titulo,
			descripcion="Desc",
			id_categoria=cat.id,
			precio_base=100,
			unidad_precio=unidad,
			monto_deposito=50,
			estado_publicacion="publicado",
		)
		db_session.add(a)
		db_session.commit()
		return a

	return _make_articulo
