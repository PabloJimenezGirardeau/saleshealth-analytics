"""
pages/2_Segmentacion.py — Clustering: scatter PCA, radar, silhouette, tabla de acción.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    inject_css, render_sidebar, load_customer_360, get_pca_data,
    PALETA, COLORES_CLUSTER, ORDEN_CLUSTERS, FEATURES, CLUSTER_LABELS
)

st.set_page_config(
    page_title="saleshealth | Segmentación",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()
render_sidebar("segmentacion")

# ── Datos ─────────────────────────────────────────────────────────────────────
df              = load_customer_360()
df_pca, var_exp = get_pca_data(df)

# Merge para hover info
df_plot = df_pca.merge(
    df[['cliente_sk', 'cltv', 'aov', 'recencia_dias', 'num_ventas', 'return_rate']],
    on='cliente_sk', how='left'
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h1>&#127919; Segmentaci&#243;n de Clientes</h1>
  <p>K-Means K=3 &middot; PCA 2D &middot; 7 features &middot; silhouette 0.847</p>
</div>
""", unsafe_allow_html=True)

# Silhouette badge
st.markdown("""
<div style="margin-bottom:20px;">
  <span class="sil-badge">
    ✓ Silhouette score K=3: <b>0.847</b> — separación óptima confirmada
  </span>
  &nbsp;&nbsp;
  <span style="font-size:0.82rem;color:#6C757D;">
    Varianza explicada: PC1 {:.1f}% · PC2 {:.1f}% · total {:.1f}%
  </span>
</div>
""".format(var_exp[0]*100, var_exp[1]*100, sum(var_exp)*100),
unsafe_allow_html=True)

# ── Scatter PCA ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Clusters en el espacio PCA</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Cada punto es un cliente · hover para ver detalle · ★ = centroide del cluster</div>', unsafe_allow_html=True)

fig_scatter = go.Figure()

for label in ORDEN_CLUSTERS:
    mask = df_plot['cluster_label'] == label
    sub  = df_plot[mask]
    fig_scatter.add_trace(go.Scatter(
        x=sub['pc1'], y=sub['pc2'],
        mode='markers',
        name=label,
        marker=dict(
            color=COLORES_CLUSTER[label],
            size=8,
            opacity=0.65,
            line=dict(width=0)
        ),
        customdata=np.column_stack([
            sub['nombre'], sub['cltv'], sub['aov'],
            sub['recencia_dias'], sub['num_ventas']
        ]),
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            'CLTV: %{customdata[1]:,.0f}€<br>'
            'AOV: %{customdata[2]:,.0f}€<br>'
            'Recencia: %{customdata[3]:.0f} días<br>'
            'Pedidos: %{customdata[4]:.0f}<extra></extra>'
        )
    ))

# Centroides
for label in ORDEN_CLUSTERS:
    mask = df_plot['cluster_label'] == label
    cx   = df_plot.loc[mask, 'pc1'].mean()
    cy   = df_plot.loc[mask, 'pc2'].mean()
    n    = mask.sum()
    fig_scatter.add_trace(go.Scatter(
        x=[cx], y=[cy],
        mode='markers+text',
        marker=dict(
            symbol='star', size=22,
            color=COLORES_CLUSTER[label],
            line=dict(color='white', width=2)
        ),
        text=[f' {label}'],
        textposition='middle right',
        textfont=dict(size=12, color=COLORES_CLUSTER[label], family='Inter, sans-serif'),
        showlegend=False,
        hovertemplate=f'<b>Centroide {label}</b><br>{n:,} clientes<extra></extra>'
    ))

fig_scatter.update_layout(
    height=480,
    paper_bgcolor='white', plot_bgcolor='white',
    legend=dict(
        title='Segmento', orientation='v',
        yanchor='top', y=0.98, xanchor='right', x=0.99,
        bgcolor='white', bordercolor='#E9ECEF', borderwidth=1,
        font=dict(size=12)
    ),
    xaxis=dict(
        title=f'PC1 ({var_exp[0]*100:.1f}% varianza explicada)',
        gridcolor='#F5F5F5', zeroline=False
    ),
    yaxis=dict(
        title=f'PC2 ({var_exp[1]*100:.1f}% varianza explicada)',
        gridcolor='#F5F5F5', zeroline=False
    ),
    margin=dict(t=20, b=50, l=60, r=20),
    font=dict(family='Inter, sans-serif', color='#1A1A1A'),
    hovermode='closest'
)
st.plotly_chart(fig_scatter, use_container_width=True,
                config={'displayModeBar': True, 'modeBarButtonsToRemove': ['select2d', 'lasso2d']})

