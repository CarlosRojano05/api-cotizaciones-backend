"""
Punto de entrada de la aplicación.

Se usa el patrón "application factory" (create_app): en lugar de crear la app
suelta, la construimos dentro de una función. Es la forma recomendada porque
facilita las pruebas automáticas y el despliegue en producción.

Para arrancar en desarrollo:   python app.py
"""
import logging
from decimal import Decimal

import mysql.connector
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from config.settings import Settings
from controllers.auth_controller import auth_bp, usuario_bp
from controllers.cliente_controller import cliente_bp
from controllers.cotizacion_controller import cotizacion_bp
from controllers.item_controller import item_bp


class ProveedorJSON(DefaultJSONProvider):
    """Convierte Decimal a número en el JSON de salida (se calcula en Decimal, se muestra como número)."""

    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Settings)
    app.json = ProveedorJSON(app)
    logging.basicConfig(level=logging.INFO)

    CORS(app, origins=Settings.CORS_ORIGINS)

    # ---------- JWT: respuestas de error en JSON y en español ----------
    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def _sin_token(motivo):
        return jsonify({"error": "Debes iniciar sesión para acceder a este recurso"}), 401

    @jwt.invalid_token_loader
    def _token_invalido(motivo):
        return jsonify({"error": "Token inválido"}), 401

    @jwt.expired_token_loader
    def _token_expirado(encabezado, datos):
        return jsonify({"error": "Tu sesión expiró. Inicia sesión nuevamente"}), 401

    # ---------- Registro de blueprints ----------
    for blueprint in (auth_bp, usuario_bp, cliente_bp, item_bp, cotizacion_bp):
        app.register_blueprint(blueprint)

    @app.route("/salud", methods=["GET"])
    def salud():
        """Sirve para comprobar que el servidor está vivo (lo usan los servicios de hosting)."""
        return jsonify({"estado": "ok"}), 200

    # ---------- Manejo global de errores: la API SIEMPRE responde JSON ----------
    @app.errorhandler(HTTPException)
    def _error_http(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(mysql.connector.errors.DataError)
    def _dato_invalido(e):
        return jsonify({"error": "Algún dato es inválido o excede el tamaño permitido"}), 400

    @app.errorhandler(mysql.connector.errors.IntegrityError)
    def _integridad(e):
        return jsonify({"error": "La operación viola una restricción de la base de datos"}), 409

    @app.errorhandler(Exception)
    def _error_inesperado(e):
        app.logger.exception("Error inesperado")  # el detalle queda en el log, NO se le muestra al usuario
        return jsonify({"error": "Error interno del servidor"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Settings.DEBUG, port=5000)
