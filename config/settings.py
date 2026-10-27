"""
Configuración central de la aplicación.

Todo lo que cambia entre tu computador y el servidor de producción
(contraseñas, claves, hosts) se lee desde variables de entorno.
Así el código nunca contiene secretos.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# Lee el archivo .env (si existe) y lo carga como variables de entorno.
load_dotenv()

# Carpeta raíz del proyecto (donde está app.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _requerida(nombre):
    """Lee una variable obligatoria. Si falta, la app NO arranca (mejor fallar al inicio)."""
    valor = os.getenv(nombre)
    if not valor:
        raise RuntimeError(
            f"Falta la variable de entorno '{nombre}'. Copia .env.example a .env y complétala."
        )
    return valor


class Settings:
    # Base de datos
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "db_cotizaciones")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

    # Flask-JWT-Extended lee estas dos claves directamente de app.config
    JWT_SECRET_KEY = _requerida("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_HORAS", "8")))

    # Archivos subidos (logos de las empresas)
    UPLOADS_DIR = os.getenv("UPLOADS_DIR") or os.path.join(BASE_DIR, "uploads")
    # Flask rechaza (413) cualquier petición más grande que esto, antes de procesarla
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    # Aplicación
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
