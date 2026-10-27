"""
Genera el PDF comercial de una cotización con ReportLab.

Es una función "pura": recibe datos (diccionarios) y devuelve los bytes del PDF.
No toca la base de datos ni Flask, por eso es fácil de probar y de modificar.

Para cambiar el diseño (tipografías, márgenes, columnas) edita SOLO este archivo.
"""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

COLOR_PRINCIPAL_DEFECTO = "#1F4E79"
GRIS_TEXTO = colors.HexColor("#555555")
GRIS_LINEA = colors.HexColor("#D9D9D9")
GRIS_FONDO = colors.HexColor("#F5F6F8")
ROJO = colors.HexColor("#B42318")
MONEDAS_SIN_DECIMALES = {"COP", "CLP", "PYG", "JPY"}


# ----------------------------------------------------------------------
# Formato de números y textos
# ----------------------------------------------------------------------
def formatear_dinero(valor, moneda="COP"):
    """1234567.5 -> '$ 1.234.567,50'  (puntos para miles, coma para decimales)."""
    valor = Decimal(str(valor))
    # En monedas sin centavos (COP) se ocultan los decimales solo si el valor es exacto.
    sin_decimales = moneda in MONEDAS_SIN_DECIMALES and valor == valor.to_integral_value()
    texto = format(valor, ",.0f" if sin_decimales else ",.2f")
    texto = texto.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return f"$ {texto}"


def formatear_cantidad(valor):
    """2.00 -> '2'   2.50 -> '2,5'"""
    valor = Decimal(str(valor))
    if valor == valor.to_integral_value():
        return str(int(valor))
    return format(valor.normalize(), "f").replace(".", ",")


def formatear_porcentaje(valor):
    """19.00 -> '19'   5.50 -> '5,5'"""
    return format(Decimal(str(valor)).normalize(), "f").replace(".", ",")


