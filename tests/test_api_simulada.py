"""
Prueba automática de la API completa con base de datos y JWT SIMULADOS.

No necesita MySQL ni internet: reemplaza la base de datos por funciones falsas y comprueba
rutas, roles, validaciones, aislamiento entre empresas, historial, PDF, logo y panel.

Cómo correrla (desde la carpeta del proyecto):
    python tests/test_api_simulada.py

Debe terminar con:  TODAS LAS PRUEBAS FINALES PASARON
Córrela cada vez que modifiques el backend: si algo se rompió, lo verás de inmediato.
(No reemplaza probar con MySQL real: eso lo haces con la colección de Postman.)
"""
import io, os, sys, types, tempfile, shutil
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal

TMP = tempfile.mkdtemp()
os.environ["JWT_SECRET_KEY"] = "x" * 40
os.environ["UPLOADS_DIR"] = TMP
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------- Simulación de librerías que no están en este entorno ----------
mysql = types.ModuleType("mysql"); conn_mod = types.ModuleType("mysql.connector")
errors = types.ModuleType("mysql.connector.errors")
class IntegrityError(Exception): errno = 1062
class DataError(Exception): pass
errors.IntegrityError = IntegrityError; errors.DataError = DataError
conn_mod.errors = errors; mysql.connector = conn_mod
conn_mod.ClientFlag = types.SimpleNamespace(FOUND_ROWS=2); conn_mod.pooling = types.SimpleNamespace()
sys.modules.update({"mysql": mysql, "mysql.connector": conn_mod, "mysql.connector.errors": errors})
sys.modules["flask_cors"] = types.SimpleNamespace(CORS=lambda *a, **k: None)

from flask import request, abort, g
jwt = types.ModuleType("flask_jwt_extended")
class JWTManager:
    def __init__(self, app=None): pass
    def __getattr__(self, n): return lambda f: f
def _claims():
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer "): abort(401)
    uid, emp, rol = h[7:].split(":")
    return {"sub": uid, "empresa_id": int(emp), "rol": rol}
jwt.JWTManager = JWTManager
jwt.create_access_token = lambda identity, additional_claims: f"{identity}:{additional_claims['empresa_id']}:{additional_claims['rol']}"
jwt.verify_jwt_in_request = lambda: _claims()
jwt.get_jwt = lambda: _claims()
jwt.get_jwt_identity = lambda: _claims()["sub"]
sys.modules["flask_jwt_extended"] = jwt

import services.cotizacion_service as cs
import services.dashboard_service as ds
import services.auth_service as au
import controllers.cotizacion_controller as cc
import controllers.empresa_controller as ec
import controllers.dashboard_controller as dc
import controllers.auth_controller as ac
from app import app

log = []
@contextmanager
def fake_tx():
    log.append("BEGIN")
    try: yield "CONN"
    except Exception: log.append("ROLLBACK"); raise
    log.append("COMMIT")
cs.transaccion = fake_tx; au.transaccion = fake_tx

ADMIN = {"Authorization": "Bearer 1:1:admin"}
VENDEDOR = {"Authorization": "Bearer 2:1:vendedor"}
OTRA = {"Authorization": "Bearer 9:2:admin"}
cli = app.test_client()
def ok(cond, msg=""): assert cond, msg

# =============== 1. Seguridad de rutas ===============
ok(cli.get("/cotizaciones").status_code == 401)
r = cli.get("/ruta-que-no-existe"); ok(r.status_code == 404 and r.get_json()["error"] == "El recurso solicitado no existe")
r = cli.delete("/cotizaciones/1", headers=VENDEDOR); ok(r.status_code == 403, r.data)
r = cli.put("/empresa/configuracion", json={"nombre": "X"}, headers=VENDEDOR); ok(r.status_code == 403)
r = cli.post("/empresa/logo", headers=VENDEDOR); ok(r.status_code == 403)
r = cli.put("/usuarios/3/password", json={"password_nueva": "abcdefgh"}, headers=VENDEDOR); ok(r.status_code == 403)
ok(cli.get("/salud").get_json() == {"estado": "ok"})

# =============== 2. Cotizaciones: crear + historial ===============
svc = cc.cotizacion_service
EMPRESA = {"id": 1, "nombre": "Ferretería El Tornillo S.A.S.", "nit": "900123456-1", "direccion": "Calle 45", "telefono": "300",
           "email": "v@e.com", "sitio_web": None, "color_primario": "#1F4E79", "moneda": "COP", "iva_defecto": Decimal("19.00"),
           "validez_dias": 15, "prefijo": "FER", "condiciones": "Pago 50% anticipado", "logo_path": None}
