"""
load_dimensions.py — Fase 2: LOAD DIMENSIONES
Transforma y carga las 7 dimensiones del DWH desde stg.*.
Cada dimension incluye un registro especial 'desconocido' (SK = -1).
"""

from etl.config import SCHEMA_STG, SCHEMA_DWH
from etl.db import get_engine, execute, table_count


def _load_dim_fecha(engine) -> int:
    """
    Genera dim_fecha con todos los dias del rango de ventas.
    No viene del staging — se genera a partir del rango de fechas en stg.sale.
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_fecha CASCADE')
    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_fecha (
            fecha_sk, fecha, anio, trimestre, mes, mes_nombre,
            semana, dia, dia_semana, dia_semana_nombre, es_fin_de_semana
        )
        SELECT
            TO_CHAR(d, 'YYYYMMDD')::INTEGER             AS fecha_sk,
            d::DATE                                      AS fecha,
            EXTRACT(YEAR    FROM d)::SMALLINT            AS anio,
            EXTRACT(QUARTER FROM d)::SMALLINT            AS trimestre,
            EXTRACT(MONTH   FROM d)::SMALLINT            AS mes,
            TO_CHAR(d, 'TMMonth')                        AS mes_nombre,
            EXTRACT(WEEK    FROM d)::SMALLINT            AS semana,
            EXTRACT(DAY     FROM d)::SMALLINT            AS dia,
            EXTRACT(ISODOW  FROM d)::SMALLINT            AS dia_semana,
            TO_CHAR(d, 'TMDay')                          AS dia_semana_nombre,
            EXTRACT(ISODOW  FROM d) IN (6, 7)            AS es_fin_de_semana
        FROM generate_series(
            (SELECT MIN(sale_date::DATE) FROM {SCHEMA_STG}.sale),
            (SELECT MAX(sale_date::DATE) FROM {SCHEMA_STG}.sale),
            '1 day'::INTERVAL
        ) AS d
        ON CONFLICT (fecha_sk) DO NOTHING
    """)
    return n


def _load_dim_cliente(engine) -> int:
    """Carga dim_cliente desde stg.customer."""
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_cliente RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_cliente
            (cliente_nk, nombre, apellido, apellido2, email, telefono, fecha_alta, es_desconocido)
        VALUES (-1, 'Desconocido', '', NULL, NULL, NULL, NULL, TRUE)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_cliente
            (cliente_nk, nombre, apellido, apellido2, email, telefono, fecha_alta, es_desconocido)
        SELECT
            customer_id,
            first_name,
            last_name,
            last_name2,
            email,
            phone,
            created_at,
            FALSE
        FROM {SCHEMA_STG}.customer
        ORDER BY customer_id
    """)
    return n


def _load_dim_producto(engine) -> int:
    """
    Carga dim_producto enriquecido con categoria, marca y coste
    desde stg.product + stg.central_product + stg.brand + stg.category.
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_producto RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_producto
            (producto_nk, nombre, categoria, marca, precio_venta,
             coste_unitario, margen_pct, sku, coste_imputado)
        VALUES (-1, 'Desconocido', NULL, NULL, NULL, NULL, NULL, NULL, FALSE)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_producto
            (producto_nk, nombre, categoria, marca, precio_venta,
             coste_unitario, margen_pct, sku, coste_imputado)
        SELECT
            p.product_id,
            p.name,
            cat.name                                                         AS categoria,
            b.name                                                           AS marca,
            p.price                                                          AS precio_venta,
            cp.unit_cost                                                     AS coste_unitario,
            ROUND((p.price - cp.unit_cost) / NULLIF(p.price, 0) * 100, 2)  AS margen_pct,
            cp.sku,
            CASE WHEN p.product_id = 29 THEN TRUE ELSE FALSE END            AS coste_imputado
        FROM {SCHEMA_STG}.product p
        LEFT JOIN {SCHEMA_STG}.central_product cp ON p.product_id = cp.product_id
        LEFT JOIN {SCHEMA_STG}.category cat        ON cp.category_id = cat.category_id
        LEFT JOIN {SCHEMA_STG}.brand b             ON cp.brand_id = b.brand_id
        ORDER BY p.product_id
    """)
    return n


def _load_dim_tienda(engine) -> int:
    """Carga dim_tienda desde stg.store."""
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_tienda RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_tienda
            (tienda_nk, nombre, direccion, ciudad, codigo_postal, latitud, longitud)
        VALUES (-1, 'Desconocida', NULL, NULL, NULL, NULL, NULL)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_tienda
            (tienda_nk, nombre, direccion, ciudad, codigo_postal, latitud, longitud)
        SELECT
            store_id,
            name,
            address,
            city,
            postal_code,
            latitude,
            longitude
        FROM {SCHEMA_STG}.store
        ORDER BY store_id
    """)
    return n


