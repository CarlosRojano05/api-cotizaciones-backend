from config.database import consultar, insertar


class ModelEmpresa:
    """Cada empresa es un "inquilino" (tenant): un cliente tuyo que paga por el sistema."""

    def insertar_empresa(self, nombre, nit, conn=None):
        sql = "INSERT INTO empresas (nombre, nit) VALUES (%s, %s);"
        return insertar(sql, (nombre, nit), conn)

    def obtener_empresa(self, empresa_id):
        sql = "SELECT id, nombre, nit, moneda FROM empresas WHERE id = %s;"
        return consultar(sql, (empresa_id,), uno=True)