contador = {"n": 0}; historial = []; guardado = {}
svc.empresa.obtener_configuracion = lambda emp: dict(EMPRESA) if emp == 1 else None
svc.empresa.reservar_numero = lambda emp, conn: contador.__setitem__("n", contador["n"] + 1) or contador["n"]
svc.cliente.obtener_un_cliente = lambda emp, cid: {"id": cid} if (emp, cid) == (1, 1) else None
catalogo = {1: {"id": 1, "nombre": "MO", "precio_unitario": Decimal("85000")}, 2: {"id": 2, "nombre": "Kit", "precio_unitario": Decimal("125000")}}
svc.item.obtener_items_por_ids = lambda emp, ids: [catalogo[i] for i in ids if emp == 1 and i in catalogo]
svc.cotizacion.insertar_cabecera = lambda **kw: (guardado.update(kw), 7)[1]
svc.cotizacion.insertar_detalles = lambda cid, l, c: None
svc.historial.registrar = lambda cid, uid, ant, nue, com, conn: historial.append((cid, uid, ant, nue, com))

cuerpo = {"cliente_id": 1, "descuento": 10000, "items": [{"item_id": 1, "cantidad": 2}, {"item_id": 2, "precio_unitario": 150000}]}
r = cli.post("/cotizaciones", json=cuerpo, headers=VENDEDOR); j = r.get_json()
ok(r.status_code == 201, j)
ok(j["numero_formateado"] == "FER-0001" and j["resumen_financiero"]["total"] == 368900.0, j)
ok(historial == [(7, 2, None, "Pendiente", "Cotización creada")], historial)  # quedó registrada la creación
ok(guardado["usuario_id"] == 2 and guardado["empresa_id"] == 1)
ok(cli.post("/cotizaciones", json=cuerpo, headers=OTRA).status_code == 400)   # otra empresa: no ve cliente/ítems
ok(cli.post("/cotizaciones", data="no json", headers=ADMIN).status_code == 400)

# =============== 3. Cambio de estado + historial ===============
estados = {5: "Pendiente"}; historial.clear(); log.clear()
svc.cotizacion.obtener_estado = lambda emp, cid, conn=None, bloquear=False: {"id": cid, "estado": estados[cid]} if emp == 1 and cid in estados else None
def cambiar(emp, cid, est, conn): estados[cid] = est; return 1
svc.cotizacion.actualizar_estado = cambiar

r = cli.patch("/cotizaciones/5/estado", json={"estado": "Aceptada", "comentario": "  Cliente confirmó por WhatsApp "}, headers=VENDEDOR)
ok(r.status_code == 200 and estados[5] == "Aceptada", r.data)
ok(historial == [(5, 2, "Pendiente", "Aceptada", "Cliente confirmó por WhatsApp")], historial)
ok(log == ["BEGIN", "COMMIT"], log)
r = cli.patch("/cotizaciones/5/estado", json={"estado": "Aceptada"}, headers=VENDEDOR)   # mismo estado: no se duplica el historial
ok(r.status_code == 200 and "ya estaba" in r.get_json()["mensaje"] and len(historial) == 1)
ok(cli.patch("/cotizaciones/5/estado", json={"estado": "Inventado"}, headers=ADMIN).status_code == 400)
ok(cli.patch("/cotizaciones/5/estado", json={"estado": "Rechazada", "comentario": "x" * 256}, headers=ADMIN).status_code == 400)
ok(cli.patch("/cotizaciones/99/estado", json={"estado": "Rechazada"}, headers=ADMIN).status_code == 404)
ok(cli.patch("/cotizaciones/5/estado", json={"estado": "Rechazada"}, headers=OTRA).status_code == 404)  # otra empresa
ok(cli.patch("/cotizaciones/5/estado", json={"sin": "estado"}, headers=ADMIN).status_code == 400)

svc.historial.listar = lambda emp, cid: [{"id": 1, "estado_anterior": None, "estado_nuevo": "Pendiente", "comentario": "Cotización creada",
                                          "fecha": datetime(2026, 10, 23, 9, 0), "usuario_nombre": "Carlos"}]
r = cli.get("/cotizaciones/5/historial", headers=VENDEDOR); ok(r.status_code == 200 and r.get_json()[0]["fecha"] == "2026-10-23T09:00:00", r.data)
ok(cli.get("/cotizaciones/99/historial", headers=ADMIN).status_code == 404)

