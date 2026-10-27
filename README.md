# API de Cotizaciones (multiempresa) — Backend completo

Backend del MVP: usuarios y empresas, clientes, catálogo, cotizaciones con numeración,
seguimiento (historial), configuración con logo, PDF comercial y panel de resumen.

## Estructura

```
cotizaciones_api/
├── app.py                  # Punto de entrada (create_app)
├── .env.example            # Plantilla de variables de entorno (copiar a .env)
├── requirements.txt
├── config/
│   ├── settings.py         # Lee el .env
│   └── database.py         # Pool de conexiones + transacciones
├── controllers/            # Rutas HTTP: reciben la petición y devuelven JSON
├── services/               # Reglas de negocio y validaciones
├── models/                 # Consultas SQL
├── utils/                  # JWT/roles, dinero (Decimal), PDF, validaciones
├── sql/                    # Scripts de base de datos
├── postman/                # Colección y environment listos para importar
├── docs/API.md             # Referencia de la API (para el frontend)
├── tests/                  # Prueba automática
└── uploads/                # (se crea solo) logos de las empresas — NO subir a Git
```
Flujo de una petición: **controller → service → model → MySQL**.

## Puesta en marcha

1. `python -m venv venv` y activarlo (`venv\Scripts\activate` en Windows).
2. `pip install -r requirements.txt`
3. Copia `.env.example` a `.env` y genera tu clave secreta:
   `python -c "import secrets; print(secrets.token_hex(32))"`
4. **Base de datos** — elige UNA situación:

   | Tu situación | Scripts a ejecutar |
   |---|---|
   | Base vacía / instalación nueva | `01_schema_nuevo.sql` (ya incluye todo) |
   | Tienes la base del paso 2 (ya aplicaste hasta `02`) | `03_paso3_cotizaciones.sql` y luego `04_pasos_4_a_7.sql` |
   | Ya aplicaste `03` | solo `04_pasos_4_a_7.sql` |
   | Tienes la base original (antes de multiempresa) | `02`, `03` y `04`, en ese orden |

   Si solo tienes datos de prueba, lo más simple es borrar la base y cargar `01_schema_nuevo.sql`.
5. `python app.py` y prueba `GET http://localhost:5000/salud`.

## Postman

Importa los dos archivos de la carpeta `postman/` (Import → arrastrar):
`API_Cotizaciones.postman_collection.json` y `local.postman_environment.json`.
Selecciona el environment **local** (arriba a la derecha) y ejecuta `auth > registro`
(o `login`): el token se guarda solo y todas las demás peticiones lo usan.

## Prueba automática

`python tests/test_api_simulada.py` — no necesita MySQL. Córrela cada vez que cambies el backend.

## Antes de publicarlo (producción)

- **HTTPS obligatorio**: sin él, contraseñas y tokens viajan en texto plano.
- `FLASK_DEBUG=0` y una `JWT_SECRET_KEY` larga y propia (distinta a la de desarrollo).
- `CORS_ORIGINS` con el dominio exacto del frontend (no `*`).
- No uses `python app.py` en producción: usa un servidor WSGI (gunicorn en Linux, waitress en Windows).
- Usuario de MySQL propio para la app (no `root`), con permisos solo sobre `db_cotizaciones`.
- Copias de seguridad automáticas de la base de datos **y de la carpeta `uploads/`**.
- Zona horaria del servidor = la de tus clientes (afecta vencimientos).
