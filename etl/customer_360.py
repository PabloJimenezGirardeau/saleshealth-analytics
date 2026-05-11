"""
customer_360.py — Fase 5: BUILD CUSTOMER 360
Calcula CLTV, AOV y Return Rate por cliente y carga marts.customer_360.
Una fila por cliente con todas las métricas precalculadas.
"""

from etl.config import SCHEMA_DWH, SCHEMA_MARTS
from etl.db import execute, table_count


def crear_tabla_customer_360(engine) -> None:
    """Crea la tabla marts.customer_360 si no existe."""
    execute(engine, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_MARTS}')
    execute(engine, f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_MARTS}.customer_360 (
            -- Identificacion
            cliente_sk          INTEGER         PRIMARY KEY,
            cliente_nk          INTEGER         NOT NULL,
            nombre              VARCHAR(200),

            -- Metricas de actividad
            num_ventas          INTEGER,        -- pedidos distintos
            num_lineas          INTEGER,        -- lineas de venta
            primera_compra      DATE,
            ultima_compra       DATE,
            antiguedad_dias     INTEGER,        -- dias entre primera y ultima compra
            recencia_dias       INTEGER,        -- dias desde la ultima compra hasta hoy

            -- Metricas de valor
            ingresos_brutos     NUMERIC(12,2),  -- SUM(subtotal_bruto)
            ingresos_netos      NUMERIC(12,2),  -- SUM(subtotal_neto) — descontando devoluciones
            coste_total         NUMERIC(12,2),
            margen_bruto        NUMERIC(12,2),
            margen_pct_medio    NUMERIC(6,2),

            -- AOV: Average Order Value
            aov                 NUMERIC(10,2),  -- ingresos_netos / num_ventas

            -- Frecuencia mensual
            frecuencia_mensual  NUMERIC(8,4),   -- num_ventas / meses_activo

            -- Return Rate
            unidades_compradas  INTEGER,
            unidades_devueltas  INTEGER,
            return_rate         NUMERIC(6,2),   -- unidades_devueltas / unidades_compradas * 100

            -- CLTV
            -- Formula: Ingresos_netos * Margen_pct * Frecuencia_mensual * Antiguedad_meses
            cltv                NUMERIC(12,2),

            -- Segmento (se rellena en fase de clustering)
            cluster_id          INTEGER,
            cluster_label       VARCHAR(50),

            -- Metadata
            calculado_en        TIMESTAMP DEFAULT NOW()
        )
    """)


def load_customer_360(engine) -> int:
    """
    Calcula y carga marts.customer_360.
    Devuelve el número de clientes procesados.
    """
    crear_tabla_customer_360(engine)
    execute(engine, f'TRUNCATE TABLE {SCHEMA_MARTS}.customer_360')

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_MARTS}.customer_360 (
            cliente_sk, cliente_nk, nombre,
            num_ventas, num_lineas, primera_compra, ultima_compra,
            antiguedad_dias, recencia_dias,
            ingresos_brutos, ingresos_netos, coste_total, margen_bruto, margen_pct_medio,
            aov, frecuencia_mensual,
            unidades_compradas, unidades_devueltas, return_rate,
            cltv
        )
        WITH ventas AS (
            SELECT
                fv.cliente_sk,
                COUNT(DISTINCT fv.sale_id)                          AS num_ventas,
                COUNT(*)                                             AS num_lineas,
                MIN(df.fecha)                                        AS primera_compra,
                MAX(df.fecha)                                        AS ultima_compra,
                SUM(fv.cantidad)                                     AS unidades_compradas,
                SUM(fv.subtotal_bruto)                               AS ingresos_brutos,
                SUM(fv.subtotal_neto)                                AS ingresos_netos,
                SUM(fv.coste_total)                                  AS coste_total,
                SUM(fv.margen_bruto)                                 AS margen_bruto,
                SUM(fv.cantidad_devuelta)                            AS unidades_devueltas
            FROM {SCHEMA_DWH}.fact_ventas fv
            JOIN {SCHEMA_DWH}.dim_fecha df ON fv.fecha_sk = df.fecha_sk
            WHERE fv.cliente_sk > 0  -- excluir desconocido
            GROUP BY fv.cliente_sk
        ),
        metricas AS (
            SELECT
                v.*,
                dc.cliente_nk,
                dc.nombre || ' ' || dc.apellido                      AS nombre,

                -- Antiguedad en dias
                (v.ultima_compra - v.primera_compra)                 AS antiguedad_dias,

                -- Recencia: dias desde ultima compra hasta hoy
                (CURRENT_DATE - v.ultima_compra)                     AS recencia_dias,

                -- Meses activo (minimo 1 para evitar division por cero)
                GREATEST(
                    (v.ultima_compra - v.primera_compra) / 30.0, 1
                )                                                     AS meses_activo,

                -- Margen medio ponderado
                CASE
                    WHEN v.ingresos_brutos > 0
                    THEN ROUND(v.margen_bruto / v.ingresos_brutos * 100, 2)
                    ELSE 0
                END                                                   AS margen_pct_medio,

                -- Return rate — capeado a 100 para evitar anomalias
                -- (algunos clientes tienen mas devoluciones que compras por
                --  doble registro en return_item en datos origen)
                LEAST(
                    CASE
                        WHEN v.unidades_compradas > 0
                        THEN ROUND(v.unidades_devueltas::NUMERIC
                             / v.unidades_compradas * 100, 2)
                        ELSE 0
                    END,
                    100
                )                                                     AS return_rate

            FROM ventas v
            JOIN {SCHEMA_DWH}.dim_cliente dc ON v.cliente_sk = dc.cliente_sk
        )
        SELECT
            m.cliente_sk,
            m.cliente_nk,
            m.nombre,
            m.num_ventas,
            m.num_lineas,
            m.primera_compra,
            m.ultima_compra,
            m.antiguedad_dias,
            m.recencia_dias,
            ROUND(m.ingresos_brutos, 2)                              AS ingresos_brutos,
            ROUND(m.ingresos_netos, 2)                               AS ingresos_netos,
            ROUND(m.coste_total, 2)                                  AS coste_total,
            ROUND(m.margen_bruto, 2)                                 AS margen_bruto,
            m.margen_pct_medio,

            -- AOV
            ROUND(m.ingresos_netos / NULLIF(m.num_ventas, 0), 2)    AS aov,

            -- Frecuencia mensual
            ROUND(m.num_ventas / m.meses_activo, 4)                  AS frecuencia_mensual,

            -- Return rate
            m.unidades_compradas,
            m.unidades_devueltas,
            m.return_rate,

            -- CLTV = Ingresos_netos * Margen_pct
            -- Formula correcta segun enunciado: AOV * frecuencia * meses_activo * margen
            -- que algebraicamente simplifica a: ingresos_netos * margen_pct
            -- Evita el error anterior donde num_ventas aparecia al cuadrado
            -- (ingresos_netos ya contiene num_ventas implicito via AOV*num_ventas)
            ROUND(
                m.ingresos_netos * (m.margen_pct_medio / 100.0),
            2)                                                        AS cltv

        FROM metricas m
        ORDER BY m.cliente_sk
    """)
    return n