# Anular
svc.cotizacion.anular = lambda emp, cid: 1 if (emp, cid) == (1, 5) else 0
ok(cli.delete("/cotizaciones/5", headers=ADMIN).status_code == 200)
ok(cli.delete("/cotizaciones/6", headers=ADMIN).status_code == 404)

# =============== 4. Listado con filtros ===============
visto = {}
def listar(emp, **kw): visto.update(kw, emp=emp); return []
svc.cotizacion.obtener_cotizaciones = listar
r = cli.get("/cotizaciones?estado=Pendiente&cliente_id=3&vencidas=1&buscar=%20andina%20", headers=ADMIN)
ok(r.status_code == 200 and visto == {"estado": "Pendiente", "cliente_id": 3, "solo_vencidas": True, "buscar": "andina", "emp": 1}, visto)
visto.clear(); cli.get("/cotizaciones", headers=ADMIN)
ok(visto == {"estado": None, "cliente_id": None, "solo_vencidas": False, "buscar": None, "emp": 1}, visto)
ok(cli.get("/cotizaciones?estado=Mala", headers=ADMIN).status_code == 400)
ok(cli.get("/cotizaciones?cliente_id=abc", headers=ADMIN).status_code == 400)
ok(cli.get("/cotizaciones?cliente_id=1%20OR%201=1", headers=ADMIN).status_code == 400)  # intento de inyección

# =============== 5. PDF ===============
COT = {"id": 5, "numero_formateado": "FER-0005", "fecha": datetime(2026, 10, 23, 10, 0), "fecha_vencimiento": date(2026, 11, 7), "vencida": False,
       "estado": "Pendiente", "subtotal": Decimal("170000.00"), "descuento": Decimal("0"), "iva_porcentaje": Decimal("19.00"),
       "impuesto": Decimal("32300.00"), "total": Decimal("202300.00"), "notas": None, "cliente_nombre": "Andina", "cliente_identificacion": "900",
       "cliente_telefono": None, "cliente_email": None, "cliente_direccion": None,
       "detalles_cotizaciones": [{"item_id": 1, "item_nombre": "MO", "item_descripcion": None, "item_tipo": "servicio", "cantidad": Decimal("2"), "precio_unitario": Decimal("85000"), "subtotal_linea": Decimal("170000")}]}
svc.cotizacion.obtener_cotizacion_por_id = lambda emp, cid: dict(COT) if (emp, cid) == (1, 5) else None
r = cli.get("/cotizaciones/5/pdf", headers=VENDEDOR)
ok(r.status_code == 200 and r.mimetype == "application/pdf" and r.data.startswith(b"%PDF"), r.data[:80])
ok(r.headers["Content-Disposition"] == 'inline; filename="FER-0005.pdf"', r.headers["Content-Disposition"])
r = cli.get("/cotizaciones/5/pdf?descargar=1", headers=VENDEDOR); ok(r.headers["Content-Disposition"].startswith("attachment"))
ok(cli.get("/cotizaciones/5/pdf", headers=OTRA).status_code == 404)
ok(cli.get("/cotizaciones/5/pdf").status_code == 401)

# =============== 6. Configuración de la empresa ===============
svc2 = ec.empresa_service
estado_emp = dict(EMPRESA)
svc2.empresa.obtener_configuracion = lambda emp: dict(estado_emp) if emp == 1 else None
svc2.empresa.actualizar_configuracion = lambda emp, campos: estado_emp.update(campos) or 1
r = cli.get("/empresa/configuracion", headers=VENDEDOR); j = r.get_json()
ok(r.status_code == 200 and j["tiene_logo"] is False and "logo_path" not in j and j["prefijo"] == "FER")
r = cli.put("/empresa/configuracion", json={"telefono": " 300 123 4567 ", "color_primario": "#ff8800", "email": "ventas@x.com", "moneda": "usd",
                                           "iva_defecto": 5, "validez_dias": 30, "prefijo": "tor", "condiciones": ""}, headers=ADMIN)
ok(r.status_code == 200, r.data)
ok(estado_emp["telefono"] == "300 123 4567" and estado_emp["color_primario"] == "#FF8800" and estado_emp["moneda"] == "USD"
   and estado_emp["prefijo"] == "TOR" and estado_emp["condiciones"] is None and estado_emp["iva_defecto"] == Decimal("5.00"), estado_emp)
