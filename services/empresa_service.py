import io
import os
import re

from PIL import Image

from config.settings import Settings
from models.empresa_model import ModelEmpresa
from utils.dinero import a_decimal, redondear

MAX_LOGO_BYTES = 2 * 1024 * 1024        # 2 MB
FORMATOS_LOGO = ("PNG", "JPEG", "WEBP")
LADO_MAXIMO_LOGO = 600                  # px: el logo se reduce a este tamaño máximo


# ----------------------------------------------------------------------
# Validadores: cada uno recibe el valor enviado y devuelve el valor limpio,
# o lanza ValueError con un mensaje claro.
# ----------------------------------------------------------------------
def _texto(campo, maximo, obligatorio=False):
    def validar(valor):
        if valor is None and not obligatorio:
            return None
        if not isinstance(valor, str):
            raise ValueError(f"'{campo}' debe ser texto")
        limpio = valor.strip()
        if obligatorio and not limpio:
            raise ValueError(f"'{campo}' no puede estar vacío")
        if len(limpio) > maximo:
            raise ValueError(f"'{campo}' no puede superar {maximo} caracteres")
        return limpio or None
    return validar


def _correo(valor):
    limpio = _texto("email", 100)(valor)
    if limpio and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", limpio):
        raise ValueError("'email' no es un correo válido")
    return limpio


def _moneda(valor):
    limpio = _texto("moneda", 3, obligatorio=True)(valor).upper()
    if not re.fullmatch(r"[A-Z]{3}", limpio):
        raise ValueError("'moneda' debe ser un código de 3 letras (ej. COP, USD)")
    return limpio


def _color(valor):
    limpio = _texto("color_primario", 7, obligatorio=True)(valor)
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", limpio):
        raise ValueError("'color_primario' debe tener el formato #RRGGBB (ej. #1F4E79)")
    return limpio.upper()


def _iva(valor):
    iva = redondear(a_decimal(valor, "iva_defecto"))
    if iva < 0 or iva > 100:
        raise ValueError("'iva_defecto' debe estar entre 0 y 100")
    return iva


def _validez(valor):
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 365:
        raise ValueError("'validez_dias' debe ser un número entero entre 1 y 365")
    return valor


def _prefijo(valor):
    limpio = _texto("prefijo", 10, obligatorio=True)(valor).upper()
    if not re.fullmatch(r"[A-Z0-9]{1,10}", limpio):
        raise ValueError("'prefijo' debe tener de 1 a 10 letras o números, sin espacios")
    return limpio


VALIDADORES = {
    "nombre": _texto("nombre", 150, obligatorio=True),
    "nit": _texto("nit", 30),
    "direccion": _texto("direccion", 255),
    "telefono": _texto("telefono", 30),
    "email": _correo,
    "sitio_web": _texto("sitio_web", 100),
    "color_primario": _color,
    "moneda": _moneda,
    "iva_defecto": _iva,
    "validez_dias": _validez,
    "prefijo": _prefijo,
    "condiciones": _texto("condiciones", 2000),
}


class EmpresaService:
    """Configuración de la empresa: datos para el PDF, preferencias comerciales y logo."""

    def __init__(self):
        self.empresa = ModelEmpresa()

    # ---------------- Configuración ----------------
    def _publica(self, config):
        """Quita la ruta interna del logo y la reemplaza por un simple tiene_logo (true/false)."""
        config = dict(config)
        config["tiene_logo"] = bool(config.pop("logo_path", None))
        return config

    def obtener_configuracion(self, empresa_id):
        config = self.empresa.obtener_configuracion(empresa_id)
        if not config:
            return {"error": "Empresa no encontrada"}, 404
        return self._publica(config), 200

    def actualizar_configuracion(self, empresa_id, datos):
        """Actualización parcial: solo cambia los campos que vengan en el JSON."""
        cambios = {}
        try:
            for campo, validar in VALIDADORES.items():
                if campo in datos:
                    cambios[campo] = validar(datos[campo])
        except ValueError as e:
            return {"error": str(e)}, 400

        if not cambios:
            return {"error": f"No se envió ningún campo válido. Campos permitidos: {list(VALIDADORES)}"}, 400

        self.empresa.actualizar_configuracion(empresa_id, cambios)
        return {
            "mensaje": "Configuración actualizada exitosamente",
            "configuracion": self._publica(self.empresa.obtener_configuracion(empresa_id)),
        }, 200

    # ---------------- Logo ----------------
    def resolver_ruta_logo(self, ruta_relativa):
        """Convierte 'logos/empresa_1.png' en ruta completa, verificando que no se salga de uploads."""
        if not ruta_relativa:
            return None
        base = os.path.abspath(Settings.UPLOADS_DIR)
        ruta = os.path.abspath(os.path.join(base, ruta_relativa))
        if not ruta.startswith(base + os.sep) or not os.path.isfile(ruta):
            return None
        return ruta

    def ruta_logo(self, empresa_id):
        config = self.empresa.obtener_configuracion(empresa_id)
        return self.resolver_ruta_logo(config["logo_path"]) if config else None

    def guardar_logo(self, empresa_id, archivo):
        if archivo is None or not archivo.filename:
            return {"error": "Envía la imagen en el campo 'logo' (form-data, tipo File)"}, 400

        contenido = archivo.read(MAX_LOGO_BYTES + 1)
        if len(contenido) > MAX_LOGO_BYTES:
            return {"error": "El logo no puede pesar más de 2 MB"}, 413

        # No confiamos en la extensión ni en lo que diga el cliente: abrimos la imagen de verdad.
        try:
            with Image.open(io.BytesIO(contenido)) as original:
                original.load()  # decodifica todo: detecta archivos dañados
                if original.format not in FORMATOS_LOGO:
                    raise ValueError
                logo = original.convert("RGBA")
        except Exception:
            return {"error": "El archivo no es una imagen válida. Usa PNG, JPG o WEBP"}, 400

        # Se reduce y se vuelve a guardar como PNG propio: así cualquier contenido
        # extraño que traiga el archivo original se descarta.
        logo.thumbnail((LADO_MAXIMO_LOGO, LADO_MAXIMO_LOGO))
        relativa = os.path.join("logos", f"empresa_{int(empresa_id)}.png")
        absoluta = os.path.join(Settings.UPLOADS_DIR, relativa)
        os.makedirs(os.path.dirname(absoluta), exist_ok=True)
        logo.save(absoluta, "PNG", optimize=True)

        self.empresa.actualizar_logo(empresa_id, relativa.replace(os.sep, "/"))
        return {"mensaje": "Logo actualizado exitosamente"}, 200

    def eliminar_logo(self, empresa_id):
        ruta = self.ruta_logo(empresa_id)
        if ruta:
            os.remove(ruta)
        self.empresa.actualizar_logo(empresa_id, None)
        return {"mensaje": "Logo eliminado"}, 200