st.markdown("<br>", unsafe_allow_html=True)

# ── Radar + perfil ────────────────────────────────────────────────────────────
col_radar, col_perfil = st.columns([1, 1.1])

METRICAS_RADAR = ['cltv', 'aov', 'frecuencia_mensual', 'antiguedad_dias', 'num_ventas']
LABELS_RADAR   = ['CLTV', 'AOV', 'Frecuencia', 'Antigüedad', 'Num. ventas']

df_radar = df.groupby('cluster_label')[METRICAS_RADAR].mean().loc[ORDEN_CLUSTERS]
df_norm  = df_radar.copy()
for col in METRICAS_RADAR:
    mn, mx = df_radar[col].min(), df_radar[col].max()
    df_norm[col] = (df_radar[col] - mn) / (mx - mn + 1e-9)

with col_radar:
    st.markdown('<div class="section-title">Perfil por cluster</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Métricas normalizadas 0-1 · mayor área = mayor valor relativo</div>', unsafe_allow_html=True)

    fig_radar = go.Figure()
    for label in ORDEN_CLUSTERS:
        vals  = df_norm.loc[label, METRICAS_RADAR].tolist()
        vals += vals[:1]
        ang   = LABELS_RADAR + [LABELS_RADAR[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals, theta=ang, name=label,
            line=dict(color=COLORES_CLUSTER[label], width=2.2),
            fill='toself',
            fillcolor=COLORES_CLUSTER[label],
            opacity=0.12
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,1],
                            tickfont=dict(size=8, color='#999'),
                            gridcolor='#E9ECEF'),
            angularaxis=dict(tickfont=dict(size=11, color='#1A1A1A'),
                             gridcolor='#E9ECEF'),
            bgcolor='white'
        ),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15,
                    font=dict(size=11)),
        paper_bgcolor='white',
        height=360,
        margin=dict(t=20, b=60, l=40, r=40),
        font=dict(family='Inter, sans-serif')
    )
    st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

with col_perfil:
    st.markdown('<div class="section-title">Métricas medias por segmento</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Comparativa de KPIs clave</div>', unsafe_allow_html=True)

    COLS_TABLA = ['cltv', 'aov', 'num_ventas', 'recencia_dias', 'return_rate', 'antiguedad_dias']
    LABELS_T   = ['CLTV (€)', 'AOV (€)', 'Pedidos', 'Recencia (d)', 'RR (%)', 'Antigüedad (d)']

    df_perf = df.groupby('cluster_label')[COLS_TABLA].mean().loc[ORDEN_CLUSTERS].round(1)

    rows = ""
    for label in ORDEN_CLUSTERS:
        color = COLORES_CLUSTER[label]
        row   = df_perf.loc[label]
        n_seg = len(df[df['cluster_label'] == label])
        rows += f"""
        <tr>
          <td style="padding:10px 14px;">
            <span style="background:{color}22;color:{color};padding:2px 10px;
                         border-radius:20px;font-size:0.77rem;font-weight:600;">{label}</span>
            <br><span style="font-size:0.75rem;color:#999;margin-top:2px;display:block;">{n_seg:,} clientes</span>
          </td>
          <td style="padding:10px 14px;font-weight:700;color:{color};">{row['cltv']:,.0f}€</td>
          <td style="padding:10px 14px;color:#1A1A1A;">{row['aov']:,.0f}€</td>
          <td style="padding:10px 14px;color:#1A1A1A;">{row['num_ventas']:.1f}</td>
          <td style="padding:10px 14px;color:#1A1A1A;">{row['recencia_dias']:.0f}d</td>
          <td style="padding:10px 14px;color:#1A1A1A;">{row['return_rate']:.1f}%</td>
          <td style="padding:10px 14px;color:#1A1A1A;">{row['antiguedad_dias']:.0f}d</td>
        </tr>"""

    header_cells = "".join(
        f'<th style="text-align:left;padding:9px 14px;color:#6C757D;font-weight:500;'
        f'font-size:0.70rem;text-transform:uppercase;letter-spacing:0.5px;'
        f'border-bottom:2px solid #E9ECEF;">{h}</th>'
        for h in ['Segmento'] + LABELS_T
    )

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:8px;border:1px solid #E9ECEF;">
      <table class="action-table">
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabla de acción ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Plan de acción por segmento</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Recomendaciones de negocio derivadas del análisis</div>', unsafe_allow_html=True)

