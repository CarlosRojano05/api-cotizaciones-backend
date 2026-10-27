from flask import Blueprint, g, jsonify

from services.item_service import ItemService
from utils.auth import login_requerido, rol_requerido
from utils.http import ERROR_JSON, leer_json

item_bp = Blueprint("item_bp", __name__)
item_service = ItemService()


# Ver el catálogo: cualquier usuario. Modificarlo: solo admin.
@item_bp.route("/items", methods=["GET"])
@login_requerido
def listar_items():
    return jsonify(item_service.listar_items(g.empresa_id)), 200


@item_bp.route("/items", methods=["POST"])
@rol_requerido("admin")
def crear_item():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = item_service.crear_item(g.empresa_id, datos)
    return jsonify(respuesta), status


@item_bp.route("/items/<int:id>", methods=["PUT"])
@rol_requerido("admin")
def actualizar_item(id):
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = item_service.actualizar_item(g.empresa_id, id, datos)
    return jsonify(respuesta), status


@item_bp.route("/items/<int:id>", methods=["DELETE"])
@rol_requerido("admin")
def eliminar_item(id):
    respuesta, status = item_service.desactivar_item(g.empresa_id, id)
    return jsonify(respuesta), status
