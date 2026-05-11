"""
pages/1_CLTV.py — Análisis de valor: CLTV, Lorenz, zonas, heatmap, cohorts, top clientes.
Mejoras: barras orientación con gradiente, cohorts con colores diferenciados,
         selector de segmento en top tabla.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    inject_css, render_sidebar, load_customer_360, load_zona_data,
    get_zona_predominante, get_lorenz, render_top_table, calcular_gini,
    PALETA, COLORES_CLUSTER, ORDEN_CLUSTERS
)

st.set_page_config(page_title="saleshealth | CLTV", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
render_sidebar("cltv")

df      = load_customer_360()
df_zona = load_zona_data()
df_z    = get_zona_predominante(df, df_zona)

pop_cum, cltv_cum = get_lorenz(df["cltv"])
cltv_sorted_asc = np.sort(df["cltv"].values)
cltv_cum_arr    = np.cumsum(cltv_sorted_asc) / cltv_sorted_asc.sum()
pop_cum_arr     = np.arange(1, len(cltv_sorted_asc) + 1) / len(cltv_sorted_asc)
idx_20          = np.searchsorted(cltv_cum_arr, 0.20)
pct_top_80      = round((1 - pop_cum_arr[idx_20]) * 100, 1)
x_lorenz_mark   = pop_cum_arr[idx_20] * 100
gini            = calcular_gini(df["cltv"])

st.markdown("""
<div class="page-header">
  <h1>&#128200; An&#225;lisis de Valor &mdash; CLTV</h1>
  <p>Customer Lifetime Value &middot; concentraci&#243;n &middot; geograf&#237;a &middot; top clientes &middot; cohorts</p>
