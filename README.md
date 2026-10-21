# API de Cotizaciones (multiempresa)

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
├── utils/                  # auth (JWT), dinero (Decimal), validaciones, http
└── sql/                    # Scripts de base de datos
```
Flujo de una petición: **controller → service → model → MySQL**.

## Puesta en marcha
1. `python -m venv venv` y activarlo (`venv\Scripts\activate` en Windows).
2. `pip install -r requirements.txt`
3. Copia `.env.example` a `.env` y genera tu clave:
   `python -c "import secrets; print(secrets.token_hex(32))"`
4. Base de datos: instalación nueva -> `sql/01_schema_nuevo.sql`;
   si ya tienes datos -> `sql/02_migracion_desde_v0.sql`.
5. `python app.py` y prueba `GET http://localhost:5000/salud`.

## Endpoints
| Método | Ruta | Acceso |
|---|---|---|
| POST | /auth/registro | público (crea empresa + admin) |
| POST | /auth/login | público |
| GET | /auth/me | autenticado |
| GET/POST | /usuarios | admin |
| DELETE | /usuarios/<id> | admin |
| GET/POST/PUT | /clientes ... | autenticado |
| DELETE | /clientes/<id> | admin |
| GET | /items | autenticado |
| POST/PUT/DELETE | /items ... | admin |
| GET/POST | /cotizaciones | autenticado |
| GET | /cotizaciones/<id> | autenticado |
| PATCH | /cotizaciones/<id>/estado | autenticado |

Las rutas privadas requieren el encabezado `Authorization: Bearer <token>`.
