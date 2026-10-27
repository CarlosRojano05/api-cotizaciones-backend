"""
Autenticación y autorización.

Flujo:
  1. El usuario hace login -> el servidor le entrega un TOKEN (JWT) firmado.
  2. En cada petición el cliente envía:  Authorization: Bearer <token>
  3. Los decoradores de abajo validan el token y dejan en `g` (un objeto
     temporal de Flask, vive solo durante esa petición):
         g.usuario_id, g.empresa_id, g.rol

IMPORTANTE (aislamiento de datos): la empresa SIEMPRE se toma del token,
jamás del JSON que envía el cliente. Así nadie puede pedir datos de otra empresa.
"""
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, verify_jwt_in_request


def crear_token(usuario_id, empresa_id, rol):
    return create_access_token(
        identity=str(usuario_id),  # el "sub" del JWT debe ser texto
        additional_claims={"empresa_id": empresa_id, "rol": rol},
    )


def login_requerido(funcion):
    """Exige un token válido. Deja usuario_id, empresa_id y rol en `g`."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        verify_jwt_in_request()  # lanza error 401 si falta, expiró o es falso
        datos_token = get_jwt()
        g.usuario_id = int(get_jwt_identity())
        g.empresa_id = datos_token["empresa_id"]
        g.rol = datos_token["rol"]
        return funcion(*args, **kwargs)
    return envoltura


def rol_requerido(*roles_permitidos):
    """Exige token válido Y que el rol esté en la lista. Ej: @rol_requerido("admin")"""
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if g.rol not in roles_permitidos:
                return jsonify({"error": "No tienes permisos para realizar esta acción"}), 403
            return funcion(*args, **kwargs)
        return login_requerido(envoltura)
    return decorador
