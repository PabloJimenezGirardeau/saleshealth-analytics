"""
export_data.py — Fase 7: Exportación de datos para el dashboard HTML
Genera dashboard_data.js con todos los datos para las 7 páginas.
Ejecutar desde la raíz del proyecto:
    python export_data.py
"""

import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from pathlib import Path

# ── Conexión ─────────────────────────────────────────────────────────────────
DB_URL = 'postgresql+psycopg2://postgres:pimpum.postgre@localhost:5432/saleshealth'
engine = create_engine(DB_URL)

def query(sql):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)

OUTPUT_PATH = Path('reports/dashboard_data.json')
JS_PATH     = Path('reports/dashboard_data.js')
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

FEATURES = [
    'cltv', 'ingresos_netos', 'aov',
    'frecuencia_mensual', 'recencia_dias',
    'return_rate', 'antiguedad_dias'
]

def pct_change(actual, anterior):
    if anterior and anterior != 0:
        return round((actual - anterior) / abs(anterior) * 100, 1)
    return None

print('Exportando datos para el dashboard...')
data = {}


# ════════════════════════════════════════════════════════════════════════════
# 1. INICIO — KPIs + comparativas + hallazgos + salud + clustering resumen
# ════════════════════════════════════════════════════════════════════════════
print('  [1/7] Inicio...')

kpis_raw = query("""
    SELECT
        SUM(subtotal_neto)      AS ingresos_netos,
        SUM(subtotal_bruto)     AS ingresos_brutos,
        AVG(precio_unitario)    AS aov,
        AVG(margen_pct)         AS margen_pct_medio,
        COUNT(DISTINCT sale_id) AS num_ventas
    FROM dwh.fact_ventas
""")

devol_raw = query("""
    SELECT COUNT(*) AS num_devoluciones, SUM(importe_devuelto) AS importe_devuelto
    FROM dwh.fact_devoluciones
""")

clientes_raw = query("""
    SELECT COUNT(*) AS num_clientes FROM marts.customer_360 WHERE cltv IS NOT NULL
""")

return_rate_raw = query("""
    SELECT SUM(cantidad_devuelta)::float / NULLIF(SUM(cantidad),0)*100 AS return_rate
    FROM dwh.fact_ventas
""")

# Mes actual
mes_actual = query("""
    WITH ultimo AS (
        SELECT MAX(anio) AS anio, MAX(mes) AS mes
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    )
    SELECT SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    JOIN ultimo u ON df.anio=u.anio AND df.mes=u.mes
""")

# Mes anterior
mes_anterior = query("""
    WITH ultimo AS (
        SELECT MAX(anio) AS anio, MAX(mes) AS mes
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    ),
    ant AS (
        SELECT CASE WHEN mes=1 THEN anio-1 ELSE anio END AS anio,
               CASE WHEN mes=1 THEN 12 ELSE mes-1 END AS mes FROM ultimo
    )
    SELECT SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    JOIN ant a ON df.anio=a.anio AND df.mes=a.mes
""")

# Mismo mes año anterior
mes_anio_ant = query("""
    WITH ultimo AS (
        SELECT MAX(anio) AS anio, MAX(mes) AS mes
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    )
    SELECT SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    JOIN ultimo u ON df.anio=u.anio-1 AND df.mes=u.mes
""")

# Sparkline últimos 12 meses + ratio devoluciones
sparkline = query("""
    WITH rng AS (
        SELECT MAX(anio*100+mes)-11 AS min_ym
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    )
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    JOIN rng ON df.anio*100+df.mes >= rng.min_ym
    GROUP BY df.anio, df.mes
    ORDER BY df.anio, df.mes
""")

devol_sparkline = query("""
    WITH rng AS (
        SELECT MAX(anio*100+mes)-11 AS min_ym
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    )
    SELECT df.anio, df.mes, COUNT(*) AS num_devoluciones
    FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_fecha df ON fd.fecha_sk=df.fecha_sk
    JOIN rng ON df.anio*100+df.mes >= rng.min_ym
    GROUP BY df.anio, df.mes
    ORDER BY df.anio, df.mes
""")

# Top 3 productos mes actual
top3_mes = query("""
    WITH ultimo AS (
        SELECT MAX(anio) AS anio, MAX(mes) AS mes
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    )
    SELECT dp.nombre AS producto, SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    JOIN ultimo u ON df.anio=u.anio AND df.mes=u.mes
    GROUP BY dp.nombre
    ORDER BY ingresos_netos DESC LIMIT 3
""")

# Resumen clustering para Inicio
cl_resumen = query("""
    SELECT cluster_label,
           COUNT(*) AS n,
           ROUND(AVG(cltv)::numeric,2) AS cltv_medio,
           ROUND(SUM(cltv)::numeric,2) AS cltv_total
    FROM marts.customer_360
    WHERE cltv IS NOT NULL AND cluster_label IS NOT NULL
    GROUP BY cluster_label
""")

# Calcular salud del negocio
rr   = float(return_rate_raw['return_rate'].iloc[0] or 0)
mg   = float(kpis_raw['margen_pct_medio'].iloc[0] or 0)
rec  = float(query("SELECT AVG(recencia_dias) AS r FROM marts.customer_360 WHERE cltv IS NOT NULL")['r'].iloc[0] or 0)

def health_score(rr, mg, rec):
    score = 0
    # Return rate: <5% verde, <15% amarillo, resto rojo
    score += 2 if rr < 5 else (1 if rr < 15 else 0)
    # Margen: >40% verde, >25% amarillo, resto rojo
    score += 2 if mg > 40 else (1 if mg > 25 else 0)
    # Recencia: <90d verde, <180d amarillo, resto rojo
    score += 2 if rec < 90 else (1 if rec < 180 else 0)
    if score >= 5: return 'verde'
    if score >= 3: return 'amarillo'
    return 'rojo'

ing_act  = float(mes_actual['ingresos_netos'].iloc[0] or 0)
ing_ant  = float(mes_anterior['ingresos_netos'].iloc[0] or 0)
ing_yoy  = float(mes_anio_ant['ingresos_netos'].iloc[0] or 0)
v_act    = int(mes_actual['num_ventas'].iloc[0] or 0)
v_ant    = int(mes_anterior['num_ventas'].iloc[0] or 0)

# Ratio devoluciones por mes (alinear con sparkline)
sp_labels = sparkline['label'].tolist()
dev_map   = {(r['anio'], r['mes']): int(r['num_devoluciones']) for _, r in devol_sparkline.iterrows()}
ratios    = []
for _, row in sparkline.iterrows():
    ventas = int(row['num_ventas'])
    devol  = dev_map.get((row['anio'], row['mes']), 0)
    ratios.append(round(devol / ventas * 100, 2) if ventas > 0 else 0)

