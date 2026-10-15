from flask import Blueprint, request, jsonify
from service.item_service import ItemService

item_bp = Blueprint('item_bp', __name__)

item = ItemService()

@item_bp.route('/items', methods=['GET'])
def listar_items_():
    items = item.listar_items()
    return jsonify(items), 200

@item_bp.route('/items', methods=['POST'])
def crear_item_():
    # 1. Atrapamos el JSON que viene desde Postman o el Frontend
    datos_item = request.json
    
    # Si por alguna razón no envían un JSON válido
    if not datos_item:
        return jsonify({"error": "No se enviaron datos en formato JSON"}), 400

    # 2. Se lo pasamos al Servicio para que aplique las reglas de negocio
    respuesta, status_code = item.crear_item(datos_item)
    
    # 3. Devolvemos la respuesta empaquetada con jsonify y su código HTTP
    return jsonify(respuesta), status_code