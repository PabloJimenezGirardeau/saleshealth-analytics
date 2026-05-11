"""
extract.py — Fase 1: EXTRACT
Lee las 17 tablas de public.* y las copia en stg.* sin transformaciones.
Crea las tablas de staging si no existen (LIKE origen).
"""

import time
from sqlalchemy import text
from etl.config import TODAS_LAS_TABLAS, SCHEMA_ORIGEN, SCHEMA_STG
from etl.db import get_engine, execute, table_count


def crear_tablas_stg(engine) -> None:
    """Crea las tablas de staging como copia exacta del origen si no existen."""
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_STG}'))
        for tabla in TODAS_LAS_TABLAS:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_STG}.{tabla}
                (LIKE {SCHEMA_ORIGEN}.{tabla} INCLUDING ALL)
            """))


def extract(engine) -> dict:
    """
    Copia todas las tablas de public.* a stg.*.
    Devuelve un dict con el conteo de registros por tabla.
    """
    crear_tablas_stg(engine)
    resultados = {}

    for tabla in TODAS_LAS_TABLAS:
        # Truncar staging y reinsertar desde origen
        execute(engine, f'TRUNCATE TABLE {SCHEMA_STG}.{tabla}')
        n = execute(engine, f"""
            INSERT INTO {SCHEMA_STG}.{tabla}
            SELECT * FROM {SCHEMA_ORIGEN}.{tabla}
        """)
        resultados[tabla] = n

    return resultados