</div>
""", unsafe_allow_html=True)

# ── Lorenz ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Curva de Lorenz &mdash; Concentraci\u00f3n del CLTV</div>', unsafe_allow_html=True)
col_lor_sub, col_gini = st.columns([3, 1])
with col_lor_sub:
    st.markdown(f'<div class="section-sub">El {pct_top_80}% de clientes TOP genera el 80% del CLTV total &middot; CLTV total: {df["cltv"].sum()/1e6:.1f}M\u20ac</div>', unsafe_allow_html=True)
with col_gini:
    gini_color = "#27A06B" if gini < 0.4 else "#E07B2A" if gini < 0.7 else "#E57373"
    st.markdown(
        f'<div style="text-align:right;padding-top:2px;">'
        f'<span style="background:{gini_color}22;color:{gini_color};border:1px solid {gini_color}66;'
        f'padding:4px 14px;border-radius:20px;font-size:0.82rem;font-weight:700;">'
        f'Coef. Gini: {gini}</span>'
        f'<div style="font-size:0.68rem;color:#8B949E;margin-top:3px;text-align:right;">'
        f'0=igualdad perfecta &middot; 1=máxima concentración</div>'
        f'</div>',
        unsafe_allow_html=True
    )

fig_lorenz = go.Figure()
fig_lorenz.add_trace(go.Scatter(
    x=pop_cum, y=cltv_cum, mode="lines", name="Curva de Lorenz",
    line=dict(color=PALETA["primary"], width=2.5),
    fill="tozeroy", fillcolor="rgba(44,111,191,0.07)",
    hovertemplate="%{x:.1f}% de clientes \u2192 %{y:.1f}% del CLTV<extra></extra>"
))
fig_lorenz.add_trace(go.Scatter(
    x=[0,100], y=[0,100], mode="lines", name="Igualdad perfecta",
    line=dict(color="#BBBBBB", width=1.5, dash="dash"), hoverinfo="skip"
))
fig_lorenz.add_vline(x=x_lorenz_mark, line_dash="dot", line_color=PALETA["danger"], opacity=0.6)
fig_lorenz.add_hline(y=20, line_dash="dot", line_color=PALETA["danger"], opacity=0.6)
fig_lorenz.add_annotation(
    x=x_lorenz_mark, y=20,
    text=f"<b>El {pct_top_80}% de clientes<br>genera el 80% del CLTV</b>",
    showarrow=True, arrowhead=2, arrowcolor=PALETA["danger"],
    font=dict(size=11, color=PALETA["danger"]),
    bgcolor="white", bordercolor=PALETA["danger"], borderwidth=1, ax=-90, ay=-50
)
fig_lorenz.update_layout(
    height=360, paper_bgcolor="white", plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(title="% acumulado de clientes (orden ascendente)", gridcolor="#F0F0F0", range=[0,100]),
    yaxis=dict(title="% acumulado del CLTV total", gridcolor="#F0F0F0", range=[0,100]),
    margin=dict(t=20, b=50, l=60, r=20),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)
st.plotly_chart(fig_lorenz, use_container_width=True, config={"displayModeBar": False})
st.markdown("<br>", unsafe_allow_html=True)

# ── CLTV por zona ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">CLTV medio por zona geogr\u00e1fica</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Zona predominante asignada via fact_ventas \u2192 dim_zona</div>', unsafe_allow_html=True)

col_area, col_ori = st.columns(2)

df_area = (df_z[df_z["tipo_area"].notna()]
           .groupby("tipo_area").agg(clientes=("cliente_sk","count"), cltv_medio=("cltv","mean"))
           .reset_index().sort_values("cltv_medio", ascending=False))

df_ori = (df_z[df_z["orientacion"].notna()]
          .groupby("orientacion").agg(clientes=("cliente_sk","count"), cltv_medio=("cltv","mean"))
          .reset_index().sort_values("cltv_medio", ascending=False))

with col_area:
    fig_area = go.Figure()
    area_colors = [PALETA["primary"], PALETA["secondary"]]
    for i, row in df_area.reset_index(drop=True).iterrows():
        fig_area.add_trace(go.Bar(
            x=[row["tipo_area"]], y=[row["cltv_medio"]],
            name=row["tipo_area"],
            marker_color=area_colors[i % 2],
            text=f"{row['cltv_medio']:,.0f}\u20ac<br><span style='font-size:10px'>{row['clientes']:,} clientes</span>",
            textposition="inside", insidetextanchor="middle",
            hovertemplate=f"<b>{row['tipo_area']}</b><br>CLTV: {row['cltv_medio']:,.0f}\u20ac<br>Clientes: {row['clientes']:,}<extra></extra>"
        ))
    fig_area.update_layout(
        title=dict(text="Por tipo de \u00e1rea", font=dict(size=12, color="#1A1A1A"), x=0),
        height=300, showlegend=False, barmode="group",
        paper_bgcolor="white", plot_bgcolor="white",
        yaxis=dict(gridcolor="#F0F0F0", title="CLTV medio (EUR)"),
        xaxis=dict(showgrid=False),
        margin=dict(t=40, b=20, l=60, r=10),
        font=dict(family="Inter, sans-serif")
    )
    st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar": False})

with col_ori:
    # Gradiente de color: mayor CLTV = azul oscuro, menor = azul claro
    n_ori    = len(df_ori)
    blues    = ["#1A3A6B","#1E4F96","#2C6FBF","#4A8FD4","#6AAEE0","#8FCAEC","#B8DEF5"]
    col_list = [blues[min(i, len(blues)-1)] for i in range(n_ori)]

    fig_ori = go.Figure()
    fig_ori.add_trace(go.Bar(
        x=df_ori["orientacion"], y=df_ori["cltv_medio"],
        marker_color=col_list, marker_line_width=0,
        text=df_ori["cltv_medio"].apply(lambda v: f"{v:,.0f}\u20ac"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>CLTV: %{y:,.0f}\u20ac<extra></extra>"
    ))
    fig_ori.update_layout(
        title=dict(text="Por orientaci\u00f3n geogr\u00e1fica (mayor \u2192 menor CLTV)", font=dict(size=12, color="#1A1A1A"), x=0),
        height=300, showlegend=False,
        paper_bgcolor="white", plot_bgcolor="white",
        yaxis=dict(gridcolor="#F0F0F0", title="CLTV medio (EUR)"),
        xaxis=dict(showgrid=False, title=""),
        margin=dict(t=40, b=20, l=60, r=10),
        font=dict(family="Inter, sans-serif")
    )
    st.plotly_chart(fig_ori, use_container_width=True, config={"displayModeBar": False})

# ── Heatmap ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title" style="margin-top:8px;">Mapa de calor &mdash; Orientaci\u00f3n \u00d7 Tipo de \u00e1rea</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">CLTV medio por cruce de variables geogr\u00e1ficas</div>', unsafe_allow_html=True)

pivot = (df_z[df_z["orientacion"].notna() & df_z["tipo_area"].notna()]
         .groupby(["orientacion","tipo_area"])["cltv"].mean().round(0)
         .reset_index().pivot(index="orientacion", columns="tipo_area", values="cltv").fillna(0))

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
    colorscale=[[0,"#EBF3FF"],[0.5,"#7AAEE8"],[1,"#2C6FBF"]],
    text=[[f"{v:,.0f}\u20ac" for v in row] for row in pivot.values],
    texttemplate="<b>%{text}</b>", textfont=dict(size=12, color="white"),
    showscale=True, colorbar=dict(title=dict(text="CLTV (\u20ac)", font=dict(size=11))),
    hovertemplate="<b>%{y} \u00d7 %{x}</b><br>CLTV medio: %{z:,.0f}\u20ac<extra></extra>"
))
fig_heat.update_layout(
    height=300, paper_bgcolor="white", plot_bgcolor="white",
    xaxis=dict(title="Tipo de \u00e1rea", side="bottom"),
    yaxis=dict(title="Orientaci\u00f3n"),
    margin=dict(t=20, b=50, l=90, r=80),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)
st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
st.markdown("<br>", unsafe_allow_html=True)

# ── Cohorts con colores diferenciados ─────────────────────────────────────────
st.markdown('<div class="section-title">CLTV medio por cohorte de primera compra</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-sub">Escala logar\u00edtmica \u00b7 '
    'CLTV bajo en 2022-2025: clientes recientes tienen poca antig\u00fcedad \u2192 f\u00f3rmula CLTV \u00d7 meses_activo es menor</div>',
    unsafe_allow_html=True
)

df["anio_primera_compra"] = pd.to_datetime(df["primera_compra"]).dt.year
cohorts = (df.groupby("anio_primera_compra")
           .agg(clientes=("cliente_sk","count"), cltv_medio=("cltv","mean"))
           .reset_index())

# Colores: azul para cohorts consolidados (2020-2021), gris azulado para recientes
cohort_colors = []
for yr in cohorts["anio_primera_compra"]:
    if yr <= 2021:
        cohort_colors.append(PALETA["primary"])
    else:
        cohort_colors.append("#90A4AE")

fig_cohorts = go.Figure()
fig_cohorts.add_trace(go.Bar(
    x=cohorts["anio_primera_compra"],
    y=cohorts["cltv_medio"],
    marker_color=cohort_colors, marker_line_width=0,
    text=cohorts["cltv_medio"].apply(lambda v: f"{v:,.0f}\u20ac"),
    textposition="outside",
    customdata=cohorts["clientes"],
    hovertemplate="<b>Cohorte %{x}</b><br>CLTV medio: %{y:,.0f}\u20ac<br>Clientes: %{customdata:,}<extra></extra>"
))
# Anotación explicativa en la barra de 2020
fig_cohorts.add_annotation(
    x=2020, y=cohorts[cohorts["anio_primera_compra"]==2020]["cltv_medio"].values[0],
    text=f"<b>{cohorts[cohorts['anio_primera_compra']==2020]['clientes'].values[0]:,} clientes</b><br>Cohorte consolidado",
    showarrow=True, arrowhead=2, arrowcolor=PALETA["primary"],
    font=dict(size=10, color=PALETA["primary"]),
    bgcolor="white", bordercolor=PALETA["primary"], borderwidth=1,
    ax=60, ay=-30
)
fig_cohorts.update_layout(
    height=340, showlegend=False,
    paper_bgcolor="white", plot_bgcolor="white",
    yaxis=dict(type="log", gridcolor="#F0F0F0", title="CLTV medio (EUR) \u2014 escala log"),
    xaxis=dict(showgrid=False, title="A\u00f1o de primera compra",
               tickvals=cohorts["anio_primera_compra"].tolist()),
    margin=dict(t=20, b=50, l=70, r=20),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)
st.plotly_chart(fig_cohorts, use_container_width=True, config={"displayModeBar": False})

# Leyenda manual cohorts
st.markdown(f"""
<div style="display:flex;gap:20px;margin-top:-8px;margin-bottom:16px;font-size:0.8rem;">
  <div style="display:flex;align-items:center;gap:6px;">
    <div style="width:12px;height:12px;border-radius:3px;background:{PALETA["primary"]};"></div>
    <span style="color:#6C757D;">Cohortes consolidados (2020-2021)</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <div style="width:12px;height:12px;border-radius:3px;background:#90A4AE;"></div>
    <span style="color:#6C757D;">Cohortes recientes &mdash; CLTV bajo por poca antig\u00fcedad</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Top clientes con selector de segmento ─────────────────────────────────────
st.markdown('<div class="section-title">Top clientes por CLTV</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Barra proporcional al CLTV m\u00e1ximo del grupo seleccionado</div>', unsafe_allow_html=True)

col_sel, col_n = st.columns([2, 1])
with col_sel:
    seg_opciones = ["Todos"] + ORDEN_CLUSTERS
    seg_sel = st.selectbox("Ver top de:", seg_opciones, label_visibility="collapsed")
with col_n:
    n_top = st.selectbox("Mostrar:", [10, 20, 50], index=1, label_visibility="collapsed")

if seg_sel == "Todos":
    df_top = df.nlargest(n_top, "cltv")
else:
    df_top = df[df["cluster_label"] == seg_sel].nlargest(n_top, "cltv")

st.markdown(render_top_table(df_top, n=n_top), unsafe_allow_html=True)