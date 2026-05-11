# SalesHealth Analytics

> Entorno analítico completo sobre datos de venta de productos de salud — Data Warehouse, ETL, métricas de cliente y dashboard interactivo.

**Proyecto Final · Gestión de Bases de Datos · 3º Ingeniería Matemática · UAX 2025/2026**  
**Autor:** Pablo Jiménez Girardeau

---

## 🔗 Dashboard en vivo

👉 **[Abrir Dashboard Interactivo](https://pablojimenezgirardeau.github.io/saleshealth-analytics/dashboard.html)**

---

## Descripción

Construcción de un entorno analítico end-to-end sobre una base de datos operacional de venta de 50 productos de salud. El proyecto incluye modelado dimensional (Kimball), pipeline ETL idempotente, cálculo de métricas de cliente (CLTV, AOV, Return Rate), segmentación K-Means y un dashboard interactivo de 10 páginas.

---

## Mapa del proyecto

```
DATOS OPERACIONALES (PostgreSQL · saleshealth)
│
│   ERP (10 tablas)        CRM (2 tablas)
│   ventas, productos      clientes, zonas
│   tiendas, ofertas
│                          Logística (3 tablas)
│   Postventa (2 tablas)   almacenes, inventario
│   devoluciones
│
▼
┌─────────────────────────────────────────┐
│  FASE 1 — Calidad de Datos              │
│  10 problemas detectados · 3 corregidos │
│  Regla: nunca eliminar clientes         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  FASE 2 — Modelo ER                     │
│  17 tablas · 4 sistemas de origen       │
│  Diagrama: docs/er_operacional.png      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  FASE 3 — Modelo Dimensional (Kimball)  │
│  2 hechos + 7 dimensiones               │
│  fact_ventas (42.555) + fact_devoluc.   │
│  Diagrama: docs/modelo_dimensional.png  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  FASE 4 — Pipeline ETL                  │
│  public → stg → dwh → marts             │
│  Idempotente · 21/21 validaciones OK    │
│  Tiempo: ~18s · python -m etl.run_etl   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  FASE 5 — Métricas de Cliente           │
│  CLTV · AOV · Return Rate               │
│  marts.customer_360 (5.750 clientes)    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  FASE 6 — PCA + Clustering K-Means      │
│  K=3 · Silhouette 0.847                 │
│  Champions / Base / Churned             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  DASHBOARD INTERACTIVO (HTML + JS)      │
│  10 páginas · sin dependencias server   │
│  Chart.js · selectores · comparadores  │
└─────────────────────────────────────────┘
```

---

## Arquitectura de la BD

```
public (OLTP · 17 tablas)
    ↓ ETL extract
stg (staging · 17 tablas)
    ↓ ETL load
dwh (estrella Kimball · 2 hechos + 7 dims)
    ↓ ETL customer_360 + clusters
marts (customer_360 · 5.750 filas)
```

Una única base de datos PostgreSQL (`saleshealth`) con 4 schemas separados. JOINs directos entre capas sin conexiones externas.

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
│   ├── fase1/                  # Exploración y limpieza de datos
│   ├── fase2_er/               # Modelo Entidad-Relación
│   ├── fase3_dwh/              # Modelo Dimensional
│   ├── fase5_metricas/         # Análisis CLTV, AOV, Return Rate
│   └── fase6_clustering/       # PCA + segmentación de clientes
├── docs/
│   ├── documento_tecnico.docx  # Documento técnico (5 hojas)
│   ├── er_operacional_dbdiagram.png
│   ├── modelo_dimensional.png
│   └── GD_ProyectoFinal.pdf    # Enunciado oficial
├── reports/
│   └── dashboard_data.js       # Datos del dashboard (generado)
└── .gitignore
```

---

## Entregables oficiales

| # | Entregable | Archivo |
|---|-----------|---------|
| 1 | Diagrama Modelo Entidad-Relación | `docs/diagramas/er_operacional_dbdiagram.png` |
| 2 | Diagrama Modelo Dimensional | `docs/diagramas/modelo_dimensional.png` |
| 3 | ETL de datos | `etl/` |
| 4 | Cálculo y análisis de CLTV | `notebooks/fase5_metricas/10_metricas_cliente.ipynb` |
| 5 | PCA y clustering | `notebooks/fase6_clustering/11_clustering.ipynb` |
| 6 | Documento técnico (máx. 5 hojas) | `documento_tecnico.docx` |

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

## Stack tecnológico

- **Base de datos:** PostgreSQL 18
- **ETL:** Python 3 · SQLAlchemy · psycopg2
- **Análisis:** pandas · scikit-learn · matplotlib
- **Dashboard:** HTML + JavaScript + Chart.js (sin dependencias de servidor)
- **Modelado:** Metodología Kimball — esquema estrella

---

## Cómo ejecutar

### 1. Instalar dependencias
```bash
pip install sqlalchemy psycopg2-binary pandas scikit-learn matplotlib
```

### 2. Configurar conexión
Crear `etl/config.py` con las credenciales (no incluido por seguridad).

### 3. Ejecutar el ETL
```bash
python -m etl.run_etl
```

### 4. Generar datos del dashboard
```bash
python export_data.py
```

### 5. Abrir el dashboard localmente
```bash
python -m http.server 8080
# → http://localhost:8080/dashboard.html
```

O directamente online: **[Dashboard en GitHub Pages](https://pablojimenezgirardeau.github.io/saleshealth-analytics/dashboard.html)**

---

## Licencia

Proyecto académico · UAX 2025/2026. No destinado a uso comercial.
