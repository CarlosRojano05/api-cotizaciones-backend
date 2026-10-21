from config.database import consultar, insertar, insertar_muchos, modificar


class ModelCotizacion:
    def obtener_cotizaciones(self, empresa_id):
        # Alias en minúscula (c): en Linux MySQL distingue mayúsculas en alias de tablas.
        sql = """
            SELECT c.id, c.fecha, c.subtotal, c.descuento, c.impuesto, c.total, c.estado,
                   cl.nombre AS cliente_nombre,
                   cl.identificacion AS cliente_identificacion
            FROM cotizaciones c
            INNER JOIN clientes cl ON c.cliente_id = cl.id
            WHERE c.empresa_id = %s AND c.activo = 1
            ORDER BY c.fecha DESC, c.id DESC;
        """
        return consultar(sql, (empresa_id,))

    def insertar_cabecera(self, empresa_id, usuario_id, cliente_id,
                          subtotal, descuento, impuesto, total, conn):
        """`conn` es obligatorio: la cabecera SIEMPRE se guarda dentro de una transacción."""
        sql = """
            INSERT INTO cotizaciones
                (empresa_id, usuario_id, cliente_id, subtotal, descuento, impuesto, total, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendiente');
        """
        return insertar(sql, (empresa_id, usuario_id, cliente_id, subtotal, descuento, impuesto, total), conn)

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

    def actualizar_estado(self, empresa_id, cotizacion_id, estado):
        sql = "UPDATE cotizaciones SET estado = %s WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (estado, cotizacion_id, empresa_id))

    def obtener_cotizacion_por_id(self, empresa_id, cotizacion_id):
        sql_cabecera = """
            SELECT c.id, c.fecha, c.subtotal, c.descuento, c.impuesto, c.total, c.estado,
                   cl.id AS cliente_id, cl.nombre AS cliente_nombre,
                   cl.identificacion AS cliente_identificacion,
                   cl.telefono AS cliente_telefono, cl.email AS cliente_email,
                   cl.direccion AS cliente_direccion
            FROM cotizaciones c
            INNER JOIN clientes cl ON c.cliente_id = cl.id
            WHERE c.id = %s AND c.empresa_id = %s AND c.activo = 1;
        """
        cotizacion = consultar(sql_cabecera, (cotizacion_id, empresa_id), uno=True)
        if not cotizacion:
            return None

        # Los detalles no llevan empresa_id: ya verificamos arriba que la cotización es de esta empresa.
        sql_detalles = """
            SELECT cd.item_id, i.nombre AS item_nombre, cd.cantidad,
                   cd.precio_unitario, cd.subtotal_linea
            FROM cotizacion_detalles cd
            INNER JOIN items i ON cd.item_id = i.id
            WHERE cd.cotizacion_id = %s
            ORDER BY cd.id;
        """
        cotizacion["detalles_cotizaciones"] = consultar(sql_detalles, (cotizacion_id,))
        return cotizacion
