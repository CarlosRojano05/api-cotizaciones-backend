from model.contizacion_model import ModelCotizacion

class CotizacionService:
    def __init__(self):
        self.cotizacion = ModelCotizacion()

    def listar_cotizaciones(self):
        return self.cotizacion.obtener_cotizaciones()
    
    def crear_cotizacion(self, datos):
        cliente_id = datos.get('cliente_id')
        items_cotizacion = datos.get('items', []) # Lista de productos/servicios elegidos
        descuento_global = datos.get('descuento', 0.00)

        # 1. Validación de negocio básica
        if not cliente_id or not items_cotizacion:
            return {"error": "El cliente y al menos un ítem son obligatorios para cotizar"}, 400

        subtotal_acumulado = 0.00
        detalles_procesados = []

        # 2. Procesamos y calculamos cada línea de la cotización
        for item in items_cotizacion:
            item_id = item.get('item_id')
            cantidad = float(item.get('cantidad', 1))
            precio_unitario = float(item.get('precio_unitario', 0))

            if not item_id or precio_unitario <= 0:
                return {"error": "Cada ítem debe tener un ID válido y un precio mayor a 0"}, 400

            subtotal_linea = cantidad * precio_unitario
            subtotal_acumulado += subtotal_linea

            detalles_procesados.append({
                "item_id": item_id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal_linea": subtotal_linea
            })

        # 3. Aplicamos cálculos comerciales (Subtotal - Descuento + Impuesto 19% IVA por ejemplo)
        subtotal_neto = subtotal_acumulado - float(descuento_global)
        if subtotal_neto < 0:
            subtotal_neto = 0.00

        # Calculamos un IVA estándar del 19% (puedes ajustarlo o hacerlo dinámico luego)
        impuesto_iva = subtotal_neto * 0.19 
        total_final = subtotal_neto + impuesto_iva

        # 4. Guardamos la Cabecera en la Base de Datos
        cotizacion_id = self.cotizacion.ingresar_cotizacion(
            cliente_id, 
            subtotal_acumulado, 
            descuento_global, 
            impuesto_iva, 
            total_final
        )

        # 5. Guardamos cada Línea de Detalle vinculada a esa cabecera
        for det in detalles_procesados:
            self.cotizacion.insertar_detalle_contizacion(
                cotizacion_id,
                det["item_id"],
                det["cantidad"],
                det["precio_unitario"],
                det["subtotal_linea"]
            )

        return {
            "mensaje": "Cotización creada exitosamente",
            "cotizacion_id": cotizacion_id,
            "resumen_financiero": {
                "subtotal": round(subtotal_acumulado, 2),
                "descuento": round(float(descuento_global), 2),
                "impuesto_iva": round(impuesto_iva, 2),
                "total": round(total_final, 2)
            }
        }, 201