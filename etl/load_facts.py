"""
load_facts.py — Fase 3: LOAD HECHOS
Carga fact_ventas y fact_devoluciones desde stg.*
haciendo JOIN con las dimensiones para obtener las SKs.
"""

from etl.config import SCHEMA_STG, SCHEMA_DWH
from etl.db import execute, table_count


def _load_fact_ventas(engine) -> int:
    """
    Carga fact_ventas desde stg.sale_item + stg.sale.
    - Resuelve todas las SKs via JOIN con dimensiones
    - Calcula metricas derivadas: margen, subtotal_neto, es_devuelta
    - Para zona: busca por postal_code de la tienda (no del cliente —
      customer no tiene FK a city_zone)
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.fact_ventas')

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.fact_ventas (
            fecha_sk, cliente_sk, producto_sk, tienda_sk,
            zona_sk, oferta_sk,
            sale_id, sale_item_id,
            cantidad, precio_unitario, subtotal_bruto,
            coste_total, margen_bruto, margen_pct,
            es_devuelta, cantidad_devuelta, subtotal_neto
        )
        SELECT
            -- Claves subrogadas
            TO_CHAR(s.sale_date::DATE, 'YYYYMMDD')::INTEGER  AS fecha_sk,
            COALESCE(dc.cliente_sk, 1)                        AS cliente_sk,
            COALESCE(dp.producto_sk, 1)                       AS producto_sk,
            COALESCE(dt.tienda_sk, 1)                         AS tienda_sk,
            COALESCE(dz.zona_sk, 1)                           AS zona_sk,
            COALESCE(dof.oferta_sk, 1)                        AS oferta_sk,

            -- Claves naturales (trazabilidad)
            si.sale_id,
            si.sale_item_id,

            -- Metricas
            si.quantity                                       AS cantidad,
            si.unit_price                                     AS precio_unitario,
            si.subtotal                                       AS subtotal_bruto,
            ROUND(si.quantity * dp.coste_unitario, 2)        AS coste_total,
            ROUND(si.subtotal - si.quantity * dp.coste_unitario, 2) AS margen_bruto,
            CASE
                WHEN si.subtotal > 0 AND dp.coste_unitario IS NOT NULL
                THEN ROUND((si.subtotal - si.quantity * dp.coste_unitario)
                     / si.subtotal * 100, 2)
                ELSE NULL
            END                                               AS margen_pct,

            -- Flag devolucion
            CASE WHEN dev.sale_item_id IS NOT NULL THEN TRUE ELSE FALSE END AS es_devuelta,
            COALESCE(dev.cantidad_devuelta, 0)               AS cantidad_devuelta,
            ROUND(si.subtotal - COALESCE(dev.cantidad_devuelta, 0)
                  * si.unit_price, 2)                         AS subtotal_neto

        FROM {SCHEMA_STG}.sale_item si
        JOIN {SCHEMA_STG}.sale s ON si.sale_id = s.sale_id

        -- Dimension fecha
        JOIN {SCHEMA_DWH}.dim_fecha df
          ON df.fecha_sk = TO_CHAR(s.sale_date::DATE, 'YYYYMMDD')::INTEGER

        -- Dimension cliente
        LEFT JOIN {SCHEMA_DWH}.dim_cliente dc ON dc.cliente_nk = s.customer_id

        -- Dimension producto
        LEFT JOIN {SCHEMA_DWH}.dim_producto dp ON dp.producto_nk = si.product_id

        -- Dimension tienda
        LEFT JOIN {SCHEMA_DWH}.dim_tienda dt ON dt.tienda_nk = s.store_id

        -- Dimension zona (via postal_code de la tienda)
        LEFT JOIN {SCHEMA_STG}.store st ON st.store_id = s.store_id
        LEFT JOIN {SCHEMA_DWH}.dim_zona dz ON dz.codigo_postal = st.postal_code

        -- Dimension oferta
        LEFT JOIN {SCHEMA_DWH}.dim_oferta dof
          ON dof.oferta_nk = si.offer_id AND dof.es_sin_oferta = FALSE

        -- Devoluciones agregadas por sale_item
        LEFT JOIN (
            SELECT
                sale_item_id,
                SUM(quantity) AS cantidad_devuelta
            FROM {SCHEMA_STG}.return_item
            GROUP BY sale_item_id
        ) dev ON dev.sale_item_id = si.sale_item_id

        -- Usar 'Sin oferta' cuando offer_id es NULL
        LEFT JOIN {SCHEMA_DWH}.dim_oferta dof_sin
          ON dof_sin.es_sin_oferta = TRUE
    """)
    return n


def _load_fact_devoluciones(engine) -> int:
    """
    Carga fact_devoluciones desde stg.return_item.
    Resuelve SKs via JOIN con dimensiones y con fact_ventas para obtener
    tienda y cliente del sale original.
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.fact_devoluciones')

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.fact_devoluciones (
            fecha_sk, cliente_sk, producto_sk, tienda_sk, motivo_sk,
            return_id, sale_item_id,
            cantidad_devuelta, importe_devuelto, coste_devuelto
        )
        SELECT
            -- Fecha de la devolucion
            TO_CHAR(ri.return_date::DATE, 'YYYYMMDD')::INTEGER  AS fecha_sk,

            -- Cliente y tienda del sale original
            COALESCE(fv.cliente_sk, 1)                           AS cliente_sk,
            COALESCE(fv.producto_sk, 1)                          AS producto_sk,
            COALESCE(fv.tienda_sk, 1)                            AS tienda_sk,

            -- Motivo de devolucion
            COALESCE(dm.motivo_sk, 1)                            AS motivo_sk,

            -- Claves naturales
            ri.return_id,
            ri.sale_item_id,

            -- Metricas
            ri.quantity                                          AS cantidad_devuelta,
            ROUND(ri.quantity * fv.precio_unitario, 2)          AS importe_devuelto,
            ROUND(ri.quantity * dp.coste_unitario, 2)           AS coste_devuelto

        FROM {SCHEMA_STG}.return_item ri

        -- Datos del sale_item original (para precio y producto)
        LEFT JOIN {SCHEMA_DWH}.fact_ventas fv ON fv.sale_item_id = ri.sale_item_id
        LEFT JOIN {SCHEMA_DWH}.dim_producto dp ON dp.producto_sk = fv.producto_sk

        -- Dimension motivo
        LEFT JOIN {SCHEMA_DWH}.dim_motivo_devolucion dm ON dm.motivo_nk = ri.reason_id

        -- Dimension fecha devolucion (debe existir)
        JOIN {SCHEMA_DWH}.dim_fecha df
          ON df.fecha_sk = TO_CHAR(ri.return_date::DATE, 'YYYYMMDD')::INTEGER
    """)
    return n


def load_facts(engine) -> dict:
    """
    Carga los 2 hechos en orden (ventas primero, devoluciones después).
    Devuelve dict con conteos.
    """
    n_ventas = _load_fact_ventas(engine)
    n_dev    = _load_fact_devoluciones(engine)

    return {
        'fact_ventas'       : n_ventas,
        'fact_devoluciones' : n_dev,
    }
