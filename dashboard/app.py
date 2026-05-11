"""
app.py — Página de inicio del dashboard saleshealth
Executive summary: gauge con card, alertas arriba, hallazgo principal, segmentos.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    inject_css, render_sidebar, load_customer_360,
    calcular_health_score, get_lorenz, calcular_gini, PALETA, COLORES_CLUSTER, ORDEN_CLUSTERS
)

st.set_page_config(
    page_title="saleshealth | Inicio",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()
render_sidebar("inicio")

df = load_customer_360()

cltv_total   = df["cltv"].sum()
cltv_medio   = df["cltv"].mean()
cltv_mediana = df["cltv"].median()
aov_medio    = df["aov"].mean()
rr_global    = df["unidades_devueltas"].sum() / df["unidades_compradas"].sum() * 100
n_clientes   = len(df)
score, champ_pct, rr = calcular_health_score(df)

cltv_sorted_asc = np.sort(df["cltv"].values)
cltv_cum_arr    = np.cumsum(cltv_sorted_asc) / cltv_sorted_asc.sum()
pop_cum_arr     = np.arange(1, len(cltv_sorted_asc) + 1) / len(cltv_sorted_asc)
idx_20          = np.searchsorted(cltv_cum_arr, 0.20)
pct_top_80      = round((1 - pop_cum_arr[idx_20]) * 100, 1)

gini          = calcular_gini(df["cltv"])
gauge_color   = PALETA["secondary"] if score >= 70 else PALETA["warning"] if score >= 40 else PALETA["danger"]
n_churned     = len(df[df["cluster_label"] == "Churned"])
n_rr_alto     = len(df[df["return_rate"] > 50])
ingresos_perd = (df["ingresos_brutos"] - df["ingresos_netos"]).sum()
n_base        = len(df[df["cluster_label"] == "Base"])
n_champions   = len(df[df["cluster_label"] == "Champions"])
pct_cltv_champ = round(df[df["cluster_label"]=="Champions"]["cltv"].sum() / cltv_total * 100, 1)

# Header
st.markdown("""
<div class="page-header">
  <h1>Panel Ejecutivo</h1>
  <p>saleshealth &middot; Productos de salud &middot; Periodo 2020&ndash;2025</p>
</div>
""", unsafe_allow_html=True)

# Fila 1: gauge + KPIs
col_gauge, col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns([1.6, 1, 1, 1, 1])

with col_gauge:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Salud del negocio", "font": {"size": 13, "color": "#6C757D"}},
        number={"font": {"size": 46, "color": gauge_color, "family": "Inter, sans-serif"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#E9ECEF",
                     "tickfont": {"size": 9, "color": "#AAAAAA"}, "nticks": 6},
            "bar": {"color": gauge_color, "thickness": 0.3},
            "bgcolor": "#F8F9FA", "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "#FFE5E5"},
                {"range": [40, 70], "color": "#FFF3E0"},
                {"range": [70, 100], "color": "#E8F5E9"},
            ],
            "threshold": {"line": {"color": gauge_color, "width": 3}, "thickness": 0.75, "value": score}
        }
    ))
    fig_gauge.update_layout(
        height=200, margin=dict(t=36, b=0, l=16, r=16),
        paper_bgcolor="white", font={"family": "Inter, sans-serif"}
    )
    st.markdown("""<div style="background:white;border-radius:14px;padding:12px 16px 8px 16px;
        border:1px solid #E9ECEF;box-shadow:0 2px 12px rgba(0,0,0,0.07);
        position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,#2C6FBF,#27A06B);"></div>""", unsafe_allow_html=True)
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f'<div style="text-align:center;font-size:0.74rem;color:#8B949E;margin-top:-14px;padding-bottom:8px;">' +
        f'Champions {champ_pct}% &middot; RR {rr:.1f}% &middot; CLTV positivo {round(len(df[df["cltv"]>0])/len(df)*100)}%' +
        f'</div></div>', unsafe_allow_html=True
    )

