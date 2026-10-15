from model.item_model import ModelItem

class ItemService:
    def __init__(self):
        self.item = ModelItem()
        
    def listar_items(self):
        # Aquí podrías agregar lógica de negocio en el futuro (ej. ordenar alfabéticamente)
        return self.item.obtener_items()
    
    def crear_item(self, datos):
        # 1. Regla de negocio básica: Validar que los campos obligatorios vengan en el JSON
        nombre = datos.get('nombre')
        descripcion = datos.get('descripcion','')
        precio_unitario = datos.get('precio_unitario')
        tipo = datos.get('tipo')

        if not nombre or not precio_unitario or not tipo:
            return {"error": "El nombre, precio unitario y tipo son obligatorios"}, 400

        # 2. Si pasa la validación, llamamos al modelo para insertar en MySQL
        nuevo_id = self.item.insertar_item(nombre, descripcion, precio_unitario, tipo)
        
        return {"mensaje": "Item creado exitosamente", "id": nuevo_id}, 201