import mysql.connector 

class ConexionMysql:
    def __init__(self):
         # 1. Creamos la conexión directamente en self.conexion
        self.conexion = mysql.connector.connect(
            host = "localhost",
            port = "3306",
            user = "root",
            password = "",
            database = "db_cotizaciones",
        )
       
        # El código a continuación NO es obligación, este código solo es para
        # confirmar la conexión con la base de datos.
        
        if self.conexion.is_connected():
            db_info = self.conexion.get_server_info()
            print("¡Conectada exitosamente a MySQL (db_cotizaciones)!")
            print("Conectada a la versión del servidor MySQL: ", db_info)

    # Código de cierre de conexión
    def cerrar_conexion(self):
     if self.conexion.is_connected():
        self.conexion.close()  # Cerramos de forma segura