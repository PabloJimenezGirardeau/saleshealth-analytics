"""
pages/4_Metricas_Negocio.py — Evolución de ventas, productos, márgenes, retención.
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
    inject_css, render_sidebar, load_customer_360, load_ventas_negocio,
    PALETA, COLORES_CLUSTER, ORDEN_CLUSTERS
)

st.set_page_config(page_title="saleshealth | Métricas de Negocio", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
render_sidebar("negocio")

# ── Datos ─────────────────────────────────────────────────────────────────────
df_c  = load_customer_360()
df_v  = load_ventas_negocio()

st.markdown("""
<div class="page-header">
  <h1>&#128202; M&#233;tricas de Negocio</h1>
  <p>Evoluci&#243;n de ventas &middot; top productos &middot; m&#225;rgenes &middot; retenci&#243;n por a&#241;o</p>
</div>
""", unsafe_allow_html=True)

# ── KPIs globales de negocio ──────────────────────────────────────────────────
total_ventas   = df_v["subtotal_neto"].sum()
total_pedidos  = df_v.groupby(["cliente_sk","anio","mes"]).ngroups
margen_global  = df_v["margen_bruto"].sum() / df_v["subtotal_bruto"].sum() * 100
unidades_tot   = df_v["cantidad"].sum()
devoluciones   = df_v["cantidad_devuelta"].sum()

c1, c2, c3, c4 = st.columns(4)
for col, label, val, delta in [
    (c1, "Ingresos netos totales", f"{total_ventas/1e6:.2f}M€", f"{df_v['subtotal_bruto'].sum()/1e6:.2f}M€ bruto"),
    (c2, "Líneas de venta", f"{len(df_v):,}", f"{unidades_tot:,} unidades vendidas"),
    (c3, "Margen bruto global", f"{margen_global:.1f}%", f"{df_v['margen_bruto'].sum()/1e6:.2f}M€ en valor absoluto"),
    (c4, "Unidades devueltas", f"{devoluciones:,}", f"{devoluciones/unidades_tot*100:.1f}% del total vendido"),
]:
    with col:
        col.markdown(f"""<div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value" style="font-size:1.6rem;">{val}</div>
          <div class="kpi-delta">{delta}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Evolución anual de ventas ─────────────────────────────────────────────────
st.markdown('<div class="section-title">Evoluci\u00f3n anual de ventas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Ingresos netos, margen bruto y unidades vendidas por a\u00f1o</div>', unsafe_allow_html=True)

anual = df_v.groupby("anio").agg(
    ingresos_netos  = ("subtotal_neto",  "sum"),
    ingresos_brutos = ("subtotal_bruto", "sum"),
    margen_bruto    = ("margen_bruto",   "sum"),
    unidades        = ("cantidad",       "sum"),
    lineas          = ("cantidad",       "count"),
    clientes_unicos = ("cliente_sk",     "nunique"),
).reset_index()
anual["margen_pct"] = anual["margen_bruto"] / anual["ingresos_brutos"] * 100

col_ev1, col_ev2 = st.columns([1.6, 1])

with col_ev1:
    fig_ev = go.Figure()
    fig_ev.add_trace(go.Bar(
        x=anual["anio"], y=anual["ingresos_netos"],
        name="Ingresos netos", marker_color=PALETA["primary"],
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Ingresos netos: %{y:,.0f}€<extra></extra>"
    ))
    fig_ev.add_trace(go.Bar(
        x=anual["anio"], y=anual["margen_bruto"],
        name="Margen bruto", marker_color=PALETA["secondary"],
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Margen bruto: %{y:,.0f}€<extra></extra>"
    ))
    fig_ev.add_trace(go.Scatter(
        x=anual["anio"], y=anual["margen_pct"],
        name="Margen %", mode="lines+markers",
        yaxis="y2", line=dict(color=PALETA["warning"], width=2.5),
        marker=dict(size=8, color=PALETA["warning"]),
        hovertemplate="<b>%{x}</b><br>Margen: %{y:.1f}%<extra></extra>"
    ))
    fig_ev.update_layout(
        height=340, barmode="group",
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=11)),
        xaxis=dict(showgrid=False, tickvals=anual["anio"].tolist()),
        yaxis=dict(title="EUR", gridcolor="#F0F0F0",
                   tickformat=",.0f"),
        yaxis2=dict(title="Margen %", overlaying="y", side="right",
                    showgrid=False, ticksuffix="%", range=[0, 100]),
        margin=dict(t=20, b=40, l=70, r=70),
        font=dict(family="Inter, sans-serif", color="#1A1A1A")
    )
    st.plotly_chart(fig_ev, use_container_width=True, config={"displayModeBar": False})

