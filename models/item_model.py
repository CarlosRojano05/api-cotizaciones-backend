from config.database import consultar, insertar, modificar


class ModelItem:
    """Catálogo de productos y servicios. Siempre filtrado por empresa."""

    def obtener_items(self, empresa_id):
        sql = """
            SELECT id, nombre, descripcion, precio_unitario, tipo
            FROM items
            WHERE empresa_id = %s AND activo = 1
            ORDER BY nombre;
        """
        return consultar(sql, (empresa_id,))

    def obtener_items_por_ids(self, empresa_id, ids):
        """Trae varios ítems de una sola vez (los usa la cotización para validar sus líneas)."""
        if not ids:
            return []
        # Creamos un %s por cada id:  IN (%s, %s, %s)
        # Seguimos usando parámetros (no pegamos los valores en el texto), así que es seguro.
        marcadores = ", ".join(["%s"] * len(ids))
        sql = f"""
            SELECT id, nombre, precio_unitario
            FROM items
            WHERE empresa_id = %s AND activo = 1 AND id IN ({marcadores});
        """
        return consultar(sql, (empresa_id, *ids))

    def insertar_item(self, empresa_id, nombre, descripcion, precio_unitario, tipo):
        sql = """
            INSERT INTO items (empresa_id, nombre, descripcion, precio_unitario, tipo)
            VALUES (%s, %s, %s, %s, %s);
        """
        return insertar(sql, (empresa_id, nombre, descripcion, precio_unitario, tipo))

    def actualizar_item(self, empresa_id, item_id, nombre, descripcion, precio_unitario, tipo):
        sql = """
            UPDATE items
            SET nombre = %s, descripcion = %s, precio_unitario = %s, tipo = %s
            WHERE id = %s AND empresa_id = %s AND activo = 1;
        """
        return modificar(sql, (nombre, descripcion, precio_unitario, tipo, item_id, empresa_id))

    def desactivar_item(self, empresa_id, item_id):
        sql = "UPDATE items SET activo = 0 WHERE id = %s AND empresa_id = %s AND activo = 1;"
        return modificar(sql, (item_id, empresa_id))
