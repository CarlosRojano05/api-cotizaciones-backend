from datetime import date
from decimal import Decimal

from models.cotizacion_model import ModelCotizacion
from models.dashboard_model import ModelDashboard
from utils.constantes import ESTADOS_PERMITIDOS
from utils.dinero import redondear

MESES_GRAFICA = 6
CERO = Decimal("0")


def _ultimos_meses(cantidad, hoy):
    """[(2026, 5), (2026, 6), ... (2026, 10)]: del más antiguo al mes actual."""
    meses, anio, mes = [], hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(meses))


class DashboardService:
    def __init__(self):
        self.dashboard = ModelDashboard()
        self.cotizacion = ModelCotizacion()

    def obtener_resumen(self, empresa_id, hoy=None):
        hoy = hoy or date.today()

        # 1) Por estado (siempre aparecen los tres, aunque no haya ninguna)
        por_estado = {e: {"cantidad": 0, "total": CERO} for e in ESTADOS_PERMITIDOS}
        for fila in self.dashboard.por_estado(empresa_id):
            por_estado[fila["estado"]] = {"cantidad": int(fila["cantidad"]), "total": fila["total"]}

        cantidad_total = sum(v["cantidad"] for v in por_estado.values())
        monto_total = sum((v["total"] for v in por_estado.values()), CERO)

        # 2) Tasa de aceptación sobre las cotizaciones YA CERRADAS (aceptadas + rechazadas).
        #    Las pendientes no cuentan: todavía no se sabe qué pasará con ellas.
        aceptadas = por_estado["Aceptada"]["cantidad"]
        cerradas = aceptadas + por_estado["Rechazada"]["cantidad"]
        tasa = round(aceptadas * 100 / cerradas, 1) if cerradas else None

        # 3) Pendientes vencidas y por vencer
        venc = self.dashboard.vencimientos(empresa_id)

        # 4) Serie de los últimos 6 meses (rellena con ceros los meses sin cotizaciones)
        datos_mes = {(f["anio"], f["mes"]): f for f in self.dashboard.por_mes(empresa_id, MESES_GRAFICA - 1)}
        por_mes = []
        for anio, mes in _ultimos_meses(MESES_GRAFICA, hoy):
            f = datos_mes.get((anio, mes))
            por_mes.append({
                "mes": f"{anio}-{mes:02d}",
                "cantidad": int(f["cantidad"]) if f else 0,
                "total_cotizado": redondear(f["total_cotizado"]) if f else CERO,
                "total_aceptado": redondear(f["total_aceptado"]) if f else CERO,
            })

        return {
            "por_estado": por_estado,
            "totales": {"cantidad": cantidad_total, "total": monto_total},
            "tasa_aceptacion": tasa,
            "pendientes": {
                "vencidas": {"cantidad": int(venc["vencidas_cantidad"]), "total": venc["vencidas_total"]},
                "por_vencer_7_dias": {"cantidad": int(venc["por_vencer_cantidad"]), "total": venc["por_vencer_total"]},
            },
            "mes_actual": por_mes[-1],
            "por_mes": por_mes,
            "recientes": self.cotizacion.obtener_cotizaciones(empresa_id, limite=5),
        }, 200
