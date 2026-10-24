from config.database import consultar, insertar, modificar

# Lista blanca: solo estas columnas se pueden cambiar desde la configuración.
CAMPOS_CONFIGURABLES = (
    "nombre", "nit", "direccion", "telefono", "email", "sitio_web", "color_primario",
    "moneda", "iva_defecto", "validez_dias", "prefijo", "condiciones",
)


class ModelEmpresa:
    """Cada empresa es un "inquilino" (tenant): un cliente tuyo que paga por el sistema."""

    def insertar_empresa(self, nombre, nit, conn=None):
        sql = "INSERT INTO empresas (nombre, nit) VALUES (%s, %s);"
        return insertar(sql, (nombre, nit), conn)

    def obtener_configuracion(self, empresa_id):
        sql = """
            SELECT id, nombre, nit, direccion, telefono, email, sitio_web, color_primario,
                   moneda, iva_defecto, validez_dias, prefijo, condiciones, logo_path
            FROM empresas
            WHERE id = %s;
        """
        return consultar(sql, (empresa_id,), uno=True)

    def actualizar_configuracion(self, empresa_id, campos):
        """
        Actualiza solo los campos enviados. Los NOMBRES de columna salen de la lista blanca
        (nunca del usuario) y los VALORES van como parámetros: no hay inyección SQL posible.
        """
        columnas = [c for c in campos if c in CAMPOS_CONFIGURABLES]
        if not columnas:
            return 0
        asignaciones = ", ".join(f"{c} = %s" for c in columnas)
        sql = f"UPDATE empresas SET {asignaciones} WHERE id = %s;"
        return modificar(sql, (*[campos[c] for c in columnas], empresa_id))

    def actualizar_logo(self, empresa_id, logo_path):
        sql = "UPDATE empresas SET logo_path = %s WHERE id = %s;"
        return modificar(sql, (logo_path, empresa_id))

    def reservar_numero(self, empresa_id, conn):
        """
        Entrega el siguiente número consecutivo de cotización de esta empresa.

        `FOR UPDATE` BLOQUEA la fila de la empresa hasta que termine la transacción.
        Si dos vendedores cotizan al mismo instante, el segundo espera su turno y
        recibe el número siguiente: es imposible que dos cotizaciones tengan el mismo.
        Y como el UPDATE está dentro de la transacción, si la cotización falla y se hace
        rollback, el número se "devuelve" y no quedan huecos.
        """
        fila = consultar(
            "SELECT ultimo_numero FROM empresas WHERE id = %s FOR UPDATE;",
            (empresa_id,), uno=True, conn=conn,
        )
        nuevo = fila["ultimo_numero"] + 1
        modificar("UPDATE empresas SET ultimo_numero = %s WHERE id = %s;", (nuevo, empresa_id), conn=conn)
        return nuevo
