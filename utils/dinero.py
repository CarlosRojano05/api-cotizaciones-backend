"""
Dinero con Decimal, NUNCA con float.

    >>> 0.1 + 0.2
    0.30000000000000004          # float: error de redondeo
    >>> Decimal("0.1") + Decimal("0.2")
    Decimal('0.3')               # Decimal: exacto

Regla: convierte a Decimal apenas llegue el dato y redondea a 2 decimales
cada valor monetario antes de guardarlo.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTAVOS = Decimal("0.01")


def a_decimal(valor, nombre_campo="valor"):
    """Convierte lo que llegue en el JSON a Decimal, o lanza ValueError con un mensaje claro."""
    if valor is None or isinstance(valor, bool) or valor == "":
        raise ValueError(f"'{nombre_campo}' es obligatorio y debe ser un número")
    try:
        # str(valor) primero: Decimal(0.1) heredaría el error del float, Decimal("0.1") no.
        numero = Decimal(str(valor))
    except InvalidOperation:
        raise ValueError(f"'{nombre_campo}' debe ser un número válido")
    if not numero.is_finite():
        raise ValueError(f"'{nombre_campo}' debe ser un número válido")
    return numero


def redondear(numero):
    """Redondea a 2 decimales (0.125 -> 0.13, como se hace comercialmente)."""
    return numero.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
