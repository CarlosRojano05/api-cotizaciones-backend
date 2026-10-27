from mysql.connector import errors as mysql_errors

from models.cliente_model import ModelCliente
from utils.validaciones import texto


class ClienteService:
    def __init__(self):
        self.cliente = ModelCliente()

    def listar_clientes(self, empresa_id):
        return self.cliente.obtener_clientes(empresa_id)

    def listar_cliente(self, empresa_id, cliente_id):
        return self.cliente.obtener_un_cliente(empresa_id, cliente_id)

    def _leer_campos(self, datos):
        return (
            texto(datos.get("nombre")),
            texto(datos.get("identificacion")),
            texto(datos.get("telefono")),
            texto(datos.get("email")),
            texto(datos.get("direccion")),
        )

    def crear_cliente(self, empresa_id, datos):
        nombre, identificacion, telefono, email, direccion = self._leer_campos(datos)

        if not nombre or not identificacion:
            return {"error": "El nombre y la identificación son obligatorios"}, 400

        try:
            nuevo_id = self.cliente.insertar_cliente(
                empresa_id, nombre, identificacion, telefono, email, direccion
            )
        except mysql_errors.IntegrityError as e:
            if e.errno == 1062:  # choca con el índice único (empresa_id, identificacion)
                return {"error": "Ya existe un cliente con esa identificación"}, 409
            raise

        return {"mensaje": "Cliente creado exitosamente", "id": nuevo_id}, 201

    def actualizar_cliente(self, empresa_id, cliente_id, datos):
        nombre, identificacion, telefono, email, direccion = self._leer_campos(datos)

        if not nombre or not identificacion:
            return {"error": "El nombre y la identificación son obligatorios para actualizar"}, 400

        try:
            filas = self.cliente.actualizar_cliente(
                empresa_id, cliente_id, nombre, identificacion, telefono, email, direccion
            )
        except mysql_errors.IntegrityError as e:
            if e.errno == 1062:
                return {"error": "Ya existe otro cliente con esa identificación"}, 409
            raise

        if filas == 0:
            return {"error": f"No se encontró el cliente con el ID {cliente_id}"}, 404
        return {"mensaje": "Cliente actualizado exitosamente"}, 200

    def desactivar_cliente(self, empresa_id, cliente_id):
        if self.cliente.desactivar_cliente(empresa_id, cliente_id) == 0:
            return {"error": f"No se encontró el cliente activo con el ID {cliente_id}"}, 404
        return {"mensaje": "Cliente desactivado exitosamente (baja lógica aplicada)"}, 200
