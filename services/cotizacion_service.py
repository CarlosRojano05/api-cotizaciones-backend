from decimal import Decimal

from config.database import transaccion
from models.cliente_model import ModelCliente
from models.cotizacion_model import ModelCotizacion
from models.item_model import ModelItem
from utils.dinero import a_decimal, redondear

ESTADOS_PERMITIDOS = ("Pendiente", "Aceptada", "Rechazada")

# TEMPORAL: en el paso 3 este valor saldrá de la configuración de cada empresa.
TASA_IVA = Decimal("0.19")


class CotizacionService:
    def __init__(self):
        self.cotizacion = ModelCotizacion()
        self.cliente = ModelCliente()
        self.item = ModelItem()

    def listar_cotizaciones(self, empresa_id):
        return self.cotizacion.obtener_cotizaciones(empresa_id)

    def _preparar_lineas(self, empresa_id, items_enviados):
        """
        Valida cada línea y calcula sus montos con Decimal.
        Lanza ValueError (con mensaje claro) si algo está mal.
        """
        ids = []
        for linea in items_enviados:
            if not isinstance(linea, dict) or not isinstance(linea.get("item_id"), int):
                raise ValueError("Cada ítem debe incluir un 'item_id' numérico")
            ids.append(linea["item_id"])

        # SEGURIDAD: solo existen los ítems que pertenecen a ESTA empresa y están activos.
        catalogo = {i["id"]: i for i in self.item.obtener_items_por_ids(empresa_id, tuple(set(ids)))}

        lineas = []
        for linea in items_enviados:
            item_id = linea["item_id"]
            if item_id not in catalogo:
                raise ValueError(f"El ítem {item_id} no existe o está inactivo")

            cantidad = a_decimal(linea.get("cantidad", 1), "cantidad")
            # Si no envían precio, se usa el del catálogo.
            precio = a_decimal(
                linea.get("precio_unitario", catalogo[item_id]["precio_unitario"]), "precio_unitario"
            )
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor que 0")
            if precio < 0:
                raise ValueError("El precio unitario no puede ser negativo")

            cantidad, precio = redondear(cantidad), redondear(precio)
            lineas.append({
                "item_id": item_id,
                "cantidad": cantidad,
                "precio_unitario": precio,
                "subtotal_linea": redondear(cantidad * precio),
            })
        return lineas

    def crear_cotizacion(self, empresa_id, usuario_id, datos):
        cliente_id = datos.get("cliente_id")
        items_enviados = datos.get("items")

        if not isinstance(cliente_id, int) or not isinstance(items_enviados, list) or not items_enviados:
            return {"error": "El cliente y al menos un ítem son obligatorios para cotizar"}, 400

        # SEGURIDAD: el cliente debe ser de esta empresa.
        if not self.cliente.obtener_un_cliente(empresa_id, cliente_id):
            return {"error": "El cliente no existe o está inactivo"}, 400

        try:
            descuento = a_decimal(datos.get("descuento") or 0, "descuento")
            lineas = self._preparar_lineas(empresa_id, items_enviados)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Cálculos comerciales (todo en Decimal)
        subtotal = sum((l["subtotal_linea"] for l in lineas), Decimal("0"))
        if descuento < 0 or descuento > subtotal:
            return {"error": "El descuento no puede ser negativo ni mayor al subtotal"}, 400

        descuento = redondear(descuento)
        base = subtotal - descuento
        impuesto = redondear(base * TASA_IVA)
        total = base + impuesto

        # UNA transacción: cabecera + líneas se guardan juntas o no se guarda nada.
        with transaccion() as conn:
            cotizacion_id = self.cotizacion.insertar_cabecera(
                empresa_id, usuario_id, cliente_id, subtotal, descuento, impuesto, total, conn
            )
            self.cotizacion.insertar_detalles(cotizacion_id, lineas, conn)

        return {
            "mensaje": "Cotización creada exitosamente",
            "cotizacion_id": cotizacion_id,
            "resumen_financiero": {
                "subtotal": subtotal,
                "descuento": descuento,
                "impuesto_iva": impuesto,
                "total": total,
            },
        }, 201

    def actualizar_estado(self, empresa_id, cotizacion_id, nuevo_estado):
        if nuevo_estado not in ESTADOS_PERMITIDOS:
            return {"error": f"Estado inválido. Los permitidos son: {list(ESTADOS_PERMITIDOS)}"}, 400

        if self.cotizacion.actualizar_estado(empresa_id, cotizacion_id, nuevo_estado) == 0:
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404
        return {"mensaje": f"Cotización actualizada exitosamente a '{nuevo_estado}'"}, 200

    def obtener_cotizacion_detalle(self, empresa_id, cotizacion_id):
        cotizacion = self.cotizacion.obtener_cotizacion_por_id(empresa_id, cotizacion_id)
        if not cotizacion:
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404
        return cotizacion, 200
