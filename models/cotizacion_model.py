from config.database import consultar, insertar, insertar_muchos, modificar
from utils.validaciones import formatear_numero


def _decorar(fila):
    """Agrega 'numero_formateado' (COT-0001) y convierte 'vencida' (0/1) a True/False."""
    fila["numero_formateado"] = formatear_numero(fila.pop("prefijo"), fila["numero"])
    fila["vencida"] = bool(fila["vencida"])
    return fila


class ModelCotizacion:
    # "Vencida" NO se guarda: se calcula al consultar (Pendiente y con fecha ya pasada).
    # Así nunca queda desactualizada y no hace falta ningún proceso nocturno.
    _VENCIDA = "(c.estado = 'Pendiente' AND c.fecha_vencimiento < CURDATE()) AS vencida"

    def obtener_cotizaciones(self, empresa_id, estado=None, cliente_id=None,
                             solo_vencidas=False, buscar=None, limite=None):
        """
        Lista con filtros opcionales. El WHERE se arma con TEXTOS FIJOS (nunca con datos del
        usuario); los valores del usuario viajan siempre como parámetros (%s).
        """
        condiciones = ["c.empresa_id = %s", "c.activo = 1"]
        params = [empresa_id]

        if estado:
            condiciones.append("c.estado = %s")
            params.append(estado)
        if cliente_id:
            condiciones.append("c.cliente_id = %s")
            params.append(cliente_id)
        if solo_vencidas:
            condiciones.append("c.estado = 'Pendiente' AND c.fecha_vencimiento < CURDATE()")
        if buscar:
            condiciones.append(
                "(cl.nombre LIKE %s OR cl.identificacion LIKE %s "
                "OR CONCAT(e.prefijo, '-', LPAD(c.numero, 4, '0')) LIKE %s)"
            )
            params.extend([f"%{buscar}%"] * 3)

        sql = f"""
            SELECT c.id, c.numero, e.prefijo, c.fecha, c.fecha_vencimiento, {self._VENCIDA},
                   c.subtotal, c.descuento, c.iva_porcentaje, c.impuesto, c.total, c.estado,
                   cl.id AS cliente_id, cl.nombre AS cliente_nombre,
                   cl.identificacion AS cliente_identificacion
            FROM cotizaciones c
            INNER JOIN clientes cl ON c.cliente_id = cl.id
            INNER JOIN empresas e ON c.empresa_id = e.id
            WHERE {" AND ".join(condiciones)}
            ORDER BY c.numero DESC
        """
        if limite:
            sql += " LIMIT %s"
            params.append(limite)

        return [_decorar(f) for f in consultar(sql, tuple(params))]

    def insertar_cabecera(self, empresa_id, usuario_id, cliente_id, numero, fecha_vencimiento,
                          iva_porcentaje, subtotal, descuento, impuesto, total, notas, conn):
        """`conn` es obligatorio: la cabecera SIEMPRE se guarda dentro de una transacción."""
        sql = """
            INSERT INTO cotizaciones
                (empresa_id, usuario_id, cliente_id, numero, fecha_vencimiento, iva_porcentaje,
                 subtotal, descuento, impuesto, total, notas, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente');
        """
        valores = (empresa_id, usuario_id, cliente_id, numero, fecha_vencimiento, iva_porcentaje,
                   subtotal, descuento, impuesto, total, notas)
        return insertar(sql, valores, conn)

    def insertar_detalles(self, cotizacion_id, lineas, conn):
        """Guarda todas las líneas con UNA sola instrucción (executemany)."""
        sql = """
            INSERT INTO cotizacion_detalles
                (cotizacion_id, item_id, cantidad, precio_unitario, subtotal_linea)
            VALUES (%s, %s, %s, %s, %s);
        """
        filas = [
            (cotizacion_id, l["item_id"], l["cantidad"], l["precio_unitario"], l["subtotal_linea"])
            for l in lineas
        ]
        return insertar_muchos(sql, filas, conn)

    def obtener_estado(self, empresa_id, cotizacion_id, conn=None, bloquear=False):
        """
        Devuelve {'id', 'estado'} o None. Con bloquear=True usa FOR UPDATE: nadie más puede
        cambiar esta cotización hasta que termine la transacción (evita que dos usuarios
        cambien el estado a la vez y el historial quede incoherente).
        """
        sql = "SELECT id, estado FROM cotizaciones WHERE id = %s AND empresa_id = %s AND activo = 1"
        if bloquear:
            sql += " FOR UPDATE"
        return consultar(sql + ";", (cotizacion_id, empresa_id), uno=True, conn=conn)

    def actualizar_estado(self, empresa_id, cotizacion_id, estado, conn):
        sql = "UPDATE cotizaciones SET estado = %s WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (estado, cotizacion_id, empresa_id), conn=conn)

    def anular(self, empresa_id, cotizacion_id):
        """Baja lógica: la cotización deja de aparecer, pero su número NO se reutiliza."""
        sql = "UPDATE cotizaciones SET activo = 0 WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (cotizacion_id, empresa_id))

    def obtener_cotizacion_por_id(self, empresa_id, cotizacion_id):
        sql_cabecera = f"""
            SELECT c.id, c.numero, e.prefijo, c.fecha, c.fecha_vencimiento, {self._VENCIDA},
                   c.subtotal, c.descuento, c.iva_porcentaje, c.impuesto, c.total, c.estado, c.notas,
                   cl.id AS cliente_id, cl.nombre AS cliente_nombre,
                   cl.identificacion AS cliente_identificacion,
                   cl.telefono AS cliente_telefono, cl.email AS cliente_email,
                   cl.direccion AS cliente_direccion
            FROM cotizaciones c
            INNER JOIN clientes cl ON c.cliente_id = cl.id
            INNER JOIN empresas e ON c.empresa_id = e.id
            WHERE c.id = %s AND c.empresa_id = %s AND c.activo = 1;
        """
        cotizacion = consultar(sql_cabecera, (cotizacion_id, empresa_id), uno=True)
        if not cotizacion:
            return None
        cotizacion = _decorar(cotizacion)

        # Los detalles no llevan empresa_id: ya verificamos arriba que la cotización es de esta empresa.
        sql_detalles = """
            SELECT cd.item_id, i.nombre AS item_nombre, i.descripcion AS item_descripcion,
                   i.tipo AS item_tipo, cd.cantidad, cd.precio_unitario, cd.subtotal_linea
            FROM cotizacion_detalles cd
            INNER JOIN items i ON cd.item_id = i.id
            WHERE cd.cotizacion_id = %s
            ORDER BY cd.id;
        """
        cotizacion["detalles_cotizaciones"] = consultar(sql_detalles, (cotizacion_id,))
        return cotizacion
