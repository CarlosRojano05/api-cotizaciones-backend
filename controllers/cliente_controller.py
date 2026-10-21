from flask import Blueprint, g, jsonify

from services.cliente_service import ClienteService
from utils.auth import login_requerido, rol_requerido
from utils.http import ERROR_JSON, leer_json

cliente_bp = Blueprint("cliente_bp", __name__)
cliente_service = ClienteService()


@cliente_bp.route("/clientes", methods=["GET"])
@login_requerido
def listar_clientes():
    return jsonify(cliente_service.listar_clientes(g.empresa_id)), 200


@cliente_bp.route("/clientes/<int:id>", methods=["GET"])
@login_requerido
def listar_un_cliente(id):
    cliente = cliente_service.listar_cliente(g.empresa_id, id)
    if not cliente:
        return jsonify({"error": f"No se encontró el cliente con ID {id}"}), 404
    return jsonify(cliente), 200


@cliente_bp.route("/clientes", methods=["POST"])
@login_requerido
def crear_cliente():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = cliente_service.crear_cliente(g.empresa_id, datos)
    return jsonify(respuesta), status


@cliente_bp.route("/clientes/<int:id>", methods=["PUT"])
@login_requerido
def actualizar_cliente(id):
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = cliente_service.actualizar_cliente(g.empresa_id, id, datos)
    return jsonify(respuesta), status


@cliente_bp.route("/clientes/<int:id>", methods=["DELETE"])
@rol_requerido("admin")
def eliminar_cliente(id):
    respuesta, status = cliente_service.desactivar_cliente(g.empresa_id, id)
    return jsonify(respuesta), status
