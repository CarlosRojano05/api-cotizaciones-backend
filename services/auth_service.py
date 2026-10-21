from mysql.connector import errors as mysql_errors
from werkzeug.security import check_password_hash, generate_password_hash

from config.database import transaccion
from models.empresa_model import ModelEmpresa
from models.usuario_model import ModelUsuario
from utils.auth import crear_token
from utils.validaciones import texto

ROLES_VALIDOS = ("admin", "vendedor")
LARGO_MINIMO_PASSWORD = 8


def _validar_email_y_password(email, password):
    """Devuelve un mensaje de error, o None si todo está bien."""
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 100:
        return "El correo electrónico no es válido"
    if len(password) < LARGO_MINIMO_PASSWORD:
        return f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres"
    return None


class AuthService:
    def __init__(self):
        self.empresa = ModelEmpresa()
        self.usuario = ModelUsuario()

    def registrar(self, datos):
        """Crea una EMPRESA nueva y su primer usuario (admin) en una sola transacción."""
        empresa_nombre = texto(datos.get("empresa_nombre"))
        nit = texto(datos.get("nit")) or None
        nombre = texto(datos.get("nombre"))
        email = texto(datos.get("email")).lower()
        password = datos.get("password") if isinstance(datos.get("password"), str) else ""

        if not empresa_nombre or not nombre or not email or not password:
            return {"error": "empresa_nombre, nombre, email y password son obligatorios"}, 400

        error = _validar_email_y_password(email, password)
        if error:
            return {"error": error}, 400

        if self.usuario.obtener_por_email(email):
            return {"error": "Ya existe una cuenta con ese correo"}, 409

        # Nunca se guarda la contraseña: se guarda su "hash" (huella irreversible).
        password_hash = generate_password_hash(password)

        try:
            # Si falla la creación del usuario, la empresa tampoco se crea (rollback).
            with transaccion() as conn:
                empresa_id = self.empresa.insertar_empresa(empresa_nombre, nit, conn)
                usuario_id = self.usuario.insertar_usuario(
                    empresa_id, nombre, email, password_hash, "admin", conn
                )
        except mysql_errors.IntegrityError as e:
            if e.errno == 1062:  # llave duplicada (dos registros simultáneos con el mismo correo)
                return {"error": "Ya existe una cuenta con ese correo"}, 409
            raise

        return {
            "mensaje": "Empresa registrada exitosamente",
            "token": crear_token(usuario_id, empresa_id, "admin"),
            "usuario": {"id": usuario_id, "nombre": nombre, "email": email, "rol": "admin"},
            "empresa": {"id": empresa_id, "nombre": empresa_nombre},
        }, 201

    def login(self, datos):
        email = texto(datos.get("email")).lower()
        password = datos.get("password") if isinstance(datos.get("password"), str) else ""

        usuario = self.usuario.obtener_por_email(email)

        # Mismo mensaje para "no existe" y "clave incorrecta": no le damos pistas a un atacante.
        if (
            not usuario
            or not usuario["activo"]
            or not check_password_hash(usuario["password_hash"], password)
        ):
            return {"error": "Correo o contraseña incorrectos"}, 401

        return {
            "token": crear_token(usuario["id"], usuario["empresa_id"], usuario["rol"]),
            "usuario": {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "email": usuario["email"],
                "rol": usuario["rol"],
            },
            "empresa": {"id": usuario["empresa_id"], "nombre": usuario["empresa_nombre"]},
        }, 200

    def perfil(self, empresa_id, usuario_id):
        usuario = self.usuario.obtener_por_id(empresa_id, usuario_id)
        if not usuario:
            return {"error": "Usuario no encontrado"}, 404
        return usuario, 200


class UsuarioService:
    """Gestión de usuarios de UNA empresa (solo la usa el admin)."""

    def __init__(self):
        self.usuario = ModelUsuario()

    def listar_usuarios(self, empresa_id):
        return self.usuario.listar_usuarios(empresa_id)

    def crear_usuario(self, empresa_id, datos):
        nombre = texto(datos.get("nombre"))
        email = texto(datos.get("email")).lower()
        password = datos.get("password") if isinstance(datos.get("password"), str) else ""
        rol = texto(datos.get("rol")) or "vendedor"

        if not nombre or not email or not password:
            return {"error": "nombre, email y password son obligatorios"}, 400
        if rol not in ROLES_VALIDOS:
            return {"error": f"Rol inválido. Los permitidos son: {list(ROLES_VALIDOS)}"}, 400

        error = _validar_email_y_password(email, password)
        if error:
            return {"error": error}, 400

        try:
            nuevo_id = self.usuario.insertar_usuario(
                empresa_id, nombre, email, generate_password_hash(password), rol
            )
        except mysql_errors.IntegrityError as e:
            if e.errno == 1062:
                return {"error": "Ya existe una cuenta con ese correo"}, 409
            raise

        return {"mensaje": "Usuario creado exitosamente", "id": nuevo_id}, 201

    def desactivar_usuario(self, empresa_id, usuario_actual_id, usuario_id):
        if usuario_id == usuario_actual_id:
            return {"error": "No puedes desactivar tu propio usuario"}, 400
        if self.usuario.desactivar_usuario(empresa_id, usuario_id) == 0:
            return {"error": f"No se encontró el usuario activo con ID {usuario_id}"}, 404
        return {"mensaje": "Usuario desactivado exitosamente"}, 200