with col_kpi1:
    st.markdown(f"""<div class="kpi-card">
      <div class="kpi-label">CLTV Total</div>
      <div class="kpi-value">{cltv_total/1_000_000:.1f}<span style="font-size:1rem;font-weight:500;color:#8B949E;">M€</span></div>
      <div class="kpi-delta">Media: {cltv_medio:,.0f}€ &middot; Mediana: {cltv_mediana:.0f}€</div>
    </div>""", unsafe_allow_html=True)

with col_kpi2:
    st.markdown(f"""<div class="kpi-card">
      <div class="kpi-label">Clientes activos</div>
      <div class="kpi-value">{n_clientes:,}</div>
      <div class="kpi-delta"><span style="color:{PALETA["primary"]};font-weight:700;">{champ_pct}%</span> Champions &middot; {round(n_base/n_clientes*100,1)}% Base</div>
    </div>""", unsafe_allow_html=True)

with col_kpi3:
    st.markdown(f"""<div class="kpi-card">
      <div class="kpi-label">AOV medio</div>
      <div class="kpi-value">{aov_medio:,.0f}<span style="font-size:1rem;font-weight:500;color:#8B949E;">€</span></div>
      <div class="kpi-delta">Mediana: {df["aov"].median():,.0f}€ &middot; distribución sesgada</div>
    </div>""", unsafe_allow_html=True)

