# Proyecto Final — Gestion de Datos (UAX)

## Base de datos
- **Nombre:** `saleshealth` (PostgreSQL)
- **Conexion:** localhost:5432, usuario `postgres`
- **17 tablas:** brand, category, central_inventory, central_product, city_zone, customer, inventory, offer, product, product_offer, return_item, return_reason, sale, sale_item, store, warehouse, warehouse_location
- **Herramienta de gestion:** DBeaver

## Contexto de negocio
Venta de 50 productos relacionados con la salud. El objetivo es construir un entorno analitico (Data Warehouse) y calcular metricas de cliente, especialmente el Customer Lifetime Value (CLTV).

## Regla clave de la profesora
> **No se puede eliminar ningun cliente.** Si los datos son incorrectos, NULL o sin logica, hay que corregirlos o buscar una logica, pero NUNCA borrar clientes.

## Volumenes de datos principales
| Tabla | Registros |
|-------|-----------|
| sale_item | 42.555 |
| sale | 20.000 |
| customer | 5.750 |
| return_item | 2.330 |
| inventory | 1.000 |
| product / central_product | 50 |
| city_zone | 42 |
| warehouse_location | 40 |
| brand | 29 |
| store | 20 |
| product_offer | 6 |
| category | 6 |
| return_reason | 6 |
| warehouse | 1 |
| offer | 1 |

---

## Etapas del proyecto

### Fase 1 — Exploracion y Limpieza de Datos 
**Archivo:** `fase1_exploracion_limpieza.ipynb`

Problemas detectados y decisiones:

| # | Problema | Decision |
|---|----------|----------|
| 1 | 568 telefonos con longitud incorrecta (10-12 chars en vez de 13) | Se conservan — no reconstruibles |
| 2 | 2.930 clientes comparten nombre+apellido | No es error — customer_id es unico |
| 3 | Venta 13009 con total erroneo (+3 EUR) | **Corregido** — total recalculado desde lineas |
| 4 | 8 lineas con descuento aplicado pero offer_id NULL | **Corregido** — asignado offer_id = 1 |
| 5 | Producto 29 ("Sensor temperatura inteligente") sin registro en central_product | **Corregido** — insertado con coste imputado por mediana (59.94 EUR) |
| 6 | Integridad referencial entre todas las tablas | Sin problemas |

### Fase 2 — Modelo Entidad-Relacion (ER) ⬜ PENDIENTE
- Documentar el diagrama ER de la base de datos operacional (las 17 tablas)
- Identificar fuentes: ERP (ventas, inventario), CRM (clientes), logistica (almacenes), postventa (devoluciones)
- **Entregable:** Diagrama ER

### Fase 3 — Modelo Dimensional (Data Warehouse) ⬜ PENDIENTE
- Disenar esquema estrella con tablas de hechos y dimensiones
- Hechos candidatos: `fact_ventas`, `fact_devoluciones`
- Dimensiones candidatas: `dim_cliente`, `dim_producto`, `dim_tienda`, `dim_tiempo`, `dim_zona`
- **Entregable:** Diagrama del modelo dimensional

### Fase 4 — Arquitectura Data Lake a DWH ⬜ PENDIENTE
- Definir el flujo de datos: origen (PostgreSQL operacional) → transformacion → DWH
- Documentar la arquitectura del pipeline
- **Entregable:** Diagrama de arquitectura

### Fase 5 — ETL (Extract, Transform, Load) ⬜ PENDIENTE
- Pipeline que extrae datos de las tablas operacionales, transforma y carga en el DWH
- Implementacion con Python (psycopg2/SQLAlchemy) o SQL
- **Entregable:** Codigo ETL funcional

### Fase 6 — Calculo de CLTV y metricas de cliente ⬜ PENDIENTE
- **Formula CLTV** = Ingresos_t x Margen_t x Frecuencia_t x R_t
  - Ingresos por cliente desde ventas historicas
  - Margen de beneficio (precio venta - coste unitario)
  - Frecuencia de compra
  - Vida util del cliente (tiempo entre primera y ultima compra)
- Posibilidad de anadir hasta 2 metricas adicionales (ej: tasa de devolucion, recencia)
- **Entregable:** Calculo y analisis del CLTV

### Fase 7 — PCA y Clustering ⬜ PENDIENTE
- Analisis de componentes principales (PCA) sobre metricas de cliente
- Clustering (K-Means u otro) para segmentar clientes
- Visualizacion de segmentos
- **Entregable:** Analisis PCA + clustering

### Fase 8 — Documento tecnico ⬜ PENDIENTE
- Resumen del proyecto completo
- **Maximo 5 hojas (10 caras)**
- **Entregable:** Documento final

---

## Entregables segun el PDF
1. Diagrama del Modelo Entidad-Relacion
2. Diagrama del Modelo Dimensional (tablas de hechos y dimensiones)
3. ETL de datos
4. Calculo y analisis de CLTV (+ hasta 2 analiticas adicionales)
5. PCA y clustering en funcion de CLTV
6. Documento tecnico (max 5 hojas / 10 caras)
