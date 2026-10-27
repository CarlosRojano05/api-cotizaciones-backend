import os

from flask import Blueprint, g, jsonify, request, send_file

from services.empresa_service import EmpresaService
from utils.auth import login_requerido, rol_requerido
from utils.http import ERROR_JSON, leer_json

empresa_bp = Blueprint("empresa_bp", __name__)
empresa_service = EmpresaService()


# Ver la configuración: cualquier usuario. Cambiarla: solo admin.
@empresa_bp.route("/empresa/configuracion", methods=["GET"])
@login_requerido
def ver_configuracion():
    respuesta, status = empresa_service.obtener_configuracion(g.empresa_id)
    return jsonify(respuesta), status


@empresa_bp.route("/empresa/configuracion", methods=["PUT"])
@rol_requerido("admin")
def actualizar_configuracion():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = empresa_service.actualizar_configuracion(g.empresa_id, datos)
    return jsonify(respuesta), status


# ---------- Logo ----------
@empresa_bp.route("/empresa/logo", methods=["GET"])
@login_requerido
def ver_logo():
    ruta = empresa_service.ruta_logo(g.empresa_id)
    if not ruta:
        return jsonify({"error": "La empresa no tiene logo"}), 404
    # max_age=0: el navegador siempre pregunta si cambió (el archivo conserva el mismo nombre).
    return send_file(ruta, mimetype="image/png", max_age=0)


@empresa_bp.route("/empresa/logo", methods=["POST"])
@rol_requerido("admin")
def subir_logo():
    # Los archivos NO llegan como JSON sino como "form-data" con un campo de tipo File llamado "logo".
    respuesta, status = empresa_service.guardar_logo(g.empresa_id, request.files.get("logo"))
    return jsonify(respuesta), status


@empresa_bp.route("/empresa/logo", methods=["DELETE"])
@rol_requerido("admin")
def eliminar_logo():
    respuesta, status = empresa_service.eliminar_logo(g.empresa_id)
    return jsonify(respuesta), status