with col_kpi4:
    rr_color = PALETA["secondary"] if rr_global < 3 else PALETA["warning"] if rr_global < 7 else PALETA["danger"]
    st.markdown(f"""<div class="kpi-card">
      <div class="kpi-label">Return Rate</div>
      <div class="kpi-value" style="color:{rr_color};">{rr_global:.1f}<span style="font-size:1rem;font-weight:500;color:#8B949E;">%</span></div>
      <div class="kpi-delta">{n_rr_alto:,} clientes con RR &gt; 50%</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Fila 2: alertas en dos columnas
st.markdown('<div class="section-title">Alertas automáticas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Generadas desde los datos · actualización en cada carga</div>', unsafe_allow_html=True)

col_a1, col_a2 = st.columns(2)
with col_a1:
    st.markdown(f"""
    <div class="alert alert-danger">
      🔴 <b>{n_churned:,} clientes Churned</b> con Return Rate &gt;86% —
      CLTV medio negativo. Candidatos a baja o campaña de recuperación agresiva.
    </div>
    <div class="alert alert-warning">
      🟡 <b>{n_base:,} clientes Base ({round(n_base/n_clientes*100,1)}%)</b>
      llevan una media de 880 días sin comprar.
      Potencial de reactivación alto si se actúa con descuento dirigido.
    </div>
    """, unsafe_allow_html=True)
with col_a2:
    st.markdown(f"""
    <div class="alert alert-warning">
      🟡 <b>{n_rr_alto:,} clientes</b> con Return Rate &gt;50% —
      pérdida estimada en ingresos netos: <b>{ingresos_perd:,.0f}€</b>.
    </div>
    <div class="alert alert-success">
      🟢 <b>{n_champions:,} Champions</b> generan el <b>{pct_cltv_champ}%</b>
      del CLTV total. Prioridad máxima de retención y fidelización.
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Fila 3: hallazgo + lorenz mini
col_insight, col_lorenz = st.columns([1, 1.2])
with col_insight:
    st.markdown(f"""
    <div class="insight-box">
      <div class="insight-label">📊 Hallazgo principal</div>
      <div class="insight-text">
        El <b>{pct_top_80}% de clientes TOP</b> genera el <b>80% del CLTV total</b>
        — concentración extrema que define la estrategia de retención.
      </div>
      <div style="margin-top:18px;display:flex;gap:22px;flex-wrap:wrap;">
        <div>
          <div style="font-size:0.68rem;color:#58A6FF;text-transform:uppercase;letter-spacing:0.8px;">CLTV Total</div>
          <div style="font-size:1.3rem;font-weight:800;color:white;">{cltv_total/1e6:.1f}M€</div>
        </div>
        <div>
          <div style="font-size:0.68rem;color:#58A6FF;text-transform:uppercase;letter-spacing:0.8px;">Concentración</div>
          <div style="font-size:1.3rem;font-weight:800;color:white;">{pct_top_80}% → 80%</div>
        </div>
        <div>
          <div style="font-size:0.68rem;color:#58A6FF;text-transform:uppercase;letter-spacing:0.8px;">Champions</div>
          <div style="font-size:1.3rem;font-weight:800;color:white;">{pct_cltv_champ}% CLTV</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_lorenz:
    pop_cum, cltv_cum = get_lorenz(df["cltv"])
    fig_mini = go.Figure()
    fig_mini.add_trace(go.Scatter(
        x=pop_cum, y=cltv_cum, mode="lines",
        line=dict(color=PALETA["primary"], width=2.5),
        fill="tozeroy", fillcolor="rgba(44,111,191,0.08)",
        hovertemplate="%{x:.1f}% clientes → %{y:.1f}% CLTV<extra></extra>"
    ))
    fig_mini.add_trace(go.Scatter(
        x=[0,100], y=[0,100], mode="lines",
        line=dict(color="#CCCCCC", width=1, dash="dash"), hoverinfo="skip"
    ))
    fig_mini.add_vline(x=100 - pct_top_80, line_dash="dot", line_color=PALETA["danger"], opacity=0.7)
    fig_mini.update_layout(
        height=200, margin=dict(t=10, b=36, l=46, r=10),
        paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
        xaxis=dict(title=dict(text="% clientes", font=dict(size=10)), tickfont=dict(size=9), gridcolor="#F0F0F0"),
        yaxis=dict(title=dict(text="% CLTV", font=dict(size=10)), tickfont=dict(size=9), gridcolor="#F0F0F0"),
        font=dict(family="Inter, sans-serif")
    )
    st.plotly_chart(fig_mini, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# Fila 4: segmentos
st.markdown('<div class="section-title">Distribución de segmentos</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">K-Means K=3 · PCA 2D · silhouette 0.847</div>', unsafe_allow_html=True)

segment_info = {
    "Champions": {"icon": "🏆", "desc": "CLTV alto · compra frecuente · cliente antiguo", "accion": "Programa VIP + referidos"},
    "Base":      {"icon": "👥", "desc": "Una compra · inactivos ~2.4 años · sin devoluciones", "accion": "Reactivación + incentivo segunda compra"},
    "Churned":   {"icon": "⚠️", "desc": "Return Rate 86% · CLTV mínimo · alto riesgo", "accion": "Descuento recuperación o baja"},
}
for col, label in zip(st.columns(3), ORDEN_CLUSTERS):
    sub   = df[df["cluster_label"] == label]
    info  = segment_info[label]
    color = COLORES_CLUSTER[label]
    n_seg = len(sub)
    with col:
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:20px;
                    border:1px solid #E9ECEF;border-left:4px solid {color};
                    box-shadow:0 2px 10px rgba(0,0,0,0.06);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-size:1.2rem;">{info["icon"]}</span>
            <span style="background:{color}22;color:{color};padding:3px 12px;
                         border-radius:20px;font-size:0.78rem;font-weight:700;">{label}</span>
          </div>
          <div style="font-size:1.7rem;font-weight:800;color:#0D1117;letter-spacing:-0.5px;">{n_seg:,}
            <span style="font-size:0.88rem;font-weight:500;color:#8B949E;">clientes ({round(n_seg/n_clientes*100,1)}%)</span>
          </div>
          <div style="font-size:0.87rem;font-weight:700;color:{color};margin:5px 0 10px 0;">CLTV medio: {sub["cltv"].mean():,.0f}€</div>
          <div style="font-size:0.81rem;color:#6C757D;line-height:1.55;margin-bottom:12px;">{info["desc"]}</div>
          <div style="font-size:0.79rem;color:{color};font-weight:600;background:{color}11;padding:6px 12px;border-radius:8px;">→ {info["accion"]}</div>
        </div>
        """, unsafe_allow_html=True)