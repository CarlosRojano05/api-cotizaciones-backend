"""Ayudas para los controllers."""
from flask import request

ERROR_JSON = {"error": "No se enviaron datos en formato JSON"}


def leer_json():
    """Devuelve el cuerpo JSON como dict, o None si falta / está vacío / no es un objeto."""
    datos = request.get_json(silent=True)  # silent=True: no lanza error si no es JSON
    if not isinstance(datos, dict) or not datos:
        return None
    return datos