def _fecha(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def _texto(valor):
    """Escapa el texto para que símbolos como < & > del usuario no rompan el PDF."""
    return escape(str(valor)).replace("\n", "<br/>")


# ----------------------------------------------------------------------
# Piezas del documento
# ----------------------------------------------------------------------
def _estilos(color):
    base = dict(fontName="Helvetica", fontSize=9, leading=12, textColor=colors.black)
    return {
        "normal": ParagraphStyle("normal", **base),
        "pequeno": ParagraphStyle("pequeno", **{**base, "fontSize": 8, "leading": 10, "textColor": GRIS_TEXTO}),
        "empresa": ParagraphStyle("empresa", **{**base, "fontName": "Helvetica-Bold", "fontSize": 13, "leading": 16, "textColor": color}),
        "titulo": ParagraphStyle("titulo", **{**base, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24, "textColor": color, "alignment": TA_RIGHT}),
        "numero": ParagraphStyle("numero", **{**base, "fontName": "Helvetica-Bold", "fontSize": 13, "leading": 16, "alignment": TA_RIGHT}),
        "derecha": ParagraphStyle("derecha", **{**base, "alignment": TA_RIGHT}),
        "etiqueta": ParagraphStyle("etiqueta", **{**base, "fontName": "Helvetica-Bold", "fontSize": 8, "textColor": color}),
        "th": ParagraphStyle("th", **{**base, "fontName": "Helvetica-Bold", "textColor": colors.white}),
        "th_der": ParagraphStyle("th_der", **{**base, "fontName": "Helvetica-Bold", "textColor": colors.white, "alignment": TA_RIGHT}),
        "item": ParagraphStyle("item", **{**base, "fontName": "Helvetica-Bold"}),
        "total": ParagraphStyle("total", **{**base, "fontName": "Helvetica-Bold", "fontSize": 11, "textColor": colors.white}),
        "total_der": ParagraphStyle("total_der", **{**base, "fontName": "Helvetica-Bold", "fontSize": 11, "textColor": colors.white, "alignment": TA_RIGHT}),
    }


def _imagen_ajustada(ruta, ancho_max, alto_max):
    """Carga el logo respetando su proporción dentro de una caja máxima."""
    ancho, alto = ImageReader(ruta).getSize()
    escala = min(ancho_max / ancho, alto_max / alto)
    return Image(ruta, width=ancho * escala, height=alto * escala, hAlign="LEFT")


def _bloque_empresa(empresa, ruta_logo, e):
    piezas = []
    if ruta_logo:
        try:
            piezas.append(_imagen_ajustada(ruta_logo, 55 * mm, 22 * mm))
            piezas.append(Spacer(1, 2 * mm))
        except Exception:
            pass  # si el logo está dañado, el PDF se genera igual, sin logo
    piezas.append(Paragraph(_texto(empresa["nombre"]), e["empresa"]))
    if empresa.get("nit"):
        piezas.append(Paragraph(f"NIT: {_texto(empresa['nit'])}", e["pequeno"]))
    for campo in ("direccion", "telefono", "email", "sitio_web"):
        if empresa.get(campo):
            piezas.append(Paragraph(_texto(empresa[campo]), e["pequeno"]))
    return piezas


def _bloque_cotizacion(cot, e):
    estado = cot["estado"]
    if cot.get("vencida"):
        estado_html = f'<font color="{ROJO.hexval().replace("0x", "#")}">Vencida</font>'
    else:
        estado_html = _texto(estado)
    return [
        Paragraph("COTIZACIÓN", e["titulo"]),
        Paragraph(_texto(cot["numero_formateado"]), e["numero"]),
        Spacer(1, 3 * mm),
        Paragraph(f"Fecha: <b>{_fecha(cot['fecha'])}</b>", e["derecha"]),
        Paragraph(f"Válida hasta: <b>{_fecha(cot['fecha_vencimiento'])}</b>", e["derecha"]),
        Paragraph(f"Estado: <b>{estado_html}</b>", e["derecha"]),
    ]


def _bloque_cliente(cot, e, ancho):
    lineas = [Paragraph("CLIENTE", e["etiqueta"]), Paragraph(f"<b>{_texto(cot['cliente_nombre'])}</b>", e["normal"])]
    lineas.append(Paragraph(f"Identificación: {_texto(cot['cliente_identificacion'])}", e["normal"]))
    for etiqueta, campo in (("Teléfono", "cliente_telefono"), ("Correo", "cliente_email"), ("Dirección", "cliente_direccion")):
        if cot.get(campo):
            lineas.append(Paragraph(f"{etiqueta}: {_texto(cot[campo])}", e["normal"]))
    tabla = Table([[lineas]], colWidths=[ancho])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tabla


def _tabla_items(cot, moneda, color, e, ancho):
    encabezado = [
        Paragraph("#", e["th"]), Paragraph("Descripción", e["th"]), Paragraph("Cant.", e["th_der"]),
        Paragraph("Valor unitario", e["th_der"]), Paragraph("Subtotal", e["th_der"]),
    ]
    filas = [encabezado]
    for i, d in enumerate(cot["detalles_cotizaciones"], start=1):
        descripcion = [Paragraph(_texto(d["item_nombre"]), e["item"])]
        if d.get("item_descripcion"):
            descripcion.append(Paragraph(_texto(d["item_descripcion"]), e["pequeno"]))
        filas.append([
            Paragraph(str(i), e["normal"]),
            descripcion,
            Paragraph(formatear_cantidad(d["cantidad"]), e["derecha"]),
            Paragraph(formatear_dinero(d["precio_unitario"], moneda), e["derecha"]),
            Paragraph(formatear_dinero(d["subtotal_linea"], moneda), e["derecha"]),
        ])

    anchos = [9 * mm, ancho - (9 + 16 + 34 + 34) * mm, 16 * mm, 34 * mm, 34 * mm]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)  # repeatRows: el encabezado se repite en cada página
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, GRIS_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla


