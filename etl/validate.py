"""
validate.py — Fase 4: VALIDACIONES
21 checks automáticos declarativos sobre el DWH cargado.
Cada check tiene: descripcion, query, valor esperado y tipo de comparacion.
"""

from etl.config import SCHEMA_STG, SCHEMA_DWH
from etl.db import query


# ── Definicion declarativa de validaciones ────────────────────────────────────
# tipo: 'eq' (igual), 'gt' (mayor que), 'zero' (debe ser 0)

VALIDACIONES = [
    # ── Conteos de staging ────────────────────────────────────────────────────
    {
        'id': 'V01', 'desc': 'stg.sale tiene 20.000 registros',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_STG}.sale',
        'esperado': 20000, 'tipo': 'eq'
    },
    {
        'id': 'V02', 'desc': 'stg.sale_item tiene 42.555 registros',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_STG}.sale_item',
        'esperado': 42555, 'tipo': 'eq'
    },
    {
        'id': 'V03', 'desc': 'stg.customer tiene 5.750 registros',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_STG}.customer',
        'esperado': 5750, 'tipo': 'eq'
    },
    {
        'id': 'V04', 'desc': 'stg.product tiene 50 registros',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_STG}.product',
        'esperado': 50, 'tipo': 'eq'
    },

    # ── Conteos de dimensiones ────────────────────────────────────────────────
    {
        'id': 'V05', 'desc': 'dim_cliente cargada (5750 + 1 desconocido)',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_cliente',
        'esperado': 5751, 'tipo': 'eq'
    },
    {
        'id': 'V06', 'desc': 'dim_producto cargada (50 + 1 desconocido)',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_producto',
        'esperado': 51, 'tipo': 'eq'
    },
    {
        'id': 'V07', 'desc': 'dim_tienda cargada (20 + 1 desconocida)',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_tienda',
        'esperado': 21, 'tipo': 'eq'
    },
    {
        'id': 'V08', 'desc': 'dim_fecha cubre todo el rango de ventas',
        'sql': f"""
            SELECT COUNT(*) AS n
            FROM (
                SELECT DISTINCT sale_date::DATE AS fecha
                FROM {SCHEMA_STG}.sale
            ) ventas
            LEFT JOIN {SCHEMA_DWH}.dim_fecha df
              ON df.fecha = ventas.fecha
            WHERE df.fecha_sk IS NULL
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V09', 'desc': 'dim_oferta tiene registro Sin oferta',
        'sql': f"SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_oferta WHERE es_sin_oferta = TRUE",
        'esperado': 1, 'tipo': 'eq'
    },
    {
        'id': 'V10', 'desc': 'dim_motivo_devolucion tiene registro Desconocido',
        'sql': f"SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_motivo_devolucion WHERE es_desconocido = TRUE",
        'esperado': 1, 'tipo': 'eq'
    },

    # ── Conteos de hechos ─────────────────────────────────────────────────────
    {
        'id': 'V11', 'desc': 'fact_ventas tiene 42.555 registros',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas',
        'esperado': 42555, 'tipo': 'eq'
    },
    {
        'id': 'V12', 'desc': 'fact_devoluciones tiene registros > 0',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_devoluciones',
        'esperado': 0, 'tipo': 'gt'
    },

    # ── Integridad referencial DWH ────────────────────────────────────────────
    {
        'id': 'V13', 'desc': 'fact_ventas sin cliente_sk huerfano',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas fv
            LEFT JOIN {SCHEMA_DWH}.dim_cliente dc ON fv.cliente_sk = dc.cliente_sk
            WHERE dc.cliente_sk IS NULL
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V14', 'desc': 'fact_ventas sin producto_sk huerfano',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas fv
            LEFT JOIN {SCHEMA_DWH}.dim_producto dp ON fv.producto_sk = dp.producto_sk
            WHERE dp.producto_sk IS NULL
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V15', 'desc': 'fact_ventas sin tienda_sk huerfano',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas fv
            LEFT JOIN {SCHEMA_DWH}.dim_tienda dt ON fv.tienda_sk = dt.tienda_sk
            WHERE dt.tienda_sk IS NULL
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V16', 'desc': 'fact_ventas sin fecha_sk huerfano',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas fv
            LEFT JOIN {SCHEMA_DWH}.dim_fecha df ON fv.fecha_sk = df.fecha_sk
            WHERE df.fecha_sk IS NULL
        """,
        'esperado': 0, 'tipo': 'zero'
    },

    # ── Reglas de negocio ─────────────────────────────────────────────────────
    {
        'id': 'V17', 'desc': 'fact_ventas sin cantidades negativas',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas WHERE cantidad <= 0',
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V18', 'desc': 'fact_ventas sin subtotales negativos',
        'sql': f'SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas WHERE subtotal_bruto < 0',
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V19', 'desc': 'fact_ventas: subtotal_neto <= subtotal_bruto siempre',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.fact_ventas
            WHERE subtotal_neto > subtotal_bruto + 0.01
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V20', 'desc': 'dim_producto sin margenes negativos',
        'sql': f"""
            SELECT COUNT(*) AS n FROM {SCHEMA_DWH}.dim_producto
            WHERE margen_pct < 0 AND producto_nk != -1
        """,
        'esperado': 0, 'tipo': 'zero'
    },
    {
        'id': 'V21', 'desc': 'fact_ventas: total ventas coincide con stg',
        'sql': f"""
            SELECT ABS(
                (SELECT SUM(subtotal_bruto) FROM {SCHEMA_DWH}.fact_ventas) -
                (SELECT SUM(subtotal)       FROM {SCHEMA_STG}.sale_item)
            ) < 1 AS n
        """,
        'esperado': True, 'tipo': 'eq'
    },
]


def validate(engine) -> dict:
    """
    Ejecuta las 21 validaciones declarativas.
    Devuelve dict con resultados: total, passed, failed, detalles.
    """
    resultados = []

    for v in VALIDACIONES:
        try:
            df  = query(engine, v['sql'])
            val = df.iloc[0, 0]

            if v['tipo'] == 'eq':
                ok = val == v['esperado']
            elif v['tipo'] == 'zero':
                ok = int(val) == 0
            elif v['tipo'] == 'gt':
                ok = int(val) > v['esperado']
            else:
                ok = False

            resultados.append({
                'id'      : v['id'],
                'desc'    : v['desc'],
                'ok'      : ok,
                'valor'   : val,
                'esperado': v['esperado'],
            })
        except Exception as e:
            resultados.append({
                'id'      : v['id'],
                'desc'    : v['desc'],
                'ok'      : False,
                'valor'   : f'ERROR: {e}',
                'esperado': v['esperado'],
            })

    passed = sum(1 for r in resultados if r['ok'])
    failed = len(resultados) - passed

    return {
        'total'   : len(resultados),
        'passed'  : passed,
        'failed'  : failed,
        'detalles': resultados,
    }