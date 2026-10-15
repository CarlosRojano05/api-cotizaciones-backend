from config.conexion import ConexionMysql

class ModelCliente:
    def __init__(self):
        # Al poner (), Python ejecuta el __init__ de ConexionMysql 
        # y crea la conexión y el cursor reales.
       self.db = ConexionMysql()
       
    def obtener_clientes(self):
        
        sql = "SELECT id, nombre, identificacion, telefono, email, direccion FROM clientes WHERE activo = 1;"
                    
        # Solo llamas a la función, el 'with' de adentro se encarga del resto
                      #Agregamos dictionary=True dentro del cursor()
        with self.db.conexion.cursor(dictionary=True) as cursor_temporal:
            cursor_temporal.execute(sql)
            return cursor_temporal.fetchall() # Recuerda retornar los datos.
        
    def insertar_clientes(self, nombre, identificacion, telefono, email, direccion):
        
        sql = """
                    INSERT INTO clientes (nombre, identificacion, telefono, email, direccion) 
                    VALUES (%s, %s, %s, %s, %s)
        
             """
        
        valores = (nombre, identificacion, telefono, email, direccion)
         
        # 2. Usamos el 'with' con la conexión directa para crear un cursor temporal
        with self.db.conexion.cursor() as cursor_temporal:
            cursor_temporal.execute(sql, valores,)
            
        # 3. ¡EL PASO CLAVE! Confirmamos la inserción en la base de datos
            self.db.conexion.commit()
            
        # 4. Retorna el No id asignado al Insert 
            return cursor_temporal.lastrowid