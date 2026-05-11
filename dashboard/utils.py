"""
utils.py — Funciones compartidas del dashboard saleshealth
Conexion BD, carga de datos (cached), CSS, constantes, helpers.
"""

import pandas as pd
import numpy as np
import streamlit as st
from sqlalchemy import create_engine, text
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# ── Paleta y constantes ───────────────────────────────────────────────────────
PALETA = {
    'primary'  : '#2C6FBF',
    'secondary': '#27A06B',
    'warning'  : '#E07B2A',
    'danger'   : '#E57373',
    'neutral'  : '#90A4AE',
    'light'    : '#F8F9FA',
    'border'   : '#E9ECEF',
    'text'     : '#1A1A1A',
    'muted'    : '#6C757D',
}

COLORES_CLUSTER = {
    'Champions': '#2C6FBF',
    'Base'     : '#E07B2A',
    'Churned'  : '#E57373',
}

ORDEN_CLUSTERS = ['Champions', 'Base', 'Churned']

FEATURES = [
    'cltv', 'ingresos_netos', 'aov',
    'frecuencia_mensual', 'recencia_dias',
    'return_rate', 'antiguedad_dias'
]

CLUSTER_LABELS = {0: 'Champions', 1: 'Base', 2: 'Churned'}

DB_URL = 'postgresql+psycopg2://postgres:pimpum.postgre@localhost:5432/saleshealth'


# ── Conexion BD ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)


# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_customer_360():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(
            text("SELECT * FROM marts.customer_360 WHERE cltv IS NOT NULL ORDER BY cltv DESC"),
            conn
        )


@st.cache_data(ttl=3600)
def load_zona_data():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text("""
            SELECT fv.cliente_sk, dz.tipo_area, dz.orientacion, COUNT(*) AS num_lineas
            FROM dwh.fact_ventas fv
            JOIN dwh.dim_zona dz ON fv.zona_sk = dz.zona_sk
            WHERE dz.es_desconocida = FALSE
            GROUP BY fv.cliente_sk, dz.tipo_area, dz.orientacion
        """), conn)


# ── PCA (mismos parametros que ETL) ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_pca_data(_df):
    """Recalcula PCA + K-Means con los mismos parametros que etl/clusters.py."""
    df_ml = _df[['cliente_sk', 'nombre'] + FEATURES].copy()
    df_ml[FEATURES] = df_ml[FEATURES].fillna(0)
    X = df_ml[FEATURES].values

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca   = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    kmeans     = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels_raw = kmeans.fit_predict(X_pca)

    df_ml['cluster_raw'] = labels_raw
    cltv_rank = df_ml.groupby('cluster_raw')['cltv'].mean().sort_values(ascending=False)
    rank_map  = {c: r for r, c in enumerate(cltv_rank.index)}
    df_ml['cluster_label'] = df_ml['cluster_raw'].map(rank_map).map(CLUSTER_LABELS)
    df_ml['pc1'] = X_pca[:, 0]
    df_ml['pc2'] = X_pca[:, 1]

    return (
        df_ml[['cliente_sk', 'nombre', 'pc1', 'pc2', 'cluster_label']],
        pca.explained_variance_ratio_
    )


# ── Zona predominante por cliente ─────────────────────────────────────────────
def get_zona_predominante(df, df_zona):
    zona_pred = (
        df_zona
        .sort_values('num_lineas', ascending=False)
        .drop_duplicates('cliente_sk')
        [['cliente_sk', 'tipo_area', 'orientacion']]
    )
    return df.merge(zona_pred, on='cliente_sk', how='left')


# ── Datos de negocio para página 4 ───────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_ventas_negocio():
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text("""
            SELECT
                df2.anio,
                df2.mes,
                fv.cliente_sk,
                fv.producto_sk,
                dp.nombre AS nombre_producto,
                dp.categoria,
                fv.cantidad,
                fv.subtotal_bruto,
                fv.subtotal_neto,
                fv.coste_total,
                fv.margen_bruto,
                fv.cantidad_devuelta
            FROM dwh.fact_ventas fv
            JOIN dwh.dim_fecha df2 ON fv.fecha_sk = df2.fecha_sk
            JOIN dwh.dim_producto dp ON fv.producto_sk = dp.producto_sk
            WHERE fv.cliente_sk > 0
        """), conn)


# ── Coeficiente de Gini ───────────────────────────────────────────────────────
def calcular_gini(series):
    vals = np.sort(series.values)
    n    = len(vals)
    idx2 = np.arange(1, n + 1)
    return round(float((2 * np.sum(idx2 * vals)) / (n * vals.sum()) - (n + 1) / n), 3)



