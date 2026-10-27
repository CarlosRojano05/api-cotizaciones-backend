from flask import Blueprint, g, jsonify

from services.dashboard_service import DashboardService
from utils.auth import login_requerido

dashboard_bp = Blueprint("dashboard_bp", __name__)
dashboard_service = DashboardService()


@dashboard_bp.route("/dashboard", methods=["GET"])
@login_requerido
def ver_dashboard():
    respuesta, status = dashboard_service.obtener_resumen(g.empresa_id)
    return jsonify(respuesta), status