for malo in ({"color_primario": "rojo"}, {"color_primario": "#12"}, {"email": "no-es-correo"}, {"telefono": 3001234567}, {"nombre": "  "},
             {"iva_defecto": 101}, {"validez_dias": 0}, {"validez_dias": 2.5}, {"prefijo": "A B"}, {"moneda": "PESOS"},
             {"condiciones": "x" * 2001}, {"campo_inventado": "x"}, {"empresa_id": 2}):
    r = cli.put("/empresa/configuracion", json=malo, headers=ADMIN); ok(r.status_code == 400, (malo, r.data))
ok(estado_emp["nombre"] == EMPRESA["nombre"])  # los campos no enviados no cambian

# =============== 7. Logo ===============
from PIL import Image
def png(w=1200, h=400, modo="RGBA"):
    b = io.BytesIO(); Image.new(modo, (w, h), (200, 30, 30, 255) if modo == "RGBA" else (200, 30, 30)).save(b, "PNG"); b.seek(0); return b
def jpg():
    b = io.BytesIO(); Image.new("RGB", (300, 300), (10, 120, 200)).save(b, "JPEG"); b.seek(0); return b
logo_db = {"path": None}
svc2.empresa.obtener_configuracion = lambda emp: {**estado_emp, "logo_path": logo_db["path"]}
svc2.empresa.actualizar_logo = lambda emp, path: logo_db.update(path=path) or 1