acciones = [
    ('Champions', f'{len(df[df["cluster_label"]=="Champions"]):,} (13%)',
     'CLTV alto · compra frecuente · cliente antiguo · RR bajo',
     'Programa VIP exclusivo + campaña de referidos',
     '<span class="p-alta">ALTA</span>'),
    ('Base', f'{len(df[df["cluster_label"]=="Base"]):,} (80%)',
     'Una compra · inactivos ~2.4 años · sin devoluciones',
     'Email de reactivación + descuento en segunda compra',
     '<span class="p-media">MEDIA-ALTA</span>'),
    ('Churned', f'{len(df[df["cluster_label"]=="Churned"]):,} (7%)',
     'Return Rate 86% · CLTV mínimo · perfil de abandono',
     'Descuento agresivo de recuperación o dar de baja',
     '<span class="p-baja">BAJA</span>'),
]

rows_acc = ""
for seg, tam, caract, accion, prio in acciones:
    color = COLORES_CLUSTER[seg]
    rows_acc += f"""
    <tr>
      <td style="padding:12px 14px;">
        <span style="background:{color}22;color:{color};padding:3px 12px;
               border-radius:20px;font-size:0.82rem;font-weight:600;">{seg}</span>
      </td>
      <td style="padding:12px 14px;color:#6C757D;font-size:0.85rem;">{tam}</td>
      <td style="padding:12px 14px;color:#1A1A1A;font-size:0.85rem;">{caract}</td>
      <td style="padding:12px 14px;color:#1A1A1A;font-size:0.85rem;font-weight:500;">→ {accion}</td>
      <td style="padding:12px 14px;">{prio}</td>
    </tr>"""

st.markdown(f"""
<div style="border-radius:10px;border:1px solid #E9ECEF;overflow:hidden;">
  <table class="action-table">
    <thead>
      <tr>
        <th>Segmento</th><th>Tamaño</th><th>Característica clave</th>
        <th>Acción recomendada</th><th>Prioridad</th>
      </tr>
    </thead>
    <tbody>{rows_acc}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Silhouette chart ──────────────────────────────────────────────────────────
with st.expander("📊 Ver análisis de silueta completo (K=2..8)"):
    st.markdown('<div class="section-sub">Justificación estadística de la elección K=3</div>', unsafe_allow_html=True)

    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA as PCA_

    df_ml = df[['cliente_sk'] + FEATURES].copy()
    df_ml[FEATURES] = df_ml[FEATURES].fillna(0)
    X = df_ml[FEATURES].values
    X_scaled = StandardScaler().fit_transform(X)
    X_pca    = PCA_(n_components=2, random_state=42).fit_transform(X_scaled)

    k_range = range(2, 9)
    scores  = []
    for k in k_range:
        lbl = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_pca)
        scores.append(silhouette_score(X_pca, lbl))

    fig_sil = go.Figure(go.Bar(
        x=list(k_range), y=scores,
        marker_color=[PALETA['secondary'] if k == 3 else PALETA['primary'] for k in k_range],
        text=[f'{s:.3f}' for s in scores],
        textposition='outside',
        hovertemplate='K=%{x}<br>Silhouette: %{y:.3f}<extra></extra>'
    ))
    fig_sil.add_vline(x=3, line_dash='dot', line_color=PALETA['secondary'], opacity=0.7)
    fig_sil.update_layout(
        height=280, showlegend=False,
        paper_bgcolor='white', plot_bgcolor='white',
        xaxis=dict(title='K', tickvals=list(k_range), showgrid=False),
        yaxis=dict(title='Silhouette score', gridcolor='#F0F0F0',
                   range=[0, max(scores)*1.2]),
        margin=dict(t=20, b=40, l=60, r=20),
        font=dict(family='Inter, sans-serif', color='#1A1A1A')
    )
    st.plotly_chart(fig_sil, use_container_width=True, config={'displayModeBar': False})