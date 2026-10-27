from config.database import consultar, insertar


class ModelHistorial:
    """Bitácora de cambios de estado de las cotizaciones."""

    def registrar(self, cotizacion_id, usuario_id, estado_anterior, estado_nuevo, comentario, conn):
        """`conn` obligatorio: siempre se registra dentro de la misma transacción del cambio."""
        sql = """
            INSERT INTO cotizacion_historial
                (cotizacion_id, usuario_id, estado_anterior, estado_nuevo, comentario)
            VALUES (%s, %s, %s, %s, %s);
        """
        return insertar(sql, (cotizacion_id, usuario_id, estado_anterior, estado_nuevo, comentario), conn)

    def listar(self, empresa_id, cotizacion_id):
        # El JOIN con cotizaciones garantiza que la cotización sea de ESTA empresa.
        sql = """
            SELECT h.id, h.estado_anterior, h.estado_nuevo, h.comentario, h.fecha,
                   u.nombre AS usuario_nombre
            FROM cotizacion_historial h
            INNER JOIN cotizaciones c ON h.cotizacion_id = c.id
            LEFT JOIN usuarios u ON h.usuario_id = u.id
            WHERE h.cotizacion_id = %s AND c.empresa_id = %s
            ORDER BY h.id;
        """
        return consultar(sql, (cotizacion_id, empresa_id))