# ── Health score ──────────────────────────────────────────────────────────────
def calcular_health_score(df):
    n = len(df)
    champions_pct  = len(df[df['cluster_label'] == 'Champions']) / n * 100
    rr_global      = df['unidades_devueltas'].sum() / df['unidades_compradas'].sum() * 100
    cltv_pos_pct   = len(df[df['cltv'] > 0]) / n * 100

    s1 = min(champions_pct / 15 * 33, 33)       # Champions (target >15%)
    s2 = max(0, (5 - rr_global) / 5 * 33)       # Return Rate (target <5%)
    s3 = min(cltv_pos_pct / 95 * 34, 34)        # Clientes con CLTV positivo

    return round(s1 + s2 + s3), round(champions_pct, 1), round(rr_global, 2)


# ── Lorenz ────────────────────────────────────────────────────────────────────
def get_lorenz(series):
    vals = np.sort(series.values)
    cum  = np.cumsum(vals) / vals.sum()
    pop  = np.arange(1, len(vals) + 1) / len(vals)
    return pop * 100, cum * 100


# ── Percentil de un cliente ───────────────────────────────────────────────────
def get_percentil(df, cliente_sk, col='cltv'):
    val = df.loc[df['cliente_sk'] == cliente_sk, col].values[0]
    pct = (df[col] < val).mean() * 100
    return round(pct, 1), val


# ── Top 20 con sparklines HTML ────────────────────────────────────────────────
def render_top_table(df, n=20):
    top      = df.head(n).copy()
    max_cltv = top['cltv'].max()

    rows = ""
    for _, row in top.iterrows():
        pct   = row['cltv'] / max_cltv * 100
        color = COLORES_CLUSTER.get(row.get('cluster_label', ''), PALETA['neutral'])
        rows += f"""
        <tr>
          <td style="font-weight:600;color:#1A1A1A;padding:9px 12px;">{row['nombre']}</td>
          <td style="padding:9px 12px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:{pct:.0f}%;height:6px;background:{color};border-radius:4px;min-width:4px;max-width:160px;"></div>
              <span style="font-weight:700;color:{color};white-space:nowrap;">{row['cltv']:,.0f}€</span>
            </div>
          </td>
          <td style="color:#6C757D;padding:9px 12px;">{row['aov']:,.0f}€</td>
          <td style="color:#6C757D;padding:9px 12px;">{int(row['num_ventas'])}</td>
          <td style="padding:9px 12px;">
            <span style="background:{color}22;color:{color};padding:2px 10px;border-radius:20px;font-size:0.77rem;font-weight:600;">
              {row.get('cluster_label','—')}
            </span>
          </td>
        </tr>"""

    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:0.87rem;font-family:Inter,sans-serif;">
      <thead>
        <tr style="border-bottom:2px solid #E9ECEF;">
          <th style="text-align:left;padding:8px 12px;color:#6C757D;font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">Cliente</th>
          <th style="text-align:left;padding:8px 12px;color:#6C757D;font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">CLTV</th>
          <th style="text-align:left;padding:8px 12px;color:#6C757D;font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">AOV</th>
          <th style="text-align:left;padding:8px 12px;color:#6C757D;font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">Pedidos</th>
          <th style="text-align:left;padding:8px 12px;color:#6C757D;font-weight:500;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">Segmento</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


