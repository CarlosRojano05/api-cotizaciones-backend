from models.item_model import ModelItem
from utils.dinero import a_decimal, redondear
from utils.validaciones import texto

TIPOS_PERMITIDOS = ("producto", "servicio")


class ItemService:
    def __init__(self):
        self.item = ModelItem()

    def listar_items(self, empresa_id):
        return self.item.obtener_items(empresa_id)

    def _validar(self, datos):
        """Devuelve (campos, None) si todo está bien, o (None, mensaje_de_error)."""
        nombre = texto(datos.get("nombre"))
        descripcion = texto(datos.get("descripcion"))
        tipo = texto(datos.get("tipo"))

        if not nombre or not tipo:
            return None, "El nombre, el precio unitario y el tipo son obligatorios"
        if tipo not in TIPOS_PERMITIDOS:
            return None, f"Tipo inválido. Los tipos permitidos son: {list(TIPOS_PERMITIDOS)}"
        try:
            precio = a_decimal(datos.get("precio_unitario"), "precio_unitario")
        except ValueError as e:
            return None, str(e)
        if precio < 0:  # un precio de 0 es válido (ej. servicio sin costo); negativo no
            return None, "El precio unitario no puede ser negativo"

        return (nombre, descripcion, redondear(precio), tipo), None

    def crear_item(self, empresa_id, datos):
        campos, error = self._validar(datos)
        if error:
            return {"error": error}, 400
        nuevo_id = self.item.insertar_item(empresa_id, *campos)
        return {"mensaje": "Ítem creado exitosamente", "id": nuevo_id}, 201

    def actualizar_item(self, empresa_id, item_id, datos):
        campos, error = self._validar(datos)
        if error:
            return {"error": error}, 400
        if self.item.actualizar_item(empresa_id, item_id, *campos) == 0:
            return {"error": f"No se encontró el ítem con el ID {item_id}"}, 404
        return {"mensaje": "Ítem actualizado exitosamente"}, 200

    def desactivar_item(self, empresa_id, item_id):
        if self.item.desactivar_item(empresa_id, item_id) == 0:
            return {"error": f"No se encontró el ítem activo con el ID {item_id}"}, 404
        return {"mensaje": "Ítem desactivado exitosamente (baja lógica aplicada)"}, 200
