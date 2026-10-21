from flask import Blueprint, g, jsonify

from services.cotizacion_service import CotizacionService
from utils.auth import login_requerido
from utils.http import ERROR_JSON, leer_json

cotizacion_bp = Blueprint("cotizacion_bp", __name__)
cotizacion_service = CotizacionService()


@cotizacion_bp.route("/cotizaciones", methods=["GET"])
@login_requerido
def listar_cotizaciones():
    return jsonify(cotizacion_service.listar_cotizaciones(g.empresa_id)), 200


@cotizacion_bp.route("/cotizaciones", methods=["POST"])
@login_requerido
def crear_cotizacion():
    datos = leer_json()
    if datos is None:
        return jsonify(ERROR_JSON), 400
    respuesta, status = cotizacion_service.crear_cotizacion(g.empresa_id, g.usuario_id, datos)
    return jsonify(respuesta), status


@cotizacion_bp.route("/cotizaciones/<int:id>", methods=["GET"])
@login_requerido
def ver_detalle_cotizacion(id):
    respuesta, status = cotizacion_service.obtener_cotizacion_detalle(g.empresa_id, id)
    return jsonify(respuesta), status


@cotizacion_bp.route("/cotizaciones/<int:id>/estado", methods=["PATCH"])
@login_requerido
def cambiar_estado_cotizacion(id):
    datos = leer_json()
    if datos is None or "estado" not in datos:
        return jsonify({"error": "Se requiere el campo 'estado' en el JSON"}), 400
    respuesta, status = cotizacion_service.actualizar_estado(g.empresa_id, id, datos["estado"])
    return jsonify(respuesta), status