# ── CSS global ────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }

    [data-testid="stSidebar"] { background: #0F1117 !important; border-right: none !important; }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div { color: #C9D1D9 !important; }
    [data-testid="stSidebar"] hr { border-color: #30363D !important; }
    [data-testid="stSidebarNav"] a { color: #C9D1D9 !important; border-radius: 8px !important; padding: 6px 12px !important; }
    [data-testid="stSidebarNav"] a:hover { background: #21262D !important; color: #FFF !important; }
    [data-testid="stSidebarNav"] [aria-selected="true"] { background: #1F3A6E !important; color: #FFF !important; font-weight: 600 !important; }

    .kpi-card {
        background: white; border-radius: 14px; padding: 20px 22px;
        border: 1px solid #E9ECEF; box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        min-height: 115px; position: relative; overflow: hidden;
    }
    .kpi-card::before {
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #2C6FBF, #27A06B);
    }
    .kpi-label { font-size: 0.68rem; color: #8B949E; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 8px; }
    .kpi-value { font-size: 1.9rem; font-weight: 800; color: #0D1117; line-height: 1.1; letter-spacing: -0.5px; }
    .kpi-delta { font-size: 0.75rem; color: #8B949E; margin-top: 6px; }

    .page-header {
        background: linear-gradient(135deg, #1A3A6B 0%, #2C6FBF 55%, #1E8A5E 100%);
        border-radius: 16px; padding: 28px 32px; margin-bottom: 28px;
    }
    .page-header h1 { color: white !important; font-size: 1.75rem !important; font-weight: 800 !important; margin: 0 0 4px 0 !important; letter-spacing: -0.5px !important; }
    .page-header p { color: rgba(255,255,255,0.72) !important; font-size: 0.88rem !important; margin: 0 !important; }

    .alert { padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; font-size: 0.86rem; line-height: 1.55; border: 1px solid transparent; }
    .alert-danger  { background:#FFF0F0; border-color:#FFCDD2; border-left:4px solid #E57373; color:#8B1A1A; }
    .alert-warning { background:#FFF6ED; border-color:#FFE0B2; border-left:4px solid #E07B2A; color:#7A3F00; }
    .alert-success { background:#EDF7F0; border-color:#C8E6C9; border-left:4px solid #27A06B; color:#1B4D2E; }

    .section-title { font-size:1.0rem; font-weight:700; color:#0D1117; margin-bottom:2px; }
    .section-sub { font-size:0.80rem; color:#8B949E; margin-bottom:14px; }

    .insight-box { background: linear-gradient(135deg, #0D2A5C 0%, #0D3D2A 100%); border-radius: 14px; padding: 20px 24px; border: 1px solid #1F3A6E; }
    .insight-label { font-size:0.68rem; text-transform:uppercase; letter-spacing:1px; color:#58A6FF; font-weight:700; margin-bottom:6px; }
    .insight-text { font-size:1.0rem; color:#F0F6FF; font-weight:500; line-height:1.55; }

    .customer-card { background:white; border-radius:14px; padding:24px; border:1px solid #E9ECEF; box-shadow:0 4px 16px rgba(0,0,0,0.08); }
    .customer-name { font-size:1.4rem; font-weight:800; color:#0D1117; letter-spacing:-0.3px; }
    .customer-id   { font-size:0.80rem; color:#8B949E; }

    .sil-badge { display:inline-flex; align-items:center; gap:8px; background:#EDF7F0; border:1px solid #27A06B; border-radius:20px; padding:6px 18px; font-size:0.83rem; color:#1B4D2E; font-weight:600; }

    .action-table { width:100%; border-collapse:collapse; font-size:0.86rem; }
    .action-table th { text-align:left; padding:10px 14px; color:#8B949E; font-weight:600; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.8px; border-bottom:2px solid #E9ECEF; background:#F8F9FA; }
    .action-table td { padding:11px 14px; border-bottom:1px solid #F0F0F0; vertical-align:middle; }
    .action-table tr:hover td { background:#FAFBFC; }
    .p-alta  { background:#FFE5E5; color:#9B1C1C; padding:3px 12px; border-radius:20px; font-size:0.76rem; font-weight:700; }
    .p-media { background:#FEF0E0; color:#7A3F00; padding:3px 12px; border-radius:20px; font-size:0.76rem; font-weight:700; }
    .p-baja  { background:#EFEFEF; color:#5A6473; padding:3px 12px; border-radius:20px; font-size:0.76rem; font-weight:700; }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar(active_page=""):
    with st.sidebar:
        st.markdown("""
        <div style="padding:12px 0 16px 0;">
          <div style="font-size:1.3rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">
            &#128138; saleshealth
          </div>
          <div style="font-size:0.77rem;color:#8B949E;margin-top:3px;">
            Gesti&#243;n de Datos &middot; UAX 2025/26
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        st.markdown(
            '<div style="font-size:0.68rem;color:#8B949E;text-transform:uppercase;'
            'letter-spacing:1px;font-weight:700;margin-bottom:10px;">Segmentos K=3</div>',
            unsafe_allow_html=True
        )
        for label in ORDEN_CLUSTERS:
            color = COLORES_CLUSTER[label]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:9px;margin:6px 0;">'
                f'<div style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></div>'
                f'<span style="font-size:0.85rem;color:#C9D1D9;font-weight:500;">{label}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.divider()
        st.markdown(
            '<div style="font-size:0.75rem;color:#8B949E;line-height:2;">'
            '&#128197; <span style="color:#C9D1D9">2020 – 2025</span><br>'
            '&#128101; <span style="color:#C9D1D9">5.750 clientes</span><br>'
            '&#128722; <span style="color:#C9D1D9">20.000 ventas</span><br>'
            '&#128230; <span style="color:#C9D1D9">50 productos</span>'
            '</div>',
            unsafe_allow_html=True
        )
        from datetime import datetime
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        st.divider()
        st.markdown(
            f'<div style="font-size:0.70rem;color:#484F58;line-height:1.8;">'
            f'&#128337; Actualizado<br>'
            f'<span style="color:#8B949E;">{now_str}</span>'
            f'</div>',
            unsafe_allow_html=True
        )