# Hallazgos automáticos
total_cltv_cl = float(cl_resumen['cltv_total'].sum())
champ_row = cl_resumen[cl_resumen['cluster_label']=='Champions']
champ_pct_n   = round(float(champ_row['n'].iloc[0]) / int(clientes_raw['num_clientes'].iloc[0]) * 100, 1) if len(champ_row) else 0
champ_pct_cltv= round(float(champ_row['cltv_total'].iloc[0]) / total_cltv_cl * 100, 1) if len(champ_row) else 0
top_prod = top3_mes['producto'].iloc[0] if len(top3_mes) else '—'
top_motivo_raw = query("""
    SELECT dm.motivo, COUNT(*) AS n FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_motivo_devolucion dm ON fd.motivo_sk=dm.motivo_sk
    WHERE dm.es_desconocido=FALSE GROUP BY dm.motivo ORDER BY n DESC LIMIT 1
""")
top_motivo = top_motivo_raw['motivo'].iloc[0] if len(top_motivo_raw) else '—'
mes_peak_raw = query("""
    SELECT TO_CHAR(TO_DATE(df.mes::text,'MM'),'TMMonth') AS mes_nombre,
           SUM(fv.subtotal_neto) AS total
    FROM dwh.fact_ventas fv JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.mes ORDER BY total DESC LIMIT 1
""")
mes_peak = mes_peak_raw['mes_nombre'].iloc[0] if len(mes_peak_raw) else '—'

# Pareto rápido para hallazgo
cl_par = query("SELECT cltv FROM marts.customer_360 WHERE cltv IS NOT NULL ORDER BY cltv DESC")
cltv_arr  = cl_par['cltv'].values
cltv_cum  = np.cumsum(cltv_arr) / cltv_arr.sum() * 100
idx_80    = int(np.searchsorted(cltv_cum, 80))
pct_cl_80 = round((idx_80+1) / len(cltv_arr) * 100, 1)

cl_resumen_dict = {}
for _, row in cl_resumen.iterrows():
    cl_resumen_dict[row['cluster_label']] = {
        'n'         : int(row['n']),
        'cltv_medio': float(row['cltv_medio']),
        'cltv_total': float(row['cltv_total']),
        'pct'       : round(float(row['n']) / int(clientes_raw['num_clientes'].iloc[0]) * 100, 1),
        'pct_cltv'  : round(float(row['cltv_total']) / total_cltv_cl * 100, 1),
    }

data['kpis'] = {
    'ingresos_netos'  : round(float(kpis_raw['ingresos_netos'].iloc[0] or 0), 2),
    'ingresos_brutos' : round(float(kpis_raw['ingresos_brutos'].iloc[0] or 0), 2),
    'aov'             : round(float(kpis_raw['aov'].iloc[0] or 0), 2),
    'margen_pct_medio': round(mg, 2),
    'num_ventas'      : int(kpis_raw['num_ventas'].iloc[0] or 0),
    'num_devoluciones': int(devol_raw['num_devoluciones'].iloc[0] or 0),
    'importe_devuelto': round(float(devol_raw['importe_devuelto'].iloc[0] or 0), 2),
    'num_clientes'    : int(clientes_raw['num_clientes'].iloc[0] or 0),
    'return_rate'     : round(rr, 2),
    'recencia_media'  : round(rec, 1),
    'health'          : health_score(rr, mg, rec),
    'mes_actual': {
        'ingresos_netos': round(ing_act, 2),
        'num_ventas'    : v_act,
        'var_mes_ant'   : pct_change(ing_act, ing_ant),
        'var_anio_ant'  : pct_change(ing_act, ing_yoy),
        'var_ventas'    : pct_change(v_act, v_ant),
    },
    'sparkline': {
        'labels'           : sp_labels,
        'valores'          : [round(float(v), 2) for v in sparkline['ingresos_netos']],
        'ratio_devoluciones': ratios,
    },
    'top3_mes': {
        'labels' : top3_mes['producto'].tolist(),
        'valores': [round(float(v), 2) for v in top3_mes['ingresos_netos']],
    },
    'cluster_resumen': cl_resumen_dict,
    'hallazgos': [
        f"El {pct_cl_80}% de clientes concentra el 80% del CLTV total",
        f"{mes_peak} es el mes de mayor ingreso histórico",
        f"El producto más vendido este mes es {top_prod}",
        f"El motivo de devolución más frecuente es '{top_motivo}'",
        f"Los Champions ({champ_pct_n}% de clientes) generan el {champ_pct_cltv}% del CLTV",
    ],
}


# ════════════════════════════════════════════════════════════════════════════
# 2. KPIs GLOBALES
# ════════════════════════════════════════════════════════════════════════════
print('  [2/7] KPIs globales...')

evolucion = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           SUM(fv.subtotal_bruto) AS ingresos_brutos
    FROM dwh.fact_ventas fv JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes ORDER BY df.anio, df.mes
""")

top_productos = query("""
    SELECT dp.nombre AS producto,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           SUM(fv.cantidad) AS unidades,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    GROUP BY dp.nombre ORDER BY ingresos_netos DESC LIMIT 10
""")

ventas_tienda = query("""
    SELECT dt.nombre AS tienda,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv JOIN dwh.dim_tienda dt ON fv.tienda_sk=dt.tienda_sk
    WHERE dt.tienda_sk != 1
    GROUP BY dt.nombre ORDER BY ingresos_netos DESC
""")

estacionalidad = query("""
    SELECT df.anio, df.mes, SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes ORDER BY df.anio, df.mes
""")

pivot = estacionalidad.pivot(index='anio', columns='mes', values='ingresos_netos').fillna(0)
meses_nombres = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

data['kpis_globales'] = {
    'evolucion': {
        'labels'         : evolucion['label'].tolist(),
        'ingresos_netos' : [round(float(v),2) for v in evolucion['ingresos_netos']],
        'ingresos_brutos': [round(float(v),2) for v in evolucion['ingresos_brutos']],
    },
    'top_productos': {
        'labels'        : top_productos['producto'].tolist(),
        'ingresos_netos': [round(float(v),2) for v in top_productos['ingresos_netos']],
        'unidades'      : [int(v) for v in top_productos['unidades']],
    },
    'ventas_tienda': {
        'labels'        : ventas_tienda['tienda'].tolist(),
        'ingresos_netos': [round(float(v),2) for v in ventas_tienda['ingresos_netos']],
        'num_ventas'    : [int(v) for v in ventas_tienda['num_ventas']],
    },
    'estacionalidad': {
        'anios'  : [int(a) for a in pivot.index.tolist()],
        'meses'  : meses_nombres,
        'valores': [
            [round(float(pivot.loc[anio, mes]),2) if mes in pivot.columns else 0
             for mes in range(1,13)]
            for anio in pivot.index
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 3. DEVOLUCIONES
# ════════════════════════════════════════════════════════════════════════════
print('  [3/7] Devoluciones...')

devol_kpis = query("""
    SELECT COUNT(*) AS total_devoluciones, SUM(importe_devuelto) AS importe_total,
           AVG(importe_devuelto) AS importe_medio, SUM(cantidad_devuelta) AS unidades_devueltas
    FROM dwh.fact_devoluciones
