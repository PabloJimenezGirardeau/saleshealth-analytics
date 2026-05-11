-- ============================================================
-- DDL Data Warehouse — saleshealth
-- Schema: dwh
-- Metodologia: Kimball (esquema estrella)
-- Grano: 1 fila = 1 linea de venta (sale_item)
-- ============================================================

-- Crear schema
CREATE SCHEMA IF NOT EXISTS dwh;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS marts;


-- ── dim_fecha ────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_fecha CASCADE;
CREATE TABLE dwh.dim_fecha (
    fecha_sk            INTEGER         PRIMARY KEY,  -- YYYYMMDD
    fecha               DATE            NOT NULL,
    anio                SMALLINT        NOT NULL,
    trimestre           SMALLINT        NOT NULL,     -- 1-4
    mes                 SMALLINT        NOT NULL,     -- 1-12
    mes_nombre          VARCHAR(20)     NOT NULL,
    semana              SMALLINT        NOT NULL,     -- 1-53
    dia                 SMALLINT        NOT NULL,     -- 1-31
    dia_semana          SMALLINT        NOT NULL,     -- 1=Lunes ... 7=Domingo
    dia_semana_nombre   VARCHAR(20)     NOT NULL,
    es_fin_de_semana    BOOLEAN         NOT NULL DEFAULT FALSE
);

-- ── dim_cliente ───────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_cliente CASCADE;
CREATE TABLE dwh.dim_cliente (
    cliente_sk          SERIAL          PRIMARY KEY,
    cliente_nk          INTEGER         NOT NULL,     -- customer.customer_id
    nombre              VARCHAR(100),
    apellido            VARCHAR(100),
    apellido2           VARCHAR(100),
    email               VARCHAR(200),
    telefono            VARCHAR(20),
    fecha_alta          TIMESTAMP,
    -- Dimension especial para clientes sin datos
    es_desconocido      BOOLEAN         NOT NULL DEFAULT FALSE
);

-- ── dim_producto ──────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_producto CASCADE;
CREATE TABLE dwh.dim_producto (
    producto_sk         SERIAL          PRIMARY KEY,
    producto_nk         INTEGER         NOT NULL,     -- product.product_id
    nombre              VARCHAR(200)    NOT NULL,
    categoria           VARCHAR(100),
    marca               VARCHAR(100),
    precio_venta        NUMERIC(10,2),
    coste_unitario      NUMERIC(10,2),
    margen_pct          NUMERIC(6,2),
    sku                 VARCHAR(50),
    coste_imputado      BOOLEAN         NOT NULL DEFAULT FALSE  -- flag producto 29
);

-- ── dim_tienda ────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_tienda CASCADE;
CREATE TABLE dwh.dim_tienda (
    tienda_sk           SERIAL          PRIMARY KEY,
    tienda_nk           INTEGER         NOT NULL,     -- store.store_id
    nombre              VARCHAR(100)    NOT NULL,
    direccion           VARCHAR(200),
    ciudad              VARCHAR(100),
    codigo_postal       VARCHAR(10),
    latitud             NUMERIC(10,6),
    longitud            NUMERIC(10,6)
);

-- ── dim_zona ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_zona CASCADE;
CREATE TABLE dwh.dim_zona (
    zona_sk             SERIAL          PRIMARY KEY,
    codigo_postal       VARCHAR(10)     NOT NULL,     -- city_zone.postal_code (NK)
    distrito            VARCHAR(100),
    tipo_area           VARCHAR(50),                  -- Centrica / Periferica
    orientacion         VARCHAR(50),                  -- Norte / Sur / Este / Oeste
    ciudad              VARCHAR(100),
    es_desconocida      BOOLEAN         NOT NULL DEFAULT FALSE
);

-- ── dim_oferta ────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_oferta CASCADE;
CREATE TABLE dwh.dim_oferta (
    oferta_sk           SERIAL          PRIMARY KEY,
    oferta_nk           INTEGER,                      -- offer.offer_id (NULL = sin oferta)
    nombre              VARCHAR(200)    NOT NULL,
    descripcion         TEXT,
    descuento_pct       NUMERIC(5,2),
    fecha_inicio        DATE,
    fecha_fin           DATE,
    es_sin_oferta       BOOLEAN         NOT NULL DEFAULT FALSE
);

