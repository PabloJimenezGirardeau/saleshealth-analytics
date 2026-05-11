"""
db.py — Helpers de conexión y ejecución SQLAlchemy.
"""

from sqlalchemy import create_engine, text
import pandas as pd
from etl.config import DATABASE_URL


def get_engine():
    """Devuelve el engine de SQLAlchemy."""
    return create_engine(DATABASE_URL)


def query(engine, sql: str, params: dict = None) -> pd.DataFrame:
    """Ejecuta una SELECT y devuelve un DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def execute(engine, sql: str, params: dict = None) -> int:
    """Ejecuta un INSERT/UPDATE/DELETE/DDL. Devuelve filas afectadas."""
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount if result.rowcount != -1 else 0


def execute_many(engine, sql: str, records: list) -> int:
    """Inserta múltiples registros. Devuelve número de filas insertadas."""
    if not records:
        return 0
    with engine.begin() as conn:
        result = conn.execute(text(sql), records)
        return result.rowcount


def truncate(engine, schema: str, table: str) -> None:
    """Trunca una tabla del schema indicado (con CASCADE para respetar FKs)."""
    execute(engine, f'TRUNCATE TABLE {schema}.{table} RESTART IDENTITY CASCADE')


def table_count(engine, schema: str, table: str) -> int:
    """Devuelve el número de filas de una tabla."""
    return int(query(engine, f'SELECT COUNT(*) AS n FROM {schema}.{table}')['n'].iloc[0])