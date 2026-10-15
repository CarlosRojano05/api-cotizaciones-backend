from model.cliente_model import ModelCliente

class ClienteService:
    def __init__(self):
        self.cliente = ModelCliente()
        
    def listar_clientes(self):
        # Aquí podrías agregar lógica de negocio en el futuro (ej. ordenar alfabéticamente)
        return self.cliente.obtener_clientes()
    
    def crear_cliente(self, datos):
        # 1. Regla de negocio básica: Validar que los campos obligatorios vengan en el JSON
        nombre = datos.get('nombre')
        identificacion = datos.get('identificacion')
        telefono = datos.get('telefono', '')
        email = datos.get('email', '')
        direccion = datos.get('direccion', '')

        if not nombre or not identificacion:
            return {"error": "El nombre y la identificación son obligatorios"}, 400

        # 2. Si pasa la validación, llamamos al modelo para insertar en MySQL
        nuevo_id = self.cliente.insertar_clientes(nombre, identificacion, telefono, email, direccion)
        
        return {"mensaje": "Cliente creado exitosamente", "id": nuevo_id}, 201