ok(cli.get("/empresa/logo", headers=ADMIN).status_code == 404)
r = cli.post("/empresa/logo", data={"logo": (png(), "mi logo.png")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 200, r.data)
ruta = os.path.join(TMP, "logos", "empresa_1.png"); ok(os.path.isfile(ruta) and logo_db["path"] == "logos/empresa_1.png", logo_db)
im = Image.open(ruta); ok(max(im.size) == 600 and im.size == (600, 200), im.size)       # se reduce a 600px respetando proporción
r = cli.get("/empresa/logo", headers=VENDEDOR); ok(r.status_code == 200 and r.mimetype == "image/png" and r.data[:4] == b"\x89PNG")
ok(cli.get("/empresa/configuracion", headers=ADMIN).get_json()["tiene_logo"] is True)
r = cli.post("/empresa/logo", data={"logo": (jpg(), "foto.jpg")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 200)
# PDF con logo real
ok(cli.get("/cotizaciones/5/pdf", headers=ADMIN).data.startswith(b"%PDF"))
# archivos que NO son imagen aunque se llamen .png
r = cli.post("/empresa/logo", data={"logo": (io.BytesIO(b"<?php echo 1; ?>"), "logo.png")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 400, r.data)
r = cli.post("/empresa/logo", data={"logo": (io.BytesIO(b"GIF89a" + b"\0" * 20), "logo.gif")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 400)
# demasiado grande: entre 2 y 3 MB lo rechaza el servicio, sobre 3 MB lo rechaza Flask
r = cli.post("/empresa/logo", data={"logo": (io.BytesIO(b"\0" * (2 * 1024 * 1024 + 10)), "a.png")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 413, r.status_code)
r = cli.post("/empresa/logo", data={"logo": (io.BytesIO(b"\0" * (4 * 1024 * 1024)), "a.png")}, headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 413, r.status_code)
r = cli.post("/empresa/logo", headers=ADMIN, content_type="multipart/form-data"); ok(r.status_code == 400)
ok(os.path.isfile(ruta))  # los intentos fallidos no tocaron el logo bueno
r = cli.delete("/empresa/logo", headers=ADMIN); ok(r.status_code == 200 and not os.path.exists(ruta) and logo_db["path"] is None)
# Una ruta guardada que intente salirse de uploads es ignorada
logo_db["path"] = "../../etc/passwd"; ok(svc2.ruta_logo(1) is None)

# =============== 8. Dashboard ===============
dsvc = dc.dashboard_service
dsvc.dashboard.por_estado = lambda emp: [{"estado": "Aceptada", "cantidad": 2, "total": Decimal("500000.00")}, {"estado": "Rechazada", "cantidad": 1, "total": Decimal("100000.00")},
                                         {"estado": "Pendiente", "cantidad": 3, "total": Decimal("300000.00")}]
dsvc.dashboard.vencimientos = lambda emp: {"vencidas_cantidad": 1, "vencidas_total": Decimal("90000"), "por_vencer_cantidad": 2, "por_vencer_total": Decimal("40000")}
dsvc.dashboard.por_mes = lambda emp, meses: [{"anio": 2026, "mes": 9, "cantidad": 2, "total_cotizado": Decimal("200000"), "total_aceptado": Decimal("0")},
                                              {"anio": 2026, "mes": 10, "cantidad": 4, "total_cotizado": Decimal("700000"), "total_aceptado": Decimal("500000")}]
dsvc.cotizacion.obtener_cotizaciones = lambda emp, **kw: [{"id": 1, "limite": kw.get("limite")}]
r = cli.get("/dashboard", headers=VENDEDOR); d = r.get_json(); ok(r.status_code == 200, r.data)
ok(d["por_estado"]["Aceptada"] == {"cantidad": 2, "total": 500000.0}, d["por_estado"])
ok(d["totales"] == {"cantidad": 6, "total": 900000.0})
ok(d["tasa_aceptacion"] == 66.7, d["tasa_aceptacion"])        # 2 aceptadas de 3 cerradas
ok(d["pendientes"]["vencidas"] == {"cantidad": 1, "total": 90000.0} and d["pendientes"]["por_vencer_7_dias"]["cantidad"] == 2)
ok(len(d["por_mes"]) == 6 and d["por_mes"][-1]["mes"] == f"{date.today().year}-{date.today().month:02d}")
ok(d["recientes"] == [{"id": 1, "limite": 5}])
# Sin datos: todo en cero y tasa nula
dsvc.dashboard.por_estado = lambda emp: []
dsvc.dashboard.vencimientos = lambda emp: {"vencidas_cantidad": 0, "vencidas_total": 0, "por_vencer_cantidad": 0, "por_vencer_total": 0}
dsvc.dashboard.por_mes = lambda emp, m: []
d = cli.get("/dashboard", headers=ADMIN).get_json()
ok(d["tasa_aceptacion"] is None and d["totales"]["cantidad"] == 0 and all(m["cantidad"] == 0 for m in d["por_mes"]) and set(d["por_estado"]) == {"Pendiente", "Aceptada", "Rechazada"})
# Cambio de año: en enero la serie incluye diciembre del año anterior
ok(ds._ultimos_meses(6, date(2027, 2, 10)) == [(2026, 9), (2026, 10), (2026, 11), (2026, 12), (2027, 1), (2027, 2)])

# =============== 9. Contraseñas ===============
from werkzeug.security import generate_password_hash
hashes = {1: generate_password_hash("claveVieja123")}
asvc = ac.auth_service; usvc = ac.usuario_service
asvc.usuario.obtener_hash = lambda emp, uid: hashes.get(uid) if emp == 1 else None
def setpw(emp, uid, h):
    if emp == 1 and uid in hashes: hashes[uid] = h; return 1
    return 0
asvc.usuario.actualizar_password = setpw; usvc.usuario.actualizar_password = setpw
H1 = {"Authorization": "Bearer 1:1:admin"}
r = cli.put("/auth/password", json={"password_actual": "mala", "password_nueva": "claveNueva456"}, headers=H1); ok(r.status_code == 400 and "incorrecta" in r.get_json()["error"])
r = cli.put("/auth/password", json={"password_actual": "claveVieja123", "password_nueva": "corta"}, headers=H1); ok(r.status_code == 400)
r = cli.put("/auth/password", json={"password_actual": "claveVieja123"}, headers=H1); ok(r.status_code == 400)
r = cli.put("/auth/password", json={"password_actual": "claveVieja123", "password_nueva": "claveNueva456"}, headers=H1); ok(r.status_code == 200)
from werkzeug.security import check_password_hash
ok(check_password_hash(hashes[1], "claveNueva456") and not check_password_hash(hashes[1], "claveVieja123"))
r = cli.put("/usuarios/1/password", json={"password_nueva": "otraClave789"}, headers=ADMIN); ok(r.status_code == 200 and check_password_hash(hashes[1], "otraClave789"))
ok(cli.put("/usuarios/77/password", json={"password_nueva": "otraClave789"}, headers=ADMIN).status_code == 404)
ok(cli.put("/usuarios/1/password", json={"password_nueva": "otraClave789"}, headers=OTRA).status_code == 404)  # otra empresa

# =============== 10. Errores inesperados y de base de datos ===============
svc.cotizacion.obtener_cotizacion_por_id = lambda emp, cid: (_ for _ in ()).throw(RuntimeError("boom secreto"))
r = cli.get("/cotizaciones/5", headers=ADMIN); ok(r.status_code == 500 and r.get_json() == {"error": "Error interno del servidor"})
svc.cotizacion.obtener_cotizacion_por_id = lambda emp, cid: (_ for _ in ()).throw(DataError("too long"))
r = cli.get("/cotizaciones/5", headers=ADMIN); ok(r.status_code == 400)

shutil.rmtree(TMP, ignore_errors=True)
print("TODAS LAS PRUEBAS FINALES PASARON")
