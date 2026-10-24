from flask import Blueprint, Response, g, jsonify, request

from services.cotizacion_service import CotizacionService
from utils.auth import login_requerido, rol_requerido
from utils.http import ERROR_JSON, leer_json

cotizacion_bp = Blueprint("cotizacion_bp", __name__)
cotizacion_service = CotizacionService()


@cotizacion_bp.route("/cotizaciones", methods=["GET"])
@login_requerido
def listar_cotizaciones():
    # Filtros opcionales por URL: /cotizaciones?estado=Pendiente&cliente_id=3&vencidas=1&buscar=andina
    filtros = {k: request.args.get(k) for k in ("estado", "cliente_id", "vencidas", "buscar")}
    respuesta, status = cotizacion_service.listar_cotizaciones(g.empresa_id, filtros)
    return jsonify(respuesta), status


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
    respuesta, status = cotizacion_service.actualizar_estado(
        g.empresa_id, g.usuario_id, id, datos["estado"], datos.get("comentario")
    )
    return jsonify(respuesta), status


@cotizacion_bp.route("/cotizaciones/<int:id>/historial", methods=["GET"])
@login_requerido
def ver_historial(id):
    respuesta, status = cotizacion_service.obtener_historial(g.empresa_id, id)
    return jsonify(respuesta), status


@cotizacion_bp.route("/cotizaciones/<int:id>/pdf", methods=["GET"])
@login_requerido
def descargar_pdf(id):
    resultado, status = cotizacion_service.generar_pdf(g.empresa_id, id)
    if status != 200:
        return jsonify(resultado), status

    contenido, nombre_archivo = resultado
    # ?descargar=1 fuerza la descarga; sin él, el navegador intenta mostrarlo en pantalla.
    modo = "attachment" if request.args.get("descargar") == "1" else "inline"
    return Response(
        contenido,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'{modo}; filename="{nombre_archivo}"'},
    )


@cotizacion_bp.route("/cotizaciones/<int:id>", methods=["DELETE"])
@rol_requerido("admin")
def anular_cotizacion(id):
    respuesta, status = cotizacion_service.anular_cotizacion(g.empresa_id, id)
    return jsonify(respuesta), status
