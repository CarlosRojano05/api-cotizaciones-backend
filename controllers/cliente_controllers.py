from flask import Blueprint, request, jsonify
from service.cliente_service import ClienteService

cliente_bp = Blueprint('cliente_bp', __name__)

cliente = ClienteService()

@cliente_bp.route('/clientes', methods=['GET'])
def listar_clientes_():
    clientes = cliente.listar_clientes()
    return jsonify(clientes), 200

@cliente_bp.route('/clientes', methods=['POST'])
def crear_cliente_():
    # 1. Atrapamos el JSON que viene desde Postman o el Frontend
    datos_cliente = request.json
    
    # Si por alguna razón no envían un JSON válido
    if not datos_cliente:
        return jsonify({"error": "No se enviaron datos en formato JSON"}), 400

    # 2. Se lo pasamos al Servicio para que aplique las reglas de negocio
    respuesta, status_code = cliente.crear_cliente(datos_cliente)
    
    # 3. Devolvemos la respuesta empaquetada con jsonify y su código HTTP
    return jsonify(respuesta), status_code