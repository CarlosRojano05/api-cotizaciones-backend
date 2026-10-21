from config.database import consultar, insertar, modificar


class ModelCliente:
    """
    REGLA DE ORO: toda consulta lleva `empresa_id = %s`.
    Es lo que impide que la empresa A vea o modifique clientes de la empresa B.
    """

    def obtener_clientes(self, empresa_id):
        sql = """
            SELECT id, nombre, identificacion, telefono, email, direccion
            FROM clientes
            WHERE empresa_id = %s AND activo = 1
            ORDER BY nombre;
        """
        return consultar(sql, (empresa_id,))

    def obtener_un_cliente(self, empresa_id, cliente_id):
        sql = """
            SELECT id, nombre, identificacion, telefono, email, direccion
            FROM clientes
            WHERE id = %s AND empresa_id = %s AND activo = 1;
        """
        return consultar(sql, (cliente_id, empresa_id), uno=True)

    def insertar_cliente(self, empresa_id, nombre, identificacion, telefono, email, direccion):
        sql = """
            INSERT INTO clientes (empresa_id, nombre, identificacion, telefono, email, direccion)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        return insertar(sql, (empresa_id, nombre, identificacion, telefono, email, direccion))

    def actualizar_cliente(self, empresa_id, cliente_id, nombre, identificacion, telefono, email, direccion):
        sql = """
            UPDATE clientes
            SET nombre = %s, identificacion = %s, telefono = %s, email = %s, direccion = %s
            WHERE id = %s AND empresa_id = %s AND activo = 1;
        """
        return modificar(sql, (nombre, identificacion, telefono, email, direccion, cliente_id, empresa_id))

    def desactivar_cliente(self, empresa_id, cliente_id):
        sql = "UPDATE clientes SET activo = 0 WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (cliente_id, empresa_id))
