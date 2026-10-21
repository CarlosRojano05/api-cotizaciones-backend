"""Pequeñas ayudas para limpiar datos que llegan del JSON."""


def texto(valor):
    """Devuelve el texto sin espacios sobrantes; si no es texto, devuelve ''."""
    return valor.strip() if isinstance(valor, str) else ""
