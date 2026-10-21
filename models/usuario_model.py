from config.database import consultar, insertar, modificar


class ModelUsuario:
    def insertar_usuario(self, empresa_id, nombre, email, password_hash, rol, conn=None):
        sql = """
            INSERT INTO usuarios (empresa_id, nombre, email, password_hash, rol)
            VALUES (%s, %s, %s, %s, %s);
        """
        return insertar(sql, (empresa_id, nombre, email, password_hash, rol), conn)

    def obtener_por_email(self, email):
        """Solo para el login (necesita password_hash). El email es único en TODO el sistema."""
        sql = """
            SELECT u.id, u.empresa_id, u.nombre, u.email, u.password_hash, u.rol, u.activo,
                   e.nombre AS empresa_nombre
            FROM usuarios u
            INNER JOIN empresas e ON u.empresa_id = e.id
            WHERE u.email = %s;
        """
        return consultar(sql, (email,), uno=True)

    def obtener_por_id(self, empresa_id, usuario_id):
        sql = """
            SELECT u.id, u.nombre, u.email, u.rol, u.activo, e.nombre AS empresa_nombre
            FROM usuarios u
            INNER JOIN empresas e ON u.empresa_id = e.id
            WHERE u.id = %s AND u.empresa_id = %s;
        """
        return consultar(sql, (usuario_id, empresa_id), uno=True)

    def listar_usuarios(self, empresa_id):
        sql = """
            SELECT id, nombre, email, rol, activo
            FROM usuarios
            WHERE empresa_id = %s
            ORDER BY nombre;
        """
        return consultar(sql, (empresa_id,))

    def desactivar_usuario(self, empresa_id, usuario_id):
        sql = "UPDATE usuarios SET activo = 0 WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (usuario_id, empresa_id))
