# SalesHealth Analytics

> Entorno analítico completo sobre datos de venta de productos de salud — Data Warehouse, ETL, métricas de cliente y dashboard interactivo.

**Proyecto Final · Gestión de Bases de Datos · 3º Ingeniería Matemática · UAX 2025/2026**  
**Autor:** Pablo Jiménez Girardeau

---

## Descripción

Construcción de un entorno analítico end-to-end sobre una base de datos operacional de venta de 50 productos de salud. El proyecto incluye modelado dimensional (Kimball), pipeline ETL idempotente, cálculo de métricas de cliente (CLTV, AOV, Return Rate), segmentación K-Means y un dashboard interactivo de 10 páginas.

---

## Arquitectura

```
public (OLTP, 17 tablas)
    ↓ ETL
stg (staging, 17 tablas)
    ↓
dwh (estrella Kimball: 2 hechos + 7 dimensiones)
    ↓
marts (customer_360: CLTV + clustering por cliente)
```

Una única base de datos PostgreSQL (`saleshealth`) con 4 schemas separados. Los JOINs entre capas son directos sin necesidad de conexiones externas.

---

## Estructura del repositorio

```
saleshealth-analytics/
├── dashboard.html              # Dashboard interactivo (10 páginas)
├── export_data.py              # Generador del JSON del dashboard
├── etl/
│   ├── run_etl.py              # Punto de entrada del pipeline
│   ├── extract.py              # Extracción public → stg
│   ├── load_dimensions.py      # Carga de 7 dimensiones
│   ├── load_facts.py           # Carga de fact_ventas y fact_devoluciones
│   ├── validate.py             # 21 validaciones automáticas
│   ├── customer_360.py         # CLTV, AOV, Return Rate por cliente
│   └── clusters.py             # PCA + K-Means K=3
├── notebooks/
│   ├── 10_metricas_cliente.ipynb   # Análisis CLTV, AOV, Return Rate
│   └── 11_clustering.ipynb         # PCA + segmentación de clientes
├── docs/
│   ├── documento_tecnico.docx      # Documento técnico (5 hojas)
│   ├── er_operacional_dbdiagram.png
│   ├── modelo_dimensional.png
│   └── GD_ProyectoFinal.pdf        # Enunciado oficial
├── reports/
│   └── dashboard_data.js       # Datos del dashboard (generado por export_data.py)
└── .gitignore
```

---

## Entregables oficiales

| # | Entregable | Archivo |
|---|-----------|---------|
| 1 | Diagrama Modelo Entidad-Relación | `docs/er_operacional_dbdiagram.png` |
| 2 | Diagrama Modelo Dimensional | `docs/modelo_dimensional.png` |
| 3 | ETL de datos | `etl/` |
| 4 | Cálculo y análisis de CLTV | `notebooks/10_metricas_cliente.ipynb` |
| 5 | PCA y clustering | `notebooks/11_clustering.ipynb` |
| 6 | Documento técnico (máx. 5 hojas) | `docs/documento_tecnico.docx` |

---

## Stack tecnológico

- **Base de datos:** PostgreSQL 18
- **ETL:** Python 3 · SQLAlchemy · psycopg2
- **Análisis:** pandas · scikit-learn · matplotlib
- **Dashboard:** HTML + JavaScript + Chart.js (sin dependencias de servidor)
- **Modelado:** Metodología Kimball — esquema estrella

---

## Cómo ejecutar

### Prerrequisitos
- PostgreSQL 18 con la base de datos `saleshealth` cargada
- Python 3.10+

### 1. Instalar dependencias
```bash
pip install sqlalchemy psycopg2-binary pandas scikit-learn matplotlib
```

### 2. Configurar conexión
Crear un archivo `.env` en la raíz (no incluido en el repo por seguridad):
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=saleshealth
DB_USER=postgres
DB_PASS=tu_contraseña
```

### 3. Ejecutar el ETL
```bash
python -m etl.run_etl
```
Tiempo estimado: ~18 segundos. 21/21 validaciones automáticas.

### 4. Generar datos del dashboard
```bash
python export_data.py
```

### 5. Abrir el dashboard
```bash
python -m http.server 8080
```
Navegar a `http://localhost:8080/dashboard.html`

---

## Resultados principales

| Métrica | Valor |
|---------|-------|
| Clientes analizados | 5.750 |
| CLTV total | €3,7M |
| CLTV medio / mediana | €643 / €52 |
| AOV medio | €118 |
| Return Rate global | 2,85% |
| Champions (13% clientes) | 91,6% del CLTV total |
| Silhouette Score K=3 | 0,847 |

### Segmentos K-Means

| Segmento | Clientes | % Total | CLTV medio |
|----------|----------|---------|------------|
| Champions | 750 | 13% | €4.512 |
| Base | 4.589 | 80% | €67 |
| Churned | 411 | 7% | €10 |

---

## Dashboard

10 páginas interactivas con selectores, comparadores y gráficas dinámicas:

1. Resumen Ejecutivo
2. Inicio — KPIs con comparativa YoY
3. KPIs Globales — evolución mensual y estacionalidad
4. Devoluciones — motivos, evolución, productos
5. Análisis Cliente — Pareto, Customer 360
6. Productos — selector interactivo + comparador
7. Marcas & Categorías — selector + evolución
8. Rentabilidad — márgenes, costes, evolución
9. Tiendas — selector individual + comparador hasta 4
10. Tendencias — YoY, crecimiento, productos en declive

---

## Licencia

Proyecto académico · UAX 2025/2026. No destinado a uso comercial.