-- ── dim_motivo_devolucion ─────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_motivo_devolucion CASCADE;
CREATE TABLE dwh.dim_motivo_devolucion (
    motivo_sk           SERIAL          PRIMARY KEY,
    motivo_nk           INTEGER,                      -- return_reason.reason_id
    motivo              VARCHAR(200)    NOT NULL,
    activo              BOOLEAN         NOT NULL DEFAULT TRUE,
    es_desconocido      BOOLEAN         NOT NULL DEFAULT FALSE
);




-- ── fact_ventas ───────────────────────────────────────────────────────────────
-- Grano: 1 fila = 1 linea de venta (sale_item)
DROP TABLE IF EXISTS dwh.fact_ventas CASCADE;
CREATE TABLE dwh.fact_ventas (
    -- Claves subrogadas (FKs a dimensiones)
    fecha_sk            INTEGER         NOT NULL REFERENCES dwh.dim_fecha(fecha_sk),
    cliente_sk          INTEGER         NOT NULL REFERENCES dwh.dim_cliente(cliente_sk),
    producto_sk         INTEGER         NOT NULL REFERENCES dwh.dim_producto(producto_sk),
    tienda_sk           INTEGER         NOT NULL REFERENCES dwh.dim_tienda(tienda_sk),
    zona_sk             INTEGER         NOT NULL REFERENCES dwh.dim_zona(zona_sk),
    oferta_sk           INTEGER         NOT NULL REFERENCES dwh.dim_oferta(oferta_sk),
    -- Claves naturales (trazabilidad al origen)
    sale_id             INTEGER         NOT NULL,
    sale_item_id        INTEGER         NOT NULL,
    -- Metricas
    cantidad            INTEGER         NOT NULL,
    precio_unitario     NUMERIC(10,2)   NOT NULL,
    subtotal_bruto      NUMERIC(10,2)   NOT NULL,   -- cantidad * precio_unitario
    coste_total         NUMERIC(10,2),              -- cantidad * coste_unitario
    margen_bruto        NUMERIC(10,2),              -- subtotal_bruto - coste_total
    margen_pct          NUMERIC(6,2),               -- margen_bruto / subtotal_bruto * 100
    -- Flag de devolucion (para CLTV neto sin JOIN a fact_devoluciones)
    es_devuelta         BOOLEAN         NOT NULL DEFAULT FALSE,
    cantidad_devuelta   INTEGER         NOT NULL DEFAULT 0,
    subtotal_neto       NUMERIC(10,2),              -- subtotal_bruto ajustado por devoluciones
    -- Clave primaria compuesta
    PRIMARY KEY (sale_item_id)
);

-- ── fact_devoluciones ─────────────────────────────────────────────────────────
-- Grano: 1 fila = 1 devolucion (return_item)
DROP TABLE IF EXISTS dwh.fact_devoluciones CASCADE;
CREATE TABLE dwh.fact_devoluciones (
    -- Claves subrogadas
    fecha_sk            INTEGER         NOT NULL REFERENCES dwh.dim_fecha(fecha_sk),
    cliente_sk          INTEGER         NOT NULL REFERENCES dwh.dim_cliente(cliente_sk),
    producto_sk         INTEGER         NOT NULL REFERENCES dwh.dim_producto(producto_sk),
    tienda_sk           INTEGER         NOT NULL REFERENCES dwh.dim_tienda(tienda_sk),
    motivo_sk           INTEGER         NOT NULL REFERENCES dwh.dim_motivo_devolucion(motivo_sk),
    -- Claves naturales
    return_id           INTEGER         NOT NULL,
    sale_item_id        INTEGER         NOT NULL,   -- referencia al item original
    -- Metricas
    cantidad_devuelta   INTEGER         NOT NULL,
    importe_devuelto    NUMERIC(10,2),              -- cantidad_devuelta * precio_unitario
    coste_devuelto      NUMERIC(10,2),              -- cantidad_devuelta * coste_unitario
    -- Clave primaria
    PRIMARY KEY (return_id)
);