""")

devol_evolucion = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           COUNT(*) AS num_devoluciones, SUM(fd.importe_devuelto) AS importe_devuelto
    FROM dwh.fact_devoluciones fd JOIN dwh.dim_fecha df ON fd.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes ORDER BY df.anio, df.mes
""")

devol_motivos = query("""
    SELECT dm.motivo, COUNT(*) AS total
    FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_motivo_devolucion dm ON fd.motivo_sk=dm.motivo_sk
    WHERE dm.es_desconocido=FALSE
    GROUP BY dm.motivo ORDER BY total DESC
""")

devol_productos = query("""
    SELECT dp.nombre AS producto, COUNT(*) AS num_devoluciones,
           SUM(fd.importe_devuelto) AS importe_devuelto,
           SUM(fd.cantidad_devuelta) AS unidades_devueltas
    FROM dwh.fact_devoluciones fd JOIN dwh.dim_producto dp ON fd.producto_sk=dp.producto_sk
    GROUP BY dp.nombre ORDER BY num_devoluciones DESC LIMIT 10
""")

data['devoluciones'] = {
    'kpis': {
        'total_devoluciones': int(devol_kpis['total_devoluciones'].iloc[0] or 0),
        'importe_total'     : round(float(devol_kpis['importe_total'].iloc[0] or 0),2),
        'importe_medio'     : round(float(devol_kpis['importe_medio'].iloc[0] or 0),2),
        'unidades_devueltas': int(devol_kpis['unidades_devueltas'].iloc[0] or 0),
    },
    'evolucion': {
        'labels'          : devol_evolucion['label'].tolist(),
        'num_devoluciones': [int(v) for v in devol_evolucion['num_devoluciones']],
        'importe_devuelto': [round(float(v),2) for v in devol_evolucion['importe_devuelto']],
    },
    'motivos': {
        'labels' : devol_motivos['motivo'].tolist(),
        'valores': [int(v) for v in devol_motivos['total']],
    },
    'top_productos': {
        'labels'          : devol_productos['producto'].tolist(),
        'num_devoluciones': [int(v) for v in devol_productos['num_devoluciones']],
        'importe_devuelto': [round(float(v),2) for v in devol_productos['importe_devuelto']],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 4. ANÁLISIS CLIENTE — Pareto, compras por tramo, Customer 360
# ════════════════════════════════════════════════════════════════════════════
print('  [4/7] Análisis cliente...')

clientes = query("""
    SELECT cliente_sk, nombre, cltv, ingresos_netos, aov,
           frecuencia_mensual, recencia_dias, antiguedad_dias,
           return_rate, margen_pct_medio, num_ventas,
           cluster_id, cluster_label
    FROM marts.customer_360
    WHERE cltv IS NOT NULL ORDER BY cltv DESC
""")

# Curva de Pareto
clientes_sorted = clientes.sort_values('cltv', ascending=False).reset_index(drop=True)
clientes_sorted['cltv_cum_pct'] = clientes_sorted['cltv'].cumsum() / clientes_sorted['cltv'].sum() * 100
clientes_sorted['clientes_pct'] = (clientes_sorted.index+1) / len(clientes_sorted) * 100
step   = max(1, len(clientes_sorted)//100)
pareto = clientes_sorted.iloc[::step][['clientes_pct','cltv_cum_pct']]

# Distribución por número de compras
bins_ventas  = [0,1,2,5,10,9999]
labels_ventas = ['1 compra','2 compras','3–5 compras','6–10 compras','Más de 10']
clientes['tramo_ventas'] = pd.cut(
    clientes['num_ventas'], bins=bins_ventas,
    labels=labels_ventas, right=True
)
dist_ventas = clientes['tramo_ventas'].value_counts().reindex(labels_ventas).fillna(0)

# Customer 360
customer_360 = clientes[[
    'cliente_sk','nombre','cltv','ingresos_netos','aov',
    'frecuencia_mensual','recencia_dias','antiguedad_dias',
    'return_rate','margen_pct_medio','num_ventas','cluster_label'
]].copy().fillna(0)
for col in ['cltv','ingresos_netos','aov','frecuencia_mensual',
            'recencia_dias','antiguedad_dias','return_rate','margen_pct_medio']:
    customer_360[col] = customer_360[col].round(2)
customer_360['num_ventas'] = customer_360['num_ventas'].astype(int)
customer_360['cliente_sk'] = customer_360['cliente_sk'].astype(int)

data['clientes'] = {
    'pareto': {
        'clientes_pct': [round(float(v),2) for v in pareto['clientes_pct']],
        'cltv_cum_pct': [round(float(v),2) for v in pareto['cltv_cum_pct']],
    },
    'dist_ventas': {
        'labels' : labels_ventas,
        'valores': [int(v) for v in dist_ventas.values],
    },
    'customer_360': customer_360.to_dict('records'),
}


# ════════════════════════════════════════════════════════════════════════════
# 5. CLTV — análisis en profundidad
# ════════════════════════════════════════════════════════════════════════════
print('  [5/7] CLTV...')

cltv_df = clientes.copy()
cltv_vals = cltv_df['cltv'].values

# KPIs CLTV
cltv_kpis = {
    'total'  : round(float(cltv_vals.sum()), 2),
    'medio'  : round(float(cltv_vals.mean()), 2),
    'mediana': round(float(np.median(cltv_vals)), 2),
    'maximo' : round(float(cltv_vals.max()), 2),
    'minimo' : round(float(cltv_vals[cltv_vals > 0].min()) if (cltv_vals > 0).any() else 0, 2),
}

# % CLTV top 10% y top 20%
n = len(cltv_vals)
top10_idx  = max(1, int(n*0.10))
top20_idx  = max(1, int(n*0.20))
sorted_cltv = np.sort(cltv_vals)[::-1]
cltv_kpis['pct_top10'] = round(sorted_cltv[:top10_idx].sum() / cltv_vals.sum() * 100, 1)
cltv_kpis['pct_top20'] = round(sorted_cltv[:top20_idx].sum() / cltv_vals.sum() * 100, 1)

# Histograma logarítmico
cltv_pos = cltv_vals[cltv_vals > 0]
log_bins  = np.logspace(np.log10(cltv_pos.min()), np.log10(cltv_pos.max()), 20)
counts_log, edges_log = np.histogram(cltv_pos, bins=log_bins)
bin_labels_log = [f'{edges_log[i]:,.0f}–{edges_log[i+1]:,.0f}' for i in range(len(edges_log)-1)]

# CLTV por tramo de antigüedad
cltv_df['tramo_ant'] = pd.cut(
    cltv_df['antiguedad_dias'],
    bins=[0, 365, 730, 1095, 99999],
    labels=['0–1 año','1–2 años','2–3 años','3+ años']
)
cltv_ant = cltv_df.groupby('tramo_ant', observed=True)['cltv'].agg(['mean','median','count']).reset_index()
cltv_ant.columns = ['tramo','cltv_medio','cltv_mediana','n_clientes']

# Scatter CLTV vs Antigüedad (muestra 600 pts)
sample_ant = cltv_df[['cltv','antiguedad_dias','cluster_label']].sample(
    min(600, len(cltv_df)), random_state=42)
scatter_ant = [
    {'x': round(float(r['antiguedad_dias']),0),
     'y': round(float(r['cltv']),2),
     'c': r['cluster_label']}
    for _, r in sample_ant.iterrows()
]

# Scatter CLTV vs Recencia (muestra 600 pts)
sample_rec = cltv_df[['cltv','recencia_dias','cluster_label']].sample(
    min(600, len(cltv_df)), random_state=43)
scatter_rec = [
    {'x': round(float(r['recencia_dias']),0),
     'y': round(float(r['cltv']),2),
     'c': r['cluster_label']}
    for _, r in sample_rec.iterrows()
]

# Cohorte por año de primera compra
cohorte = query("""
    SELECT
        EXTRACT(YEAR FROM primera_compra)::int AS anio,
        ROUND(AVG(cltv)::numeric, 2) AS cltv_medio,
        COUNT(*) AS n_clientes
    FROM marts.customer_360
    WHERE cltv IS NOT NULL AND primera_compra IS NOT NULL
    GROUP BY EXTRACT(YEAR FROM primera_compra)
    ORDER BY anio
""")

# RFM matrix — terciles R, F, M → heatmap 3x3 promedio CLTV
cltv_df['R'] = pd.qcut(cltv_df['recencia_dias'],    q=3, labels=['Reciente','Medio','Inactivo'])
cltv_df['F'] = pd.qcut(cltv_df['frecuencia_mensual'].rank(method='first'), q=3, labels=['Baja','Media','Alta'])
rfm = cltv_df.groupby(['R','F'], observed=True)['cltv'].mean().reset_index()
rfm.columns = ['recencia','frecuencia','cltv_medio']
rfm['cltv_medio'] = rfm['cltv_medio'].round(2)

# Top 20 clientes
top20 = cltv_df.nlargest(20, 'cltv')[[
    'nombre','cltv','ingresos_netos','aov',
    'frecuencia_mensual','recencia_dias','num_ventas','cluster_label'
]].copy()
for col in ['cltv','ingresos_netos','aov','frecuencia_mensual','recencia_dias']:
    top20[col] = top20[col].round(2)
top20['num_ventas'] = top20['num_ventas'].astype(int)

data['cltv'] = {
    'kpis': cltv_kpis,
    'histograma_log': {
        'labels' : bin_labels_log,
        'valores': counts_log.tolist(),
    },
    'por_antiguedad': {
        'labels'     : cltv_ant['tramo'].tolist(),
        'cltv_medio' : [round(float(v),2) for v in cltv_ant['cltv_medio']],
        'cltv_mediana': [round(float(v),2) for v in cltv_ant['cltv_mediana']],
        'n_clientes' : [int(v) for v in cltv_ant['n_clientes']],
    },
    'scatter_antiguedad': scatter_ant,
    'scatter_recencia'  : scatter_rec,
    'cohorte': {
        'labels'     : cohorte['anio'].tolist(),
        'cltv_medio' : [float(v) for v in cohorte['cltv_medio']],
        'n_clientes' : [int(v) for v in cohorte['n_clientes']],
    },
    'rfm': {
        'data': rfm.to_dict('records'),
        'r_labels': ['Reciente','Medio','Inactivo'],
        'f_labels': ['Baja','Media','Alta'],
    },
    'top20': top20.to_dict('records'),
}


# ════════════════════════════════════════════════════════════════════════════
# 6. CLUSTERING — PCA + K-Means + scatter AOV vs Frecuencia
# ════════════════════════════════════════════════════════════════════════════
print('  [6/7] Clustering...')

df_cl = query("""
    SELECT cliente_sk, cluster_id, cluster_label,
           cltv, ingresos_netos, aov,
           frecuencia_mensual, recencia_dias,
           return_rate, antiguedad_dias,
           num_ventas, margen_pct_medio
    FROM marts.customer_360
    WHERE cltv IS NOT NULL ORDER BY cliente_sk
""")
df_cl[FEATURES] = df_cl[FEATURES].fillna(0)

X        = df_cl[FEATURES].values
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X)
pca      = PCA(n_components=2, random_state=42)
X_pca    = pca.fit_transform(X_scaled)
df_cl['pc1'] = X_pca[:,0]
df_cl['pc2'] = X_pca[:,1]

var_exp        = pca.explained_variance_ratio_ * 100
ORDEN_CLUSTERS = ['Champions','Base','Churned']
dist_cluster   = df_cl['cluster_label'].value_counts().reindex(ORDEN_CLUSTERS).fillna(0)
perfil         = df_cl.groupby('cluster_label')[FEATURES].mean().reindex(ORDEN_CLUSTERS)
perfil_norm    = (perfil - perfil.min()) / (perfil.max() - perfil.min() + 1e-9)

FEATURES_LABELS = ['CLTV','Ingresos netos','AOV','Frecuencia','Recencia','Return Rate','Antigüedad']

# Scatter PCA
scatter_pts = []
for label in ORDEN_CLUSTERS:
    sub = df_cl[df_cl['cluster_label']==label][['pc1','pc2']].copy()
    if len(sub) > 800: sub = sub.sample(800, random_state=42)
    for _, row in sub.iterrows():
        scatter_pts.append({'x':round(float(row['pc1']),4),'y':round(float(row['pc2']),4),'cluster':label})

FEATURES_EXT = FEATURES + ['num_ventas', 'margen_pct_medio']
perfil_ext = df_cl.groupby('cluster_label')[FEATURES_EXT].mean().reindex(ORDEN_CLUSTERS)
total_cltv_cl = df_cl['cltv'].sum()

data['clustering'] = {
    'varianza_explicada': {
        'pc1'  : round(float(var_exp[0]),1),
        'pc2'  : round(float(var_exp[1]),1),
        'total': round(float(var_exp.sum()),1),
    },
    'distribucion': {
        'labels'   : ORDEN_CLUSTERS,
        'valores'  : [int(dist_cluster[c]) for c in ORDEN_CLUSTERS],
        'pct'      : [round(int(dist_cluster[c])/len(df_cl)*100,1) for c in ORDEN_CLUSTERS],
        'pct_cltv' : [round(float(df_cl[df_cl['cluster_label']==c]['cltv'].sum())/total_cltv_cl*100,1) for c in ORDEN_CLUSTERS],
    },
    'perfil_normalizado': {
        'features': FEATURES_LABELS,
        'clusters': {
            label: [round(float(perfil_norm.loc[label,f]),3) for f in FEATURES]
            for label in ORDEN_CLUSTERS
        },
    },
    'scatter'   : scatter_pts,
    'perfil_medio': {
        label: {f: round(float(perfil_ext.loc[label,f]),2) for f in FEATURES_EXT}
        for label in ORDEN_CLUSTERS
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 7. RESUMEN EJECUTIVO — calculado en JS desde los datos anteriores
#    (no necesita queries adicionales — se genera en el HTML)
# ════════════════════════════════════════════════════════════════════════════
print('  [7/7] Resumen ejecutivo (sin queries adicionales)...')
# El resumen ejecutivo se construye en el frontend desde window.DASHBOARD_DATA




# ════════════════════════════════════════════════════════════════════════════
# 7. PRODUCTOS
# ════════════════════════════════════════════════════════════════════════════
print('  [7/10] Productos...')

prod_top = query("""
    SELECT dp.nombre AS producto, dp.categoria, dp.marca,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    GROUP BY dp.nombre, dp.categoria, dp.marca
    ORDER BY ingresos_netos DESC LIMIT 15
""")

prod_margen = query("""
    SELECT dp.nombre AS producto,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           SUM(fv.cantidad) AS unidades
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    GROUP BY dp.nombre
    HAVING SUM(fv.subtotal_neto) > 0
    ORDER BY margen_medio DESC LIMIT 15
""")

prod_devol = query("""
    SELECT dp.nombre AS producto,
           COUNT(fd.*) AS num_devoluciones,
           SUM(fv_tot.subtotal_neto) AS ingresos_netos,
           ROUND(COUNT(fd.*)::numeric / NULLIF(COUNT(DISTINCT fv_tot.sale_id),0)*100,1) AS tasa_devol
    FROM dwh.dim_producto dp
    JOIN dwh.fact_ventas fv_tot ON dp.producto_sk=fv_tot.producto_sk
    LEFT JOIN dwh.fact_devoluciones fd ON dp.producto_sk=fd.producto_sk
    GROUP BY dp.nombre
    ORDER BY num_devoluciones DESC LIMIT 12
""")

# Estacionalidad top 5 productos
top5_prod = prod_top['producto'].head(5).tolist()
prod_estac = query(f"""
    SELECT dp.nombre AS producto, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon') AS mes_nombre,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    WHERE dp.nombre IN ({','.join(["'"+p.replace("'","''")+"'" for p in top5_prod])})
    GROUP BY dp.nombre, df.mes
    ORDER BY df.mes
""")
estac_pivot = prod_estac.pivot(index='producto', columns='mes', values='ingresos_netos').fillna(0)
meses_cortos = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

data['productos'] = {
    'top_ingresos': {
        'labels'      : prod_top['producto'].tolist(),
        'ingresos'    : [round(float(v),2) for v in prod_top['ingresos_netos']],
        'unidades'    : [int(v) for v in prod_top['unidades']],
        'margen'      : [float(v) for v in prod_top['margen_medio']],
        'categoria'   : prod_top['categoria'].tolist(),
        'marca'       : prod_top['marca'].tolist(),
    },
    'top_margen': {
        'labels'   : prod_margen['producto'].tolist(),
        'margen'   : [float(v) for v in prod_margen['margen_medio']],
        'ingresos' : [round(float(v),2) for v in prod_margen['ingresos_netos']],
    },
    'devol_vs_ingresos': {
        'labels'      : prod_devol['producto'].tolist(),
        'devoluciones': [int(v) for v in prod_devol['num_devoluciones']],
        'ingresos'    : [round(float(v),2) for v in prod_devol['ingresos_netos']],
        'tasa'        : [float(v) if v else 0 for v in prod_devol['tasa_devol']],
    },
    'estacionalidad': {
        'productos': top5_prod,
        'meses'    : meses_cortos,
        'valores'  : {
            p: [round(float(estac_pivot.loc[p, m]),2) if p in estac_pivot.index and m in estac_pivot.columns else 0
                for m in range(1,13)]
            for p in top5_prod if p in estac_pivot.index
        },
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 8. MARCAS & CATEGORÍAS
# ════════════════════════════════════════════════════════════════════════════
print('  [8/10] Marcas & Categorías...')

marcas = query("""
    SELECT dp.marca,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio,
           COUNT(DISTINCT fv.sale_id) AS num_ventas,
           COUNT(DISTINCT dp.producto_sk) AS num_productos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    WHERE dp.marca IS NOT NULL AND dp.marca != ''
    GROUP BY dp.marca
    ORDER BY ingresos_netos DESC LIMIT 12
""")

marcas_devol = query("""
    SELECT dp.marca,
           COUNT(fd.*) AS num_devoluciones,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio
    FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_producto dp ON fd.producto_sk=dp.producto_sk
    JOIN dwh.fact_ventas fv ON dp.producto_sk=fv.producto_sk
    WHERE dp.marca IS NOT NULL AND dp.marca != ''
    GROUP BY dp.marca
    ORDER BY num_devoluciones DESC LIMIT 12
""")

categorias = query("""
    SELECT dp.categoria,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio,
           COUNT(DISTINCT fv.sale_id) AS num_ventas,
           COUNT(DISTINCT dp.producto_sk) AS num_productos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    WHERE dp.categoria IS NOT NULL AND dp.categoria != ''
    GROUP BY dp.categoria
    ORDER BY ingresos_netos DESC
""")

cat_evol = query("""
    SELECT dp.categoria,
           df.anio,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    WHERE dp.categoria IS NOT NULL AND dp.categoria != ''
    GROUP BY dp.categoria, df.anio
    ORDER BY dp.categoria, df.anio
""")
top_cats = categorias['categoria'].head(6).tolist()
cat_evol_pivot = cat_evol[cat_evol['categoria'].isin(top_cats)].pivot(
    index='categoria', columns='anio', values='ingresos_netos').fillna(0)
anios_uniq = sorted(cat_evol['anio'].unique().tolist())

data['marcas_categorias'] = {
    'marcas': {
        'labels'       : marcas['marca'].tolist(),
        'ingresos'     : [round(float(v),2) for v in marcas['ingresos_netos']],
        'margen'       : [float(v) for v in marcas['margen_medio']],
        'num_productos': [int(v) for v in marcas['num_productos']],
        'num_ventas'   : [int(v) for v in marcas['num_ventas']],
    },
    'marcas_devol': {
        'labels'      : marcas_devol['marca'].tolist(),
        'devoluciones': [int(v) for v in marcas_devol['num_devoluciones']],
    },
    'categorias': {
        'labels'       : categorias['categoria'].tolist(),
        'ingresos'     : [round(float(v),2) for v in categorias['ingresos_netos']],
        'margen'       : [float(v) for v in categorias['margen_medio']],
        'num_productos': [int(v) for v in categorias['num_productos']],
    },
    'cat_evol': {
        'categorias': top_cats,
        'anios'     : [int(a) for a in anios_uniq],
        'valores'   : {
            c: [round(float(cat_evol_pivot.loc[c, a]),2) if c in cat_evol_pivot.index and a in cat_evol_pivot.columns else 0
                for a in anios_uniq]
            for c in top_cats if c in cat_evol_pivot.index
        },
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 9. RENTABILIDAD
# ════════════════════════════════════════════════════════════════════════════
print('  [9/10] Rentabilidad...')

rent_evol = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto)  AS ingresos_netos,
           SUM(fv.subtotal_bruto) AS ingresos_brutos,
           SUM(fv.coste_total)    AS coste_total,
           SUM(fv.margen_bruto)   AS margen_bruto,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_pct
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes
    ORDER BY df.anio, df.mes
""")

rent_cat = query("""
    SELECT dp.categoria,
           SUM(fv.subtotal_neto)  AS ingresos_netos,
           SUM(fv.coste_total)    AS coste_total,
           SUM(fv.margen_bruto)   AS margen_bruto,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_pct
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    WHERE dp.categoria IS NOT NULL AND dp.categoria != ''
    GROUP BY dp.categoria
    ORDER BY margen_pct DESC
""")

prod_margen_bajo = query("""
    SELECT dp.nombre AS producto, dp.categoria,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_pct,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           SUM(fv.cantidad) AS unidades
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    GROUP BY dp.nombre, dp.categoria
    HAVING SUM(fv.subtotal_neto) > 0
    ORDER BY margen_pct ASC LIMIT 10
""")

rent_anual = query("""
    SELECT df.anio,
           SUM(fv.subtotal_neto)  AS ingresos_netos,
           SUM(fv.coste_total)    AS coste_total,
           SUM(fv.margen_bruto)   AS margen_bruto,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_pct
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio
    ORDER BY df.anio
""")

data['rentabilidad'] = {
    'evolucion': {
        'labels'        : rent_evol['label'].tolist(),
        'ingresos_netos': [round(float(v),2) for v in rent_evol['ingresos_netos']],
        'coste_total'   : [round(float(v),2) for v in rent_evol['coste_total']],
        'margen_bruto'  : [round(float(v),2) for v in rent_evol['margen_bruto']],
        'margen_pct'    : [float(v) for v in rent_evol['margen_pct']],
    },
    'por_categoria': {
        'labels'       : rent_cat['categoria'].tolist(),
        'ingresos'     : [round(float(v),2) for v in rent_cat['ingresos_netos']],
        'margen_bruto' : [round(float(v),2) for v in rent_cat['margen_bruto']],
        'margen_pct'   : [float(v) for v in rent_cat['margen_pct']],
    },
    'prod_margen_bajo': {
        'labels'   : prod_margen_bajo['producto'].tolist(),
        'margen'   : [float(v) for v in prod_margen_bajo['margen_pct']],
        'ingresos' : [round(float(v),2) for v in prod_margen_bajo['ingresos_netos']],
        'categoria': prod_margen_bajo['categoria'].tolist(),
    },
    'anual': {
        'labels'        : [int(a) for a in rent_anual['anio']],
        'ingresos_netos': [round(float(v),2) for v in rent_anual['ingresos_netos']],
        'coste_total'   : [round(float(v),2) for v in rent_anual['coste_total']],
        'margen_pct'    : [float(v) for v in rent_anual['margen_pct']],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# 10. TIENDAS
# ════════════════════════════════════════════════════════════════════════════
print('  [10/10] Tiendas...')

tiendas_kpis = query("""
    SELECT dt.nombre AS tienda,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           COUNT(DISTINCT fv.sale_id) AS num_ventas,
           ROUND(AVG(fv.precio_unitario)::numeric,2) AS aov,
           ROUND(AVG(fv.margen_pct)::numeric,2)      AS margen_pct,
           SUM(fv.cantidad_devuelta)::float / NULLIF(SUM(fv.cantidad),0)*100 AS return_rate
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_tienda dt ON fv.tienda_sk=dt.tienda_sk
    WHERE dt.tienda_sk != 1
    GROUP BY dt.nombre
    ORDER BY ingresos_netos DESC
""")

tiendas_evol = query("""
    SELECT dt.nombre AS tienda, df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_tienda dt ON fv.tienda_sk=dt.tienda_sk
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    WHERE dt.tienda_sk != 1
    GROUP BY dt.nombre, df.anio, df.mes
    ORDER BY df.anio, df.mes
""")

tiendas_top_prod = query("""
    SELECT dt.nombre AS tienda, dp.nombre AS producto,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           RANK() OVER (PARTITION BY dt.tienda_sk ORDER BY SUM(fv.subtotal_neto) DESC) AS rk
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_tienda dt ON fv.tienda_sk=dt.tienda_sk
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    WHERE dt.tienda_sk != 1
    GROUP BY dt.nombre, dt.tienda_sk, dp.nombre
    QUALIFY rk <= 3
""" if False else """
    SELECT sub.tienda, sub.producto, sub.ingresos_netos FROM (
        SELECT dt.nombre AS tienda, dp.nombre AS producto,
               SUM(fv.subtotal_neto) AS ingresos_netos,
               ROW_NUMBER() OVER (PARTITION BY dt.tienda_sk ORDER BY SUM(fv.subtotal_neto) DESC) AS rk
        FROM dwh.fact_ventas fv
        JOIN dwh.dim_tienda dt ON fv.tienda_sk=dt.tienda_sk
        JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
        WHERE dt.tienda_sk != 1
        GROUP BY dt.nombre, dt.tienda_sk, dp.nombre
    ) sub WHERE sub.rk <= 3
    ORDER BY sub.tienda, sub.ingresos_netos DESC
""")

# Evolución por tienda — pivot
tiendas_lista = tiendas_kpis['tienda'].tolist()
labels_evol   = sorted(tiendas_evol[['anio','mes','label']].drop_duplicates().sort_values(['anio','mes'])['label'].tolist())
evol_dict = {}
for tienda in tiendas_lista:
    sub = tiendas_evol[tiendas_evol['tienda']==tienda].set_index('label')['ingresos_netos']
    evol_dict[tienda] = [round(float(sub.get(l, 0)),2) for l in labels_evol]

# Top productos por tienda
top_prod_tienda = {}
for tienda in tiendas_lista:
    sub = tiendas_top_prod[tiendas_top_prod['tienda']==tienda]
    top_prod_tienda[tienda] = [
        {'producto': r['producto'], 'ingresos': round(float(r['ingresos_netos']),2)}
        for _, r in sub.iterrows()
    ]

data['tiendas'] = {
    'kpis': {
        'labels'      : tiendas_kpis['tienda'].tolist(),
        'ingresos'    : [round(float(v),2) for v in tiendas_kpis['ingresos_netos']],
        'num_ventas'  : [int(v) for v in tiendas_kpis['num_ventas']],
        'aov'         : [float(v) for v in tiendas_kpis['aov']],
        'margen_pct'  : [float(v) for v in tiendas_kpis['margen_pct']],
        'return_rate' : [round(float(v),2) if v else 0 for v in tiendas_kpis['return_rate']],
    },
    'evolucion': {
        'labels'  : labels_evol,
        'tiendas' : evol_dict,
    },
    'top_productos': top_prod_tienda,
}


# ════════════════════════════════════════════════════════════════════════════
# 11. TENDENCIAS
# ════════════════════════════════════════════════════════════════════════════
print('  [11/10] Tendencias...')

# YoY por mes
yoy = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon') AS mes_nombre,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes
    ORDER BY df.anio, df.mes
""")
yoy_pivot = yoy.pivot(index='mes', columns='anio', values='ingresos_netos').fillna(0)
anios_yoy = sorted(yoy['anio'].unique().tolist())

# Crecimiento anual total
crec_anual = query("""
    SELECT df.anio,
           SUM(fv.subtotal_neto) AS ingresos_netos,
           COUNT(DISTINCT fv.sale_id) AS num_ventas,
           COUNT(DISTINCT fv.cliente_sk) AS clientes_activos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio ORDER BY df.anio
""")

# Mejores y peores meses históricos
best_months = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'TMMonth')||' '||df.anio AS label,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes
    ORDER BY ingresos_netos DESC LIMIT 10
""")

worst_months = query("""
    SELECT df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'TMMonth')||' '||df.anio AS label,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    GROUP BY df.anio, df.mes
    ORDER BY ingresos_netos ASC LIMIT 10
""")

# Productos con más crecimiento (último año vs anterior)
prod_crec = query("""
    WITH anios AS (
        SELECT MAX(anio) AS ultimo, MAX(anio)-1 AS anterior
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    ),
    base AS (
        SELECT dp.nombre AS producto,
               SUM(CASE WHEN df.anio=a.anterior THEN fv.subtotal_neto ELSE 0 END) AS ing_ant,
               SUM(CASE WHEN df.anio=a.ultimo   THEN fv.subtotal_neto ELSE 0 END) AS ing_act
        FROM dwh.fact_ventas fv
        JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
        JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
        CROSS JOIN anios a
        GROUP BY dp.nombre
    )
    SELECT producto,
           ROUND(ing_ant::numeric,2) AS ing_ant,
           ROUND(ing_act::numeric,2) AS ing_act,
           ROUND((ing_act-ing_ant)/NULLIF(ing_ant,0)*100,1) AS crecimiento_pct
    FROM base
    WHERE ing_ant > 0 AND ing_act > 0
    ORDER BY crecimiento_pct DESC LIMIT 10
""")

prod_decr = query("""
    WITH anios AS (
        SELECT MAX(anio) AS ultimo, MAX(anio)-1 AS anterior
        FROM dwh.dim_fecha df JOIN dwh.fact_ventas fv ON df.fecha_sk=fv.fecha_sk
    ),
    base AS (
        SELECT dp.nombre AS producto,
               SUM(CASE WHEN df.anio=a.anterior THEN fv.subtotal_neto ELSE 0 END) AS ing_ant,
               SUM(CASE WHEN df.anio=a.ultimo   THEN fv.subtotal_neto ELSE 0 END) AS ing_act
        FROM dwh.fact_ventas fv
        JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
        JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
        CROSS JOIN anios a
        GROUP BY dp.nombre
    )
    SELECT producto,
           ROUND(ing_ant::numeric,2) AS ing_ant,
           ROUND(ing_act::numeric,2) AS ing_act,
           ROUND((ing_act-ing_ant)/NULLIF(ing_ant,0)*100,1) AS crecimiento_pct
    FROM base
    WHERE ing_ant > 0 AND ing_act > 0
    ORDER BY crecimiento_pct ASC LIMIT 10
""")

data['tendencias'] = {
    'yoy': {
        'meses' : meses_cortos,
        'anios' : [int(a) for a in anios_yoy],
        'valores': {
            str(a): [round(float(yoy_pivot.loc[m, a]),2) if m in yoy_pivot.index and a in yoy_pivot.columns else 0
                     for m in range(1,13)]
            for a in anios_yoy
        },
    },
    'crecimiento_anual': {
        'labels'          : [int(a) for a in crec_anual['anio']],
        'ingresos_netos'  : [round(float(v),2) for v in crec_anual['ingresos_netos']],
        'num_ventas'      : [int(v) for v in crec_anual['num_ventas']],
        'clientes_activos': [int(v) for v in crec_anual['clientes_activos']],
    },
    'mejores_meses': {
        'labels'  : best_months['label'].tolist(),
        'ingresos': [round(float(v),2) for v in best_months['ingresos_netos']],
    },
    'peores_meses': {
        'labels'  : worst_months['label'].tolist(),
        'ingresos': [round(float(v),2) for v in worst_months['ingresos_netos']],
    },
    'prod_crecimiento': {
        'labels'    : prod_crec['producto'].tolist(),
        'pct'       : [float(v) for v in prod_crec['crecimiento_pct']],
        'ing_ant'   : [round(float(v),2) for v in prod_crec['ing_ant']],
        'ing_act'   : [round(float(v),2) for v in prod_crec['ing_act']],
    },
    'prod_decrecimiento': {
        'labels'    : prod_decr['producto'].tolist(),
        'pct'       : [float(v) for v in prod_decr['crecimiento_pct']],
        'ing_ant'   : [round(float(v),2) for v in prod_decr['ing_ant']],
        'ing_act'   : [round(float(v),2) for v in prod_decr['ing_act']],
    },
}




# ════════════════════════════════════════════════════════════════════════════
# Datos de evolución mensual por producto y por marca (para selectores)
# ════════════════════════════════════════════════════════════════════════════
print('  [Extra] Evolución por producto y marca...')

# KPIs y evolución mensual — todos los productos del top 15
all_prods = prod_top['producto'].tolist()
prod_evol_raw = query(f"""
    SELECT dp.nombre AS producto,
           df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    WHERE dp.nombre IN ({','.join(["'"+p.replace("'","''")+"'" for p in all_prods])})
    GROUP BY dp.nombre, df.anio, df.mes
    ORDER BY dp.nombre, df.anio, df.mes
""")

# Devoluciones por producto
prod_devol_kpis = query(f"""
    SELECT dp.nombre AS producto, COUNT(*) AS num_devoluciones,
           SUM(fd.importe_devuelto) AS importe_devuelto
    FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_producto dp ON fd.producto_sk=dp.producto_sk
    WHERE dp.nombre IN ({','.join(["'"+p.replace("'","''")+"'" for p in all_prods])})
    GROUP BY dp.nombre
""")
devol_dict_prod = {r['producto']:{'n':int(r['num_devoluciones']),'imp':round(float(r['importe_devuelto']),2)}
                   for _,r in prod_devol_kpis.iterrows()}

evol_labels_prod = sorted(prod_evol_raw[['anio','mes','label']].drop_duplicates()
                          .sort_values(['anio','mes'])['label'].tolist())

prod_selector = {}
for prod in all_prods:
    sub = prod_evol_raw[prod_evol_raw['producto']==prod]
    top_row = prod_top[prod_top['producto']==prod].iloc[0] if len(prod_top[prod_top['producto']==prod]) else None
    evol_map = sub.set_index('label')['ingresos_netos']
    prod_selector[prod] = {
        'ingresos'      : round(float(top_row['ingresos_netos']),2) if top_row is not None else 0,
        'unidades'      : int(top_row['unidades']) if top_row is not None else 0,
        'margen'        : float(top_row['margen_medio']) if top_row is not None else 0,
        'categoria'     : str(top_row['categoria']) if top_row is not None else '',
        'marca'         : str(top_row['marca']) if top_row is not None else '',
        'num_ventas'    : int(top_row['num_ventas']) if top_row is not None else 0,
        'devoluciones'  : devol_dict_prod.get(prod, {}).get('n', 0),
        'evolucion'     : [round(float(evol_map.get(l, 0)),2) for l in evol_labels_prod],
    }

data['productos']['selector']      = prod_selector
data['productos']['evol_labels']   = evol_labels_prod

# KPIs y evolución mensual — todas las marcas
all_marcas = marcas['marca'].tolist()
marca_evol_raw = query(f"""
    SELECT dp.marca,
           df.anio, df.mes,
           TO_CHAR(TO_DATE(df.mes::text,'MM'),'Mon')||' '||df.anio AS label,
           SUM(fv.subtotal_neto)   AS ingresos_netos,
           SUM(fv.cantidad)        AS unidades,
           ROUND(AVG(fv.margen_pct)::numeric,2) AS margen_medio,
           COUNT(DISTINCT fv.sale_id) AS num_ventas
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    JOIN dwh.dim_fecha df ON fv.fecha_sk=df.fecha_sk
    WHERE dp.marca IN ({','.join(["'"+m.replace("'","''")+"'" for m in all_marcas])})
    GROUP BY dp.marca, df.anio, df.mes
    ORDER BY dp.marca, df.anio, df.mes
""")

marca_devol_kpis = query(f"""
    SELECT dp.marca, COUNT(*) AS num_devoluciones
    FROM dwh.fact_devoluciones fd
    JOIN dwh.dim_producto dp ON fd.producto_sk=dp.producto_sk
    WHERE dp.marca IN ({','.join(["'"+m.replace("'","''")+"'" for m in all_marcas])})
    GROUP BY dp.marca
""")
devol_dict_marca = {r['marca']:int(r['num_devoluciones']) for _,r in marca_devol_kpis.iterrows()}

evol_labels_marca = sorted(marca_evol_raw[['anio','mes','label']].drop_duplicates()
                            .sort_values(['anio','mes'])['label'].tolist())

marca_selector = {}
for m_name in all_marcas:
    sub  = marca_evol_raw[marca_evol_raw['marca']==m_name]
    mrow = marcas[marcas['marca']==m_name].iloc[0] if len(marcas[marcas['marca']==m_name]) else None
    evol_map = sub.set_index('label')['ingresos_netos']
    marca_selector[m_name] = {
        'ingresos'    : round(float(mrow['ingresos_netos']),2) if mrow is not None else 0,
        'unidades'    : int(mrow['unidades']) if mrow is not None else 0,
        'margen'      : float(mrow['margen_medio']) if mrow is not None else 0,
        'num_ventas'  : int(mrow['num_ventas']) if mrow is not None else 0,
        'num_productos': int(mrow['num_productos']) if mrow is not None else 0,
        'devoluciones': devol_dict_marca.get(m_name, 0),
        'evolucion'   : [round(float(evol_map.get(l, 0)),2) for l in evol_labels_marca],
    }

data['marcas_categorias']['selector']    = marca_selector
data['marcas_categorias']['evol_labels'] = evol_labels_marca

# Distribución de categorías por marca (para donut filtrado)
cat_x_marca_raw = query(f"""
    SELECT dp.marca, dp.categoria,
           SUM(fv.subtotal_neto) AS ingresos_netos
    FROM dwh.fact_ventas fv
    JOIN dwh.dim_producto dp ON fv.producto_sk=dp.producto_sk
    WHERE dp.marca IN ({','.join(["'"+m.replace("'","''")+"'" for m in all_marcas])})
      AND dp.categoria IS NOT NULL AND dp.categoria != ''
    GROUP BY dp.marca, dp.categoria
    ORDER BY dp.marca, ingresos_netos DESC
""")
cat_x_marca = {}
for m_name in all_marcas:
    sub = cat_x_marca_raw[cat_x_marca_raw['marca']==m_name]
    cat_x_marca[m_name] = {
        'labels' : sub['categoria'].tolist(),
        'valores': [round(float(v),2) for v in sub['ingresos_netos']],
    }
data['marcas_categorias']['cat_x_marca'] = cat_x_marca


# ════════════════════════════════════════════════════════════════════════════
# Guardar JSON + JS
# ════════════════════════════════════════════════════════════════════════════
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write('window.DASHBOARD_DATA = ')
    json.dump(data, f, ensure_ascii=False, separators=(',',':'), default=str)
    f.write(';')

size_json = OUTPUT_PATH.stat().st_size / 1024
size_js   = JS_PATH.stat().st_size / 1024
print(f'\nJSON : {OUTPUT_PATH} ({size_json:.1f} KB)')
print(f'JS   : {JS_PATH} ({size_js:.1f} KB)')
print(f'\nSecciones exportadas:')
for k in data: print(f'  OK  {k}')
print('\nListo.')