from config.database import consultar


class ModelDashboard:
    """Consultas de resumen para el panel principal. Todas filtran por empresa."""

    def por_estado(self, empresa_id):
        sql = """
            SELECT estado, COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS total
            FROM cotizaciones
            WHERE empresa_id = %s AND activo = 1
            GROUP BY estado;
        """
        return consultar(sql, (empresa_id,))

    def vencimientos(self, empresa_id):
        """Solo cotizaciones Pendientes: cuántas ya vencieron y cuántas vencen en los próximos 7 días."""
        sql = """
            SELECT
                COUNT(CASE WHEN fecha_vencimiento < CURDATE() THEN 1 END) AS vencidas_cantidad,
                COALESCE(SUM(CASE WHEN fecha_vencimiento < CURDATE() THEN total END), 0) AS vencidas_total,
                COUNT(CASE WHEN fecha_vencimiento >= CURDATE()
                            AND fecha_vencimiento <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 1 END)
                    AS por_vencer_cantidad,
                COALESCE(SUM(CASE WHEN fecha_vencimiento >= CURDATE()
                                   AND fecha_vencimiento <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                                  THEN total END), 0) AS por_vencer_total
            FROM cotizaciones
            WHERE empresa_id = %s AND activo = 1 AND estado = 'Pendiente';
        """
        return consultar(sql, (empresa_id,), uno=True)

    def por_mes(self, empresa_id, meses_atras):
        """Cantidad y montos por mes, desde el día 1 de hace `meses_atras` meses."""
        sql = """
            SELECT YEAR(fecha) AS anio, MONTH(fecha) AS mes,
                   COUNT(*) AS cantidad,
                   COALESCE(SUM(total), 0) AS total_cotizado,
                   COALESCE(SUM(CASE WHEN estado = 'Aceptada' THEN total END), 0) AS total_aceptado
            FROM cotizaciones
            WHERE empresa_id = %s AND activo = 1
              AND fecha >= DATE_SUB(DATE_SUB(CURDATE(), INTERVAL DAYOFMONTH(CURDATE()) - 1 DAY),
                                    INTERVAL %s MONTH)
            GROUP BY YEAR(fecha), MONTH(fecha)
            ORDER BY anio, mes;
        """
        return consultar(sql, (empresa_id, meses_atras))
