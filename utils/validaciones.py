"""Pequeñas ayudas para limpiar datos que llegan del JSON."""


def texto(valor):
    """Devuelve el texto sin espacios sobrantes; si no es texto, devuelve ''."""
    return valor.strip() if isinstance(valor, str) else ""


def formatear_numero(prefijo, numero):
    """('COT', 7) -> 'COT-0007'. Pasados 9999 simplemente crece: 'COT-10000'."""
    return f"{prefijo}-{numero:04d}"
