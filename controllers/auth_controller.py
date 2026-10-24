from flask import Blueprint, g, jsonify

from services.auth_service import AuthService, UsuarioService
from utils.auth import login_requerido, rol_requerido
from utils.http import ERROR_JSON, leer_json

auth_bp = Blueprint("auth_bp", __name__)
usuario_bp = Blueprint("usuario_bp", __name__)

auth_service = AuthService()
usuario_service = UsuarioService()


# ---------- Rutas PÚBLICAS (no piden token) ----------
@auth_bp.route("/auth/registro", methods=["POST"])
def registro():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = auth_service.registrar(datos)
    return jsonify(respuesta), status


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = auth_service.login(datos)
    return jsonify(respuesta), status


# ---------- Rutas PRIVADAS ----------
@auth_bp.route("/auth/me", methods=["GET"])
@login_requerido
def mi_perfil():
    respuesta, status = auth_service.perfil(g.empresa_id, g.usuario_id)
    return jsonify(respuesta), status


@auth_bp.route("/auth/password", methods=["PUT"])
@login_requerido
def cambiar_password():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = auth_service.cambiar_password(g.empresa_id, g.usuario_id, datos)
    return jsonify(respuesta), status


# ---------- Gestión de usuarios (solo admin) ----------
@usuario_bp.route("/usuarios", methods=["GET"])
@rol_requerido("admin")
def listar_usuarios():
    return jsonify(usuario_service.listar_usuarios(g.empresa_id)), 200


@usuario_bp.route("/usuarios", methods=["POST"])
@rol_requerido("admin")
def crear_usuario():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = usuario_service.crear_usuario(g.empresa_id, datos)
    return jsonify(respuesta), status


@usuario_bp.route("/usuarios/<int:id>", methods=["DELETE"])
@rol_requerido("admin")
def desactivar_usuario(id):
    respuesta, status = usuario_service.desactivar_usuario(g.empresa_id, g.usuario_id, id)
    return jsonify(respuesta), status


@usuario_bp.route("/usuarios/<int:id>/password", methods=["PUT"])
@rol_requerido("admin")
def restablecer_password(id):
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = usuario_service.restablecer_password(g.empresa_id, id, datos)
    return jsonify(respuesta), status
