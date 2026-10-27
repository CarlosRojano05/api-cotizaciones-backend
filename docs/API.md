# Referencia de la API

Base: `http://localhost:5000` (en producción, tu dominio con HTTPS).

## Convenciones

- **Autenticación**: toda ruta, salvo `/auth/registro`, `/auth/login` y `/salud`, exige el encabezado
  `Authorization: Bearer <token>`. El token dura 8 horas (configurable).
- **Cuerpo**: JSON (`Content-Type: application/json`). La única excepción es la subida del logo (`multipart/form-data`).
- **Errores**: siempre `{"error": "mensaje en español"}` con el código HTTP correspondiente:
  `400` datos inválidos · `401` sin sesión / token vencido · `403` sin permisos · `404` no existe ·
  `409` duplicado · `413` archivo muy grande · `500` error del servidor.
- **Dinero**: números JSON (`368900.0`), con 2 decimales de precisión. El cálculo se hace en Decimal en el servidor.
- **Fechas**: ISO 8601. `fecha` → `"2026-10-23T10:00:00"`; `fecha_vencimiento` → `"2026-11-07"`.
- **Aislamiento**: cada usuario solo ve y modifica datos de SU empresa. Un recurso de otra empresa responde `404`.
- **Roles**: `admin` y `vendedor`. En la tabla, 🔒 = solo admin.

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/auth/registro` | público | Crea empresa + usuario admin. Devuelve token |
| POST | `/auth/login` | público | Devuelve token |
| GET | `/auth/me` | login | Perfil del usuario |
| PUT | `/auth/password` | login | Cambiar mi contraseña |
| GET | `/usuarios` | 🔒 | Usuarios de la empresa |
| POST | `/usuarios` | 🔒 | Crear usuario (admin o vendedor) |
| PUT | `/usuarios/<id>/password` | 🔒 | Asignar contraseña nueva a un usuario |
| DELETE | `/usuarios/<id>` | 🔒 | Desactivar usuario |
| GET | `/empresa/configuracion` | login | Datos y preferencias de la empresa |
| PUT | `/empresa/configuracion` | 🔒 | Actualización parcial |
| GET / POST / DELETE | `/empresa/logo` | login / 🔒 / 🔒 | Ver, subir, eliminar logo |
| GET | `/clientes`, `/clientes/<id>` | login | |
| POST / PUT | `/clientes`, `/clientes/<id>` | login | |
| DELETE | `/clientes/<id>` | 🔒 | Baja lógica |
| GET | `/items` | login | Catálogo |
| POST / PUT / DELETE | `/items`, `/items/<id>` | 🔒 | |
| GET | `/cotizaciones` | login | Lista con filtros (ver abajo) |
| POST | `/cotizaciones` | login | Crear |
| GET | `/cotizaciones/<id>` | login | Detalle con líneas |
| PATCH | `/cotizaciones/<id>/estado` | login | Cambiar estado (queda en el historial) |
| GET | `/cotizaciones/<id>/historial` | login | Cambios de estado |
| GET | `/cotizaciones/<id>/pdf` | login | PDF (`?descargar=1` fuerza descarga) |
| DELETE | `/cotizaciones/<id>` | 🔒 | Anular (baja lógica) |
| GET | `/dashboard` | login | Resumen del panel principal |
| GET | `/salud` | público | Comprobar que el servidor vive |

## Ejemplos clave

### Login / registro → respuesta
```json
{ "token": "eyJ...", "usuario": {"id": 1, "nombre": "Carlos Pérez", "email": "carlos@eltornillo.com", "rol": "admin"},
  "empresa": {"id": 1, "nombre": "Ferretería El Tornillo S.A.S."} }
```
Registro recibe: `empresa_nombre`, `nit` (opcional), `nombre`, `email`, `password` (mínimo 8 caracteres).

### Crear cotización
```json
{ "cliente_id": 1, "descuento": 10000, "iva_porcentaje": 19, "fecha_vencimiento": "2026-12-15",
  "notas": "Entrega en 3 días", "items": [ {"item_id": 1, "cantidad": 2}, {"item_id": 2, "precio_unitario": 120000} ] }