def _tabla_totales(cot, moneda, color, e):
    iva = formatear_porcentaje(cot["iva_porcentaje"])
    filas = [[Paragraph("Subtotal", e["normal"]), Paragraph(formatear_dinero(cot["subtotal"], moneda), e["derecha"])]]
    if Decimal(str(cot["descuento"])) > 0:
        filas.append([Paragraph("Descuento", e["normal"]), Paragraph("- " + formatear_dinero(cot["descuento"], moneda), e["derecha"])])
    filas.append([Paragraph(f"IVA ({iva}%)", e["normal"]), Paragraph(formatear_dinero(cot["impuesto"], moneda), e["derecha"])])
    filas.append([Paragraph("TOTAL", e["total"]), Paragraph(formatear_dinero(cot["total"], moneda), e["total_der"])])

    tabla = Table(filas, colWidths=[40 * mm, 45 * mm], hAlign="RIGHT")
    tabla.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -3), 0.5, GRIS_LINEA),
        ("BACKGROUND", (0, -1), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _seccion_texto(titulo, contenido, e):
    return KeepTogether([
        Spacer(1, 5 * mm),
        Paragraph(titulo.upper(), e["etiqueta"]),
        Spacer(1, 1 * mm),
        Paragraph(_texto(contenido), e["normal"]),
    ])


# ----------------------------------------------------------------------
# Función principal
# ----------------------------------------------------------------------
def generar_pdf(empresa, cotizacion, ruta_logo=None):
    """
    empresa:    dict con nombre, nit, direccion, telefono, email, sitio_web,
                color_primario, moneda, condiciones
    cotizacion: dict como el que devuelve ModelCotizacion.obtener_cotizacion_por_id
    ruta_logo:  ruta del archivo del logo, o None
    Devuelve los bytes del PDF.
    """
    try:
        color = colors.HexColor(empresa.get("color_primario") or COLOR_PRINCIPAL_DEFECTO)
    except ValueError:
        color = colors.HexColor(COLOR_PRINCIPAL_DEFECTO)
    moneda = empresa.get("moneda") or "COP"
    e = _estilos(color)

    margen = 18 * mm
    ancho = A4[0] - 2 * margen
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=margen, rightMargin=margen, topMargin=15 * mm, bottomMargin=20 * mm,
        title=f"Cotización {cotizacion['numero_formateado']}", author=empresa["nombre"],
    )

    # Encabezado: datos de la empresa (izquierda) | datos de la cotización (derecha)
    encabezado = Table([[_bloque_empresa(empresa, ruta_logo, e), _bloque_cotizacion(cotizacion, e)]],
                       colWidths=[ancho * 0.55, ancho * 0.45])
    encabezado.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    historia = [
        encabezado,
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=1.5, color=color),
        Spacer(1, 5 * mm),
        _bloque_cliente(cotizacion, e, ancho),
        Spacer(1, 6 * mm),
        _tabla_items(cotizacion, moneda, color, e, ancho),
        Spacer(1, 4 * mm),
        KeepTogether(_tabla_totales(cotizacion, moneda, color, e)),
    ]
    if cotizacion.get("notas"):
        historia.append(_seccion_texto("Notas", cotizacion["notas"], e))
    if empresa.get("condiciones"):
        historia.append(_seccion_texto("Términos y condiciones", empresa["condiciones"], e))

    nombre_empresa = empresa["nombre"]
    numero = cotizacion["numero_formateado"]
    vigencia = _fecha(cotizacion["fecha_vencimiento"])

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRIS_TEXTO)
        canvas.setStrokeColor(GRIS_LINEA)
        canvas.line(margen, 15 * mm, A4[0] - margen, 15 * mm)
        canvas.drawString(margen, 10 * mm, f"{nombre_empresa}  |  Cotización {numero}  |  Válida hasta {vigencia}")
        canvas.drawRightString(A4[0] - margen, 10 * mm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()
