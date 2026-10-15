from flask import Blueprint, request, jsonify
from service.cotizacion_service import CotizacionService

cotizacion_bp = Blueprint('cotizacion_bp', __name__)
cotizacion_service = CotizacionService()

@cotizacion_bp.route('/cotizaciones', methods=['GET'])
def listar_cotizaciones_():
    cotizaciones = cotizacion_service.listar_cotizaciones()
    return jsonify(cotizaciones), 200

@cotizacion_bp.route('/cotizaciones', methods=['POST'])
def crear_cotizacion_():
    datos = request.json
    if not datos:
        return jsonify({"error": "No se enviaron datos en formato JSON"}), 400

    respuesta, status_code = cotizacion_service.crear_cotizacion(datos)
    return jsonify(respuesta), status_code