with col_ev2:
    fig_cli = go.Figure()
    fig_cli.add_trace(go.Scatter(
        x=anual["anio"], y=anual["clientes_unicos"],
        mode="lines+markers+text",
        line=dict(color=PALETA["primary"], width=2.5),
        marker=dict(size=9, color=PALETA["primary"]),
        text=anual["clientes_unicos"].apply(lambda v: f"{v:,}"),
        textposition="top center", textfont=dict(size=10, color=PALETA["primary"]),
        fill="tozeroy", fillcolor="rgba(44,111,191,0.07)",
        hovertemplate="<b>%{x}</b><br>Clientes: %{y:,}<extra></extra>"
    ))
    fig_cli.update_layout(
        title=dict(text="Clientes únicos con compra por año", font=dict(size=12), x=0),
        height=340, showlegend=False,
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(showgrid=False, tickvals=anual["anio"].tolist()),
        yaxis=dict(gridcolor="#F0F0F0", title="Clientes únicos"),
        margin=dict(t=40, b=40, l=60, r=20),
        font=dict(family="Inter, sans-serif", color="#1A1A1A")
    )
    st.plotly_chart(fig_cli, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Evolución mensual ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Evoluci\u00f3n mensual de ingresos</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Ingresos netos mes a mes · estacionalidad y tendencia</div>', unsafe_allow_html=True)

mensual = df_v.groupby(["anio","mes"]).agg(
    ingresos_netos=("subtotal_neto","sum")
).reset_index()
mensual["periodo"] = mensual["anio"].astype(str) + "-" + mensual["mes"].astype(str).str.zfill(2)
mensual = mensual.sort_values("periodo")

fig_mens = go.Figure()
for anio_val in sorted(mensual["anio"].unique()):
    sub = mensual[mensual["anio"] == anio_val]
    fig_mens.add_trace(go.Scatter(
        x=sub["mes"], y=sub["ingresos_netos"],
        mode="lines+markers", name=str(anio_val),
        line=dict(width=2),
        marker=dict(size=6),
        hovertemplate=f"<b>{anio_val} mes %{{x}}</b><br>Ingresos: %{{y:,.0f}}€<extra></extra>"
    ))
fig_mens.update_layout(
    height=320, paper_bgcolor="white", plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(title="Mes", tickvals=list(range(1,13)),
               ticktext=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"],
               showgrid=False),
    yaxis=dict(title="Ingresos netos (EUR)", gridcolor="#F0F0F0", tickformat=",.0f"),
    margin=dict(t=20, b=50, l=80, r=20),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)
st.plotly_chart(fig_mens, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Top productos ─────────────────────────────────────────────────────────────
col_prod, col_cat = st.columns([1.2, 1])

with col_prod:
    st.markdown('<div class="section-title">Top 15 productos por ingresos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Ingresos netos acumulados 2020–2025</div>', unsafe_allow_html=True)

    top_prod = (df_v.groupby("nombre_producto")
                .agg(ingresos=("subtotal_neto","sum"), unidades=("cantidad","sum"),
                     margen=("margen_bruto","sum"))
                .reset_index().sort_values("ingresos", ascending=False).head(15))
    top_prod["margen_pct"] = top_prod["margen"] / top_prod["ingresos"] * 100

    fig_prod = go.Figure()
    fig_prod.add_trace(go.Bar(
        y=top_prod["nombre_producto"][::-1],
        x=top_prod["ingresos"][::-1],
        orientation="h",
        marker_color=PALETA["primary"], marker_line_width=0,
        text=top_prod["ingresos"][::-1].apply(lambda v: f"{v/1e3:.0f}k€"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Ingresos: %{x:,.0f}€<extra></extra>"
    ))
    fig_prod.update_layout(
        height=460, showlegend=False,
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title="Ingresos netos (EUR)", gridcolor="#F0F0F0", tickformat=",.0f"),
        yaxis=dict(showgrid=False),
        margin=dict(t=10, b=50, l=180, r=60),
        font=dict(family="Inter, sans-serif", color="#1A1A1A", size=11)
    )
    st.plotly_chart(fig_prod, use_container_width=True, config={"displayModeBar": False})

with col_cat:
    st.markdown('<div class="section-title">Ingresos por categor\u00eda</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Distribuci\u00f3n de ingresos netos por categor\u00eda de producto</div>', unsafe_allow_html=True)

    cat = (df_v.groupby("categoria")
           .agg(ingresos=("subtotal_neto","sum"), margen=("margen_bruto","sum"))
           .reset_index().sort_values("ingresos", ascending=False))
    cat["margen_pct"] = cat["margen"] / cat["ingresos"] * 100

    blues = ["#1A3A6B","#2C6FBF","#4A8FD4","#6AAEE0","#8FCAEC","#B8DEF5","#D4ECFA"]
    fig_cat = go.Figure(go.Pie(
        labels=cat["categoria"],
        values=cat["ingresos"],
        hole=0.52,
        marker=dict(colors=blues[:len(cat)]),
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>Ingresos: %{value:,.0f}€<br>%{percent}<extra></extra>"
    ))
    fig_cat.add_annotation(
        text=f"<b>{cat['ingresos'].sum()/1e6:.1f}M€</b><br><span style=\'font-size:10px\'>Total</span>",
        x=0.5, y=0.5, font=dict(size=14, color="#0D1117"),
        showarrow=False
    )
    fig_cat.update_layout(
        height=320, showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=10)),
        paper_bgcolor="white",
        margin=dict(t=10, b=10, l=10, r=120),
        font=dict(family="Inter, sans-serif", color="#1A1A1A")
    )
    st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})

    # Tabla de margen por categoría
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:0.9rem;">Margen por categor\u00eda</div>', unsafe_allow_html=True)
    rows_cat = ""
    for _, row in cat.iterrows():
        bar_w = min(int(row["margen_pct"]), 100)
        rows_cat += f"""<tr>
          <td style="padding:7px 10px;font-size:0.83rem;color:#0D1117;">{row["categoria"]}</td>
          <td style="padding:7px 10px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <div style="background:#E9ECEF;border-radius:4px;height:6px;width:80px;overflow:hidden;">
                <div style="width:{bar_w}%;height:100%;background:{PALETA["primary"]};border-radius:4px;"></div>
              </div>
              <span style="font-size:0.83rem;font-weight:700;color:{PALETA["primary"]};">{row["margen_pct"]:.1f}%</span>
            </div>
          </td>
          <td style="padding:7px 10px;font-size:0.83rem;color:#8B949E;">{row["ingresos"]/1e3:,.0f}k€</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="border-bottom:2px solid #E9ECEF;">
        <th style="padding:7px 10px;text-align:left;font-size:0.70rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.8px;">Categoría</th>
        <th style="padding:7px 10px;text-align:left;font-size:0.70rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.8px;">Margen</th>
        <th style="padding:7px 10px;text-align:left;font-size:0.70rem;color:#8B949E;text-transform:uppercase;letter-spacing:0.8px;">Ingresos</th>
      </tr></thead>
      <tbody>{rows_cat}</tbody>
    </table>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Heatmap de estacionalidad mes × año ───────────────────────────────────────
st.markdown('<div class="section-title">Estacionalidad \u2014 Ingresos por mes y a\u00f1o</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Heatmap de ingresos netos \u00b7 detecta patrones estacionales y picos de venta</div>', unsafe_allow_html=True)

pivot_est = (df_v.groupby(["anio","mes"])["subtotal_neto"].sum()
             .reset_index()
             .pivot(index="anio", columns="mes", values="subtotal_neto")
             .fillna(0))

meses_labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
col_labels = [meses_labels[c-1] for c in pivot_est.columns]

fig_est = go.Figure(go.Heatmap(
    z=pivot_est.values,
    x=col_labels,
    y=pivot_est.index.astype(str).tolist(),
    colorscale=[[0,"#EBF3FF"],[0.4,"#7AAEE8"],[1,"#1A3A6B"]],
    text=[[f"{v/1e3:.0f}k€" if v > 0 else "—" for v in row] for row in pivot_est.values],
    texttemplate="%{text}",
    textfont=dict(size=11, color="white"),
    showscale=True,
    colorbar=dict(title=dict(text="EUR", font=dict(size=11)), tickformat=",.0f"),
    hovertemplate="<b>%{y} · %{x}</b><br>Ingresos: %{z:,.0f}€<extra></extra>"
))
fig_est.update_layout(
    height=280,
    paper_bgcolor="white", plot_bgcolor="white",
    xaxis=dict(title="Mes", side="bottom"),
    yaxis=dict(title="Año", autorange="reversed"),
    margin=dict(t=10, b=50, l=60, r=80),
    font=dict(family="Inter, sans-serif", color="#1A1A1A")
)
st.plotly_chart(fig_est, use_container_width=True, config={"displayModeBar": False})

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabla resumen de cohorts ───────────────────────────────────────────────────
st.markdown('<div class="section-title">Resumen de cohortes de clientes</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">M\u00e9tricas clave por a\u00f1o de primera compra \u00b7 CLTV, AOV, pedidos y antig\u00fcedad media</div>', unsafe_allow_html=True)

df_c2 = df_c.copy()
df_c2["anio_primera_compra"] = pd.to_datetime(df_c2["primera_compra"]).dt.year

cohort_tabla = df_c2.groupby("anio_primera_compra").agg(
    clientes        = ("cliente_sk",       "count"),
    cltv_medio      = ("cltv",             "mean"),
    cltv_total      = ("cltv",             "sum"),
    aov_medio       = ("aov",              "mean"),
    pedidos_medio   = ("num_ventas",       "mean"),
    antiguedad_media= ("antiguedad_dias",  "mean"),
    rr_medio        = ("return_rate",      "mean"),
).reset_index().sort_values("anio_primera_compra")

cltv_max = cohort_tabla["cltv_medio"].max()

rows_coh = ""
for _, row in cohort_tabla.iterrows():
    bar_w   = max(int(row["cltv_medio"] / cltv_max * 100), 2)
    anio    = int(row["anio_primera_compra"])
    color   = PALETA["primary"] if anio <= 2021 else PALETA["neutral"]
    badge   = f'<span style="background:{color}22;color:{color};padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:700;">{anio}</span>'
    rows_coh += f"""<tr style="border-bottom:1px solid #F0F0F0;">
      <td style="padding:10px 14px;">{badge}</td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#0D1117;font-weight:600;">{int(row["clientes"]):,}</td>
      <td style="padding:10px 14px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="background:#E9ECEF;border-radius:4px;height:6px;width:90px;overflow:hidden;">
            <div style="width:{bar_w}%;height:100%;background:{color};border-radius:4px;"></div>
          </div>
          <span style="font-size:0.85rem;font-weight:700;color:{color};">{row["cltv_medio"]:,.0f}€</span>
        </div>
      </td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#6C757D;">{row["cltv_total"]/1e3:,.0f}k€</td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#6C757D;">{row["aov_medio"]:,.0f}€</td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#6C757D;">{row["pedidos_medio"]:.1f}</td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#6C757D;">{row["antiguedad_media"]:.0f}d</td>
      <td style="padding:10px 14px;font-size:0.85rem;color:#6C757D;">{row["rr_medio"]:.1f}%</td>
    </tr>"""

headers = ["Cohorte","Clientes","CLTV medio","CLTV total","AOV","Pedidos","Antigüedad","Return Rate"]
th = "".join(
    f'<th style="padding:10px 14px;text-align:left;font-size:0.70rem;color:#8B949E;'
    f'font-weight:600;text-transform:uppercase;letter-spacing:0.8px;'
    f'background:#F8F9FA;border-bottom:2px solid #E9ECEF;">{h}</th>'
    for h in headers
)

st.markdown(f"""
<div style="border-radius:12px;border:1px solid #E9ECEF;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.04);">
  <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;">
    <thead><tr>{th}</tr></thead>
    <tbody>{rows_coh}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)