from datetime import date, timedelta
from decimal import Decimal

from config.database import transaccion
from models.cliente_model import ModelCliente
from models.cotizacion_model import ModelCotizacion
from models.empresa_model import ModelEmpresa
from models.historial_model import ModelHistorial
from models.item_model import ModelItem
from services.empresa_service import EmpresaService
from utils.constantes import ESTADOS_PERMITIDOS
from utils.dinero import a_decimal, redondear
from utils.pdf_cotizacion import generar_pdf
from utils.validaciones import formatear_numero, texto

LARGO_MAXIMO_NOTAS = 2000
LARGO_MAXIMO_COMENTARIO = 255


class CotizacionService:
    def __init__(self):
        self.cotizacion = ModelCotizacion()
        self.cliente = ModelCliente()
        self.item = ModelItem()
        self.empresa = ModelEmpresa()
        self.historial = ModelHistorial()
        self.empresa_service = EmpresaService()

    def listar_cotizaciones(self, empresa_id, filtros=None):
        """
        filtros (todos opcionales): estado, cliente_id, vencidas ("1"), buscar.
        Llegan como texto desde la URL (?estado=Pendiente&cliente_id=3), así que se validan aquí.
        """
        filtros = filtros or {}
        estado = filtros.get("estado")
        if estado and estado not in ESTADOS_PERMITIDOS:
            return {"error": f"Estado inválido. Los permitidos son: {list(ESTADOS_PERMITIDOS)}"}, 400

        cliente_id = filtros.get("cliente_id")
        if cliente_id:
            if not str(cliente_id).isdigit():
                return {"error": "'cliente_id' debe ser un número"}, 400
            cliente_id = int(cliente_id)

        lista = self.cotizacion.obtener_cotizaciones(
            empresa_id,
            estado=estado or None,
            cliente_id=cliente_id or None,
            solo_vencidas=filtros.get("vencidas") in ("1", "true"),
            buscar=texto(filtros.get("buscar")) or None,
        )
        return lista, 200

    # ------------------------------------------------------------------
    # Lectura y validación de los datos opcionales (IVA, vencimiento, notas)
    # ------------------------------------------------------------------
    def _leer_iva(self, datos, iva_defecto):
        """IVA de esta cotización: el que envíen, o si no, el de la empresa. 0 es válido (exento)."""
        enviado = datos.get("iva_porcentaje")
        iva = a_decimal(iva_defecto if enviado is None else enviado, "iva_porcentaje")
        if iva < 0 or iva > 100:
            raise ValueError("'iva_porcentaje' debe estar entre 0 y 100")
        return redondear(iva)

    def _leer_vencimiento(self, datos, validez_dias):
        """Fecha enviada (AAAA-MM-DD) o, si no, hoy + días de validez de la empresa."""
        hoy = date.today()
        enviada = datos.get("fecha_vencimiento")
        if enviada is None or enviada == "":
            return hoy + timedelta(days=validez_dias)
        try:
            fecha = date.fromisoformat(enviada)
        except (TypeError, ValueError):
            raise ValueError("'fecha_vencimiento' debe tener el formato AAAA-MM-DD (ej. 2026-11-30)")
        if fecha < hoy:
            raise ValueError("La fecha de vencimiento no puede estar en el pasado")
        return fecha

    def _leer_notas(self, datos):
        notas = texto(datos.get("notas"))
        if len(notas) > LARGO_MAXIMO_NOTAS:
            raise ValueError(f"Las notas no pueden superar {LARGO_MAXIMO_NOTAS} caracteres")
        return notas or None

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

    # ------------------------------------------------------------------
    def crear_cotizacion(self, empresa_id, usuario_id, datos):
        cliente_id = datos.get("cliente_id")
        items_enviados = datos.get("items")

        if not isinstance(cliente_id, int) or not isinstance(items_enviados, list) or not items_enviados:
            return {"error": "El cliente y al menos un ítem son obligatorios para cotizar"}, 400

        # SEGURIDAD: el cliente debe ser de esta empresa.
        if not self.cliente.obtener_un_cliente(empresa_id, cliente_id):
            return {"error": "El cliente no existe o está inactivo"}, 400

        # Preferencias comerciales de la empresa (IVA, validez, prefijo)
        empresa = self.empresa.obtener_configuracion(empresa_id)

        try:
            descuento = a_decimal(datos.get("descuento") or 0, "descuento")
            iva_porcentaje = self._leer_iva(datos, empresa["iva_defecto"])
            fecha_vencimiento = self._leer_vencimiento(datos, empresa["validez_dias"])
            notas = self._leer_notas(datos)
            lineas = self._preparar_lineas(empresa_id, items_enviados)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Cálculos comerciales (todo en Decimal)
        subtotal = sum((l["subtotal_linea"] for l in lineas), Decimal("0"))
        if descuento < 0 or descuento > subtotal:
            return {"error": "El descuento no puede ser negativo ni mayor al subtotal"}, 400

        descuento = redondear(descuento)
        base = subtotal - descuento
        impuesto = redondear(base * iva_porcentaje / Decimal(100))
        total = base + impuesto

        # UNA transacción: número + cabecera + líneas se guardan juntos o no se guarda nada.
        with transaccion() as conn:
            numero = self.empresa.reservar_numero(empresa_id, conn)
            cotizacion_id = self.cotizacion.insertar_cabecera(
                empresa_id=empresa_id, usuario_id=usuario_id, cliente_id=cliente_id,
                numero=numero, fecha_vencimiento=fecha_vencimiento, iva_porcentaje=iva_porcentaje,
                subtotal=subtotal, descuento=descuento, impuesto=impuesto, total=total,
                notas=notas, conn=conn,
            )
            self.cotizacion.insertar_detalles(cotizacion_id, lineas, conn)
            self.historial.registrar(cotizacion_id, usuario_id, None, "Pendiente", "Cotización creada", conn)

        return {
            "mensaje": "Cotización creada exitosamente",
            "cotizacion_id": cotizacion_id,
            "numero": numero,
            "numero_formateado": formatear_numero(empresa["prefijo"], numero),
            "fecha_vencimiento": fecha_vencimiento,
            "resumen_financiero": {
                "subtotal": subtotal,
                "descuento": descuento,
                "iva_porcentaje": iva_porcentaje,
                "impuesto_iva": impuesto,
                "total": total,
            },
        }, 201

    def actualizar_estado(self, empresa_id, usuario_id, cotizacion_id, nuevo_estado, comentario=None):
        if nuevo_estado not in ESTADOS_PERMITIDOS:
            return {"error": f"Estado inválido. Los permitidos son: {list(ESTADOS_PERMITIDOS)}"}, 400

        comentario = texto(comentario) or None
        if comentario and len(comentario) > LARGO_MAXIMO_COMENTARIO:
            return {"error": f"El comentario no puede superar {LARGO_MAXIMO_COMENTARIO} caracteres"}, 400

        # Cambio de estado + registro en el historial: juntos o ninguno.
        with transaccion() as conn:
            # bloquear=True: si dos personas cambian la misma cotización a la vez, esperan turno.
            actual = self.cotizacion.obtener_estado(empresa_id, cotizacion_id, conn, bloquear=True)
            if not actual:
                return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404

            if actual["estado"] == nuevo_estado:
                return {"mensaje": f"La cotización ya estaba en '{nuevo_estado}'. No se registró ningún cambio"}, 200

            self.cotizacion.actualizar_estado(empresa_id, cotizacion_id, nuevo_estado, conn)
            self.historial.registrar(cotizacion_id, usuario_id, actual["estado"], nuevo_estado, comentario, conn)

        return {"mensaje": f"Cotización actualizada exitosamente a '{nuevo_estado}'"}, 200

    def obtener_historial(self, empresa_id, cotizacion_id):
        if not self.cotizacion.obtener_estado(empresa_id, cotizacion_id):
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404
        return self.historial.listar(empresa_id, cotizacion_id), 200

    def anular_cotizacion(self, empresa_id, cotizacion_id):
        if self.cotizacion.anular(empresa_id, cotizacion_id) == 0:
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404
        return {"mensaje": "Cotización anulada exitosamente"}, 200

    def obtener_cotizacion_detalle(self, empresa_id, cotizacion_id):
        cotizacion = self.cotizacion.obtener_cotizacion_por_id(empresa_id, cotizacion_id)
        if not cotizacion:
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404
        return cotizacion, 200

    def generar_pdf(self, empresa_id, cotizacion_id):
        """Devuelve ((bytes_del_pdf, nombre_de_archivo), 200) o ({error}, 404)."""
        cotizacion = self.cotizacion.obtener_cotizacion_por_id(empresa_id, cotizacion_id)
        if not cotizacion:
            return {"error": f"No se encontró la cotización con el ID {cotizacion_id}"}, 404

        empresa = self.empresa.obtener_configuracion(empresa_id)
        ruta_logo = self.empresa_service.resolver_ruta_logo(empresa["logo_path"])  # sin otra consulta
        contenido = generar_pdf(empresa, cotizacion, ruta_logo)
        return (contenido, f"{cotizacion['numero_formateado']}.pdf"), 200