```
Solo `cliente_id` e `items` son obligatorios. Si falta `precio_unitario` se usa el del catálogo; si falta
`iva_porcentaje`, el de la empresa (`0` = exento); si falta `fecha_vencimiento`, hoy + días de validez.
Respuesta `201`:
```json
{ "mensaje": "Cotización creada exitosamente", "cotizacion_id": 7, "numero": 7, "numero_formateado": "FER-0007",
  "fecha_vencimiento": "2026-12-15",
  "resumen_financiero": {"subtotal": 410000.0, "descuento": 10000.0, "iva_porcentaje": 19.0, "impuesto_iva": 76000.0, "total": 476000.0} }
```

### Listar cotizaciones — filtros opcionales
`GET /cotizaciones?estado=Pendiente&cliente_id=3&vencidas=1&buscar=andina`
`buscar` busca en nombre del cliente, identificación y número (`FER-0007`). Cada elemento:
```json
{ "id": 7, "numero": 7, "numero_formateado": "FER-0007", "fecha": "2026-10-23T10:00:00", "fecha_vencimiento": "2026-12-15",
  "vencida": false, "estado": "Pendiente", "subtotal": 410000.0, "descuento": 10000.0, "iva_porcentaje": 19.0,
  "impuesto": 76000.0, "total": 476000.0, "cliente_id": 1, "cliente_nombre": "Constructora Andina", "cliente_identificacion": "900555111-2" }
```
`vencida` = está Pendiente y su fecha de vencimiento ya pasó (se calcula, no se guarda).

### Cambiar estado
`PATCH /cotizaciones/7/estado` → `{"estado": "Aceptada", "comentario": "Confirmó por WhatsApp"}` (comentario opcional).
Estados: `Pendiente`, `Aceptada`, `Rechazada`.

### Historial
```json
[ {"id": 1, "estado_anterior": null, "estado_nuevo": "Pendiente", "comentario": "Cotización creada", "fecha": "2026-10-23T10:00:00", "usuario_nombre": "Carlos Pérez"},
  {"id": 2, "estado_anterior": "Pendiente", "estado_nuevo": "Aceptada", "comentario": "Confirmó por WhatsApp", "fecha": "2026-10-24T15:30:00", "usuario_nombre": "Laura" } ]
```

### Configuración de la empresa
`PUT /empresa/configuracion` acepta (todos opcionales): `nombre`, `nit`, `direccion`, `telefono`, `email`, `sitio_web`,
`color_primario` (`#RRGGBB`), `moneda` (3 letras), `iva_defecto` (0–100), `validez_dias` (1–365), `prefijo` (A-Z/0-9, máx. 10), `condiciones`.
`GET` devuelve lo mismo más `tiene_logo` (true/false).

### Dashboard
```json
{ "por_estado": {"Pendiente": {"cantidad": 3, "total": 300000.0}, "Aceptada": {"cantidad": 2, "total": 500000.0}, "Rechazada": {"cantidad": 1, "total": 100000.0}},
  "totales": {"cantidad": 6, "total": 900000.0},
  "tasa_aceptacion": 66.7,
  "pendientes": {"vencidas": {"cantidad": 1, "total": 90000.0}, "por_vencer_7_dias": {"cantidad": 2, "total": 40000.0}},
  "mes_actual": {"mes": "2026-10", "cantidad": 4, "total_cotizado": 700000.0, "total_aceptado": 500000.0},
  "por_mes": [ {"mes": "2026-05", "cantidad": 0, "total_cotizado": 0.0, "total_aceptado": 0.0}, "... 6 meses, del más antiguo al actual" ],
  "recientes": [ "...las 5 últimas cotizaciones, con el mismo formato del listado" ] }
```
`tasa_aceptacion` = aceptadas ÷ (aceptadas + rechazadas) × 100; es `null` si aún no hay cotizaciones cerradas.
El panel muestra datos de TODA la empresa (también para vendedores).

## Notas para el frontend

- **PDF y logo requieren el token**, y una etiqueta `<img src>` o un `window.open` NO pueden enviar encabezados.
  Se piden con `fetch` + `Authorization`, se convierten a `blob` y se muestran con `URL.createObjectURL(blob)`.
- **Subir logo**: `FormData` con el campo `logo`. No pongas `Content-Type` a mano (el navegador agrega el `boundary`).
- **Sesión vencida**: ante un `401` (salvo en el login), borra el token y manda al usuario a iniciar sesión.
- **Cambiar contraseña con clave actual incorrecta** devuelve `400` (no `401`), para no confundirlo con sesión vencida.
- Guarda el `rol` del usuario para ocultar los botones que solo puede usar el admin (el servidor igual los bloquea con `403`).
