"""
Acceso a MySQL con POOL de conexiones.

Antes: cada Model abría UNA conexión al importarse y la usaba para siempre.
Problemas: MySQL la cierra por inactividad y, además, varias peticiones
simultáneas compartían la misma conexión.

Ahora: se crea un "pool" (piscina) de N conexiones. Cada operación toma una
prestada, la usa y la devuelve. Si una conexión murió, el pool la reconecta.

Este archivo ofrece 4 herramientas sencillas para los Models:
    consultar(...)   -> SELECT
    insertar(...)    -> INSERT  (devuelve el id nuevo)
    modificar(...)   -> UPDATE / DELETE (devuelve filas encontradas)
    transaccion()    -> agrupa varias operaciones: o se guardan TODAS o NINGUNA
"""
import threading
from contextlib import contextmanager

import mysql.connector
from mysql.connector import ClientFlag, pooling

from config.settings import Settings

_pool = None
_candado = threading.Lock()  # evita crear el pool dos veces si llegan 2 peticiones a la vez


def _obtener_pool():
    """Crea el pool la primera vez que se necesita ("lazy") y luego lo reutiliza."""
    global _pool
    if _pool is None:
        with _candado:
            if _pool is None:
                _pool = pooling.MySQLConnectionPool(
                    pool_name="cotizaciones_pool",
                    pool_size=Settings.DB_POOL_SIZE,
                    pool_reset_session=True,
                    host=Settings.DB_HOST,
                    port=Settings.DB_PORT,
                    user=Settings.DB_USER,
                    password=Settings.DB_PASSWORD,
                    database=Settings.DB_NAME,
                    charset="utf8mb4",
                    # autocommit=True: cada INSERT/UPDATE suelto se guarda solo.
                    # Dentro de transaccion() lo controlamos manualmente.
                    autocommit=True,
                    # FOUND_ROWS: rowcount = filas ENCONTRADAS, no "filas que cambiaron".
                    # Sin esto, un UPDATE con los mismos valores devolvía 0 y la API
                    # respondía "no encontrado" por error.
                    client_flags=[ClientFlag.FOUND_ROWS],
                )
    return _pool


@contextmanager
def obtener_conexion():
    """Presta una conexión del pool y la devuelve automáticamente al terminar."""
    conexion = _obtener_pool().get_connection()
    try:
        yield conexion
    finally:
        conexion.close()  # en un pool, close() = "devolver a la piscina", no cerrar


@contextmanager
def transaccion():
    """
    Uso:
        with transaccion() as conn:
            id_cab = modelo.insertar_cabecera(..., conn)
            modelo.insertar_detalles(id_cab, ..., conn)

    Si todo sale bien -> COMMIT (se guarda todo).
    Si algo lanza una excepción -> ROLLBACK (no se guarda nada).
    """
    with obtener_conexion() as conexion:
        conexion.start_transaction()
        try:
            yield conexion
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise


# ----------------------------------------------------------------------
# Herramientas para los Models. El parámetro `conn` es opcional:
#   - sin conn -> la función toma su propia conexión (operación suelta)
#   - con conn -> participa en la transacción que le pasaste
# ----------------------------------------------------------------------
def consultar(sql, params=None, uno=False, conn=None):
    """Ejecuta un SELECT. uno=True devuelve un dict (o None); si no, una lista de dicts."""
    if conn is None:
        with obtener_conexion() as nueva:
            return consultar(sql, params, uno, nueva)

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone() if uno else cursor.fetchall()
    finally:
        cursor.close()


def insertar(sql, params=None, conn=None):
    """Ejecuta un INSERT y devuelve el id autogenerado."""
    if conn is None:
        with obtener_conexion() as nueva:
            return insertar(sql, params, nueva)

    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        return cursor.lastrowid
    finally:
        cursor.close()


def insertar_muchos(sql, lista_de_params, conn=None):
    """Inserta varias filas de una vez (más rápido que un INSERT por fila)."""
    if conn is None:
        with obtener_conexion() as nueva:
            return insertar_muchos(sql, lista_de_params, nueva)

    cursor = conn.cursor()
    try:
        cursor.executemany(sql, lista_de_params)
        return cursor.rowcount
    finally:
        cursor.close()


def modificar(sql, params=None, conn=None):
    """Ejecuta UPDATE/DELETE y devuelve cuántas filas coincidieron (0 = no existía)."""
    if conn is None:
        with obtener_conexion() as nueva:
            return modificar(sql, params, nueva)

    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        return cursor.rowcount
    finally:
        cursor.close()