def _load_dim_zona(engine) -> int:
    """
    Carga dim_zona desde stg.city_zone.
    Incluye registro 'Desconocida' para clientes sin zona asignada.
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_zona RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_zona
            (codigo_postal, distrito, tipo_area, orientacion, ciudad, es_desconocida)
        VALUES ('00000', 'Desconocido', NULL, NULL, NULL, TRUE)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_zona
            (codigo_postal, distrito, tipo_area, orientacion, ciudad, es_desconocida)
        SELECT
            postal_code,
            district,
            area_type,
            zone_orientation,
            city,
            FALSE
        FROM {SCHEMA_STG}.city_zone
        ORDER BY postal_code
    """)
    return n


def _load_dim_oferta(engine) -> int:
    """
    Carga dim_oferta desde stg.offer.
    Inserta registro especial 'Sin oferta' para lineas sin descuento.
    """
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_oferta RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_oferta
            (oferta_nk, nombre, descripcion, descuento_pct, fecha_inicio, fecha_fin, es_sin_oferta)
        VALUES (NULL, 'Sin oferta', 'Venta sin descuento aplicado', 0, NULL, NULL, TRUE)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_oferta
            (oferta_nk, nombre, descripcion, descuento_pct, fecha_inicio, fecha_fin, es_sin_oferta)
        SELECT
            offer_id,
            name,
            description,
            discount_percent,
            start_date,
            end_date,
            FALSE
        FROM {SCHEMA_STG}.offer
        ORDER BY offer_id
    """)
    return n


def _load_dim_motivo_devolucion(engine) -> int:
    """Carga dim_motivo_devolucion desde stg.return_reason."""
    execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.dim_motivo_devolucion RESTART IDENTITY CASCADE')

    execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_motivo_devolucion
            (motivo_nk, motivo, activo, es_desconocido)
        VALUES (NULL, 'Desconocido', TRUE, TRUE)
    """)

    n = execute(engine, f"""
        INSERT INTO {SCHEMA_DWH}.dim_motivo_devolucion
            (motivo_nk, motivo, activo, es_desconocido)
        SELECT
            reason_id,
            reason,
            active,
            FALSE
        FROM {SCHEMA_STG}.return_reason
        ORDER BY reason_id
    """)
    return n


def load_dimensions(engine) -> dict:
    """
    Carga las 7 dimensiones en orden.
    Trunca primero todos los hechos y dimensiones con CASCADE
    para evitar errores de FK.
    Devuelve dict con el conteo de registros cargados por dimension.
    """
    # Truncar todo el DWH en orden correcto (hechos primero)
    for tabla in ['fact_ventas', 'fact_devoluciones',
                  'dim_fecha', 'dim_cliente', 'dim_producto',
                  'dim_tienda', 'dim_zona', 'dim_oferta',
                  'dim_motivo_devolucion']:
        execute(engine, f'TRUNCATE TABLE {SCHEMA_DWH}.{tabla} RESTART IDENTITY CASCADE')

    loaders = {
        'dim_fecha'             : _load_dim_fecha,
        'dim_cliente'           : _load_dim_cliente,
        'dim_producto'          : _load_dim_producto,
        'dim_tienda'            : _load_dim_tienda,
        'dim_zona'              : _load_dim_zona,
        'dim_oferta'            : _load_dim_oferta,
        'dim_motivo_devolucion' : _load_dim_motivo_devolucion,
    }

    resultados = {}
    for nombre, loader in loaders.items():
        n = loader(engine)
        total = table_count(engine, SCHEMA_DWH, nombre)
        resultados[nombre] = total

    return resultados