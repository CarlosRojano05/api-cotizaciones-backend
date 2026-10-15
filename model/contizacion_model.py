from config.conexion import ConexionMysql

class ModelCotizacion:
    def __init__(self):
        self.db = ConexionMysql()
        
    def obtener_cotizaciones(self): 
        # Trae la cabecera de la cotización unida al nombre del cliente para que sea legible
        
        sql = """
               SELECT 
                   c.id, 
                   c.fecha, 
                   c.subtotal, 
                   c.impuesto, 
                   c.total, 
                   c.estado, 
                   cl.nombre AS cliente_nombre,
                   cl.identificacion AS cliente_identificacion
               FROM cotizaciones C
               INNER JOIN clientes cl ON c.cliente_id = cl.id
               WHERE c.activo = 1; 
               
                """
        
        with self.db.conexion.cursor(dictionary=True) as cursor_temporal:
            cursor_temporal.execute(sql)
            return cursor_temporal.fetchall()
        
    def ingresar_cotizacion(self, cliente_id, subtotal, descuento, impuesto, total): 
            
            sql = """
                   INSERT INTO cotizaciones (cliente_id, subtotal, descuento, impuesto, total, estado)
                   VALUES (%s, %s, %s, %s, %s, 'Pendiente') 
                   
                   """ 
            valores =(cliente_id, subtotal, descuento, impuesto, total)   
            with self.db.conexion.cursor(dictionary=True) as cursor_temporal:
                cursor_temporal.execute(sql, valores)
                self.db.conexion.commit()
                return cursor_temporal.lastrowid  # Retorna el ID de la cotización recién creada
            
    def insertar_detalle_contizacion(self, cotizacion_id, item_id, cantidad, precio_unitario, subtotal_linea):
        sql = """
            INSERT INTO cotizacion_detalles (cotizacion_id, item_id, cantidad, precio_unitario, subtotal_linea)
            VALUES (%s, %s, %s, %s, %s)
        """
        valores = (cotizacion_id, item_id, cantidad, precio_unitario, subtotal_linea)
        with self.db.conexion.cursor() as cursor_temporal:
            cursor_temporal.execute(sql, valores)
            self.db.conexion.commit()