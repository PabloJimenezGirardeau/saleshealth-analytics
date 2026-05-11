"""
pages/3_Customer_360.py — Ficha individual de cliente con posicionamiento relativo.
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
    inject_css, render_sidebar, load_customer_360, get_percentil,
    PALETA, COLORES_CLUSTER, ORDEN_CLUSTERS
)

st.set_page_config(
    page_title="saleshealth | Customer 360",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()
render_sidebar("customer360")

# ── Datos ─────────────────────────────────────────────────────────────────────
df = load_customer_360()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h1>&#128269; Customer 360</h1>
  <p>Ficha individual &middot; m&#233;tricas &middot; segmento &middot; posici&#243;n relativa en la base de clientes</p>
</div>
""", unsafe_allow_html=True)

# ── Buscador ──────────────────────────────────────────────────────────────────
col_search, col_info = st.columns([2, 1])

with col_search:
    search_term = st.text_input(
        '🔍 Buscar cliente',
        placeholder='Nombre, apellido o ID numérico — ej: Alejandro o 1037',
        help='Búsqueda parcial por nombre o ID exacto'
    )

with col_info:
    st.markdown(f"""
    <div style="padding:10px 16px;background:#F8F9FA;border-radius:8px;
                border:1px solid #E9ECEF;margin-top:28px;font-size:0.82rem;color:#6C757D;">
      👥 {len(df):,} clientes disponibles ·
      CLTV rango: {df['cltv'].min():,.0f}€ – {df['cltv'].max():,.0f}€
    </div>
    """, unsafe_allow_html=True)

# ── Lógica de búsqueda ────────────────────────────────────────────────────────
cliente = None

if search_term:
    search_term = search_term.strip()
    try:
        sk      = int(search_term)
        matches = df[df['cliente_sk'] == sk]
    except ValueError:
        matches = df[df['nombre'].str.contains(search_term, case=False, na=False)]

    if len(matches) == 0:
        st.warning(f'No se encontró ningún cliente con "{search_term}". Prueba con otro nombre o ID.')
    elif len(matches) == 1:
        cliente = matches.iloc[0]
    else:
        st.markdown(f'<div style="font-size:0.85rem;color:#6C757D;margin-bottom:6px;">{len(matches)} resultados — selecciona uno:</div>', unsafe_allow_html=True)
        opciones = matches['nombre'] + ' (ID: ' + matches['cliente_sk'].astype(str) + ')'
        sel = st.selectbox('Seleccionar cliente', opciones.tolist(), label_visibility='collapsed')
        sk  = int(sel.split('ID: ')[1].rstrip(')'))
        cliente = df[df['cliente_sk'] == sk].iloc[0]

# ── Ficha de cliente ──────────────────────────────────────────────────────────
if cliente is not None:
    color  = COLORES_CLUSTER.get(cliente.get('cluster_label', ''), PALETA['neutral'])
    pct_cltv, val_cltv = get_percentil(df, cliente['cliente_sk'], 'cltv')
    pct_aov, _         = get_percentil(df, cliente['cliente_sk'], 'aov')
    top_pct            = round(100 - pct_cltv, 1)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cabecera de la ficha ──────────────────────────────────────────────────
    st.markdown(f"""
    <div class="customer-card" style="border-top:4px solid {color};">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
        <div>
          <div class="customer-name">{cliente['nombre']}</div>
          <div class="customer-id">ID: {cliente['cliente_sk']} · Cliente desde {str(cliente['primera_compra'])[:10]}</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="background:{color}22;color:{color};padding:5px 16px;
                 border-radius:20px;font-size:0.88rem;font-weight:700;">
            {cliente.get('cluster_label','—')}
          </span>
          <div style="text-align:right;">
            <div style="font-size:0.72rem;color:#6C757D;text-transform:uppercase;letter-spacing:0.5px;">Top</div>
            <div style="font-size:1.5rem;font-weight:800;color:{color};">{top_pct}%</div>
            <div style="font-size:0.72rem;color:#6C757D;">por CLTV</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPIs del cliente ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def kpi_mini(col, label, value, delta=""):
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="min-height:80px;padding:14px 16px;">
              <div class="kpi-label">{label}</div>
              <div style="font-size:1.35rem;font-weight:700;color:#1A1A1A;">{value}</div>
              {'<div class="kpi-delta">' + delta + '</div>' if delta else ''}
            </div>
            """, unsafe_allow_html=True)

    kpi_mini(c1, 'CLTV', f'{cliente["cltv"]:,.0f}€', f'Top {top_pct}% de clientes')
    kpi_mini(c2, 'AOV', f'{cliente["aov"]:,.0f}€', f'Percentil {pct_aov:.0f}')
    kpi_mini(c3, 'Pedidos', f'{int(cliente["num_ventas"])}', f'{int(cliente["num_lineas"])} líneas')
    kpi_mini(c4, 'Return Rate', f'{cliente["return_rate"]:.1f}%',
             '✓ Bajo' if cliente['return_rate'] < 10 else '⚠ Alto')
    kpi_mini(c5, 'Recencia', f'{int(cliente["recencia_dias"])}d',
             'Compra reciente' if cliente['recencia_dias'] < 180 else 'Inactivo')
    antig_val = int(cliente["antiguedad_dias"])
    antig_label = f'{antig_val}d' if antig_val > 0 else 'Primera compra única'
    antig_sub   = f'Desde {str(cliente["primera_compra"])[:7]}' if antig_val > 0 else 'Solo 1 visita registrada'
    kpi_mini(c6, 'Antigüedad', antig_label, antig_sub)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gráficas de posicionamiento ───────────────────────────────────────────
    col_hist, col_spider = st.columns([1.3, 1])

    with col_hist:
        st.markdown('<div class="section-title">Posición relativa en CLTV</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-sub">Este cliente está en el top {top_pct}% · percentil {pct_cltv:.0f}</div>', unsafe_allow_html=True)

        cltv_clip = df['cltv'].clip(upper=df['cltv'].quantile(0.95))
        val_clip  = min(cliente['cltv'], df['cltv'].quantile(0.95))

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=cltv_clip,
            nbinsx=60,
            name='Todos los clientes',
            marker_color='#E9ECEF',
            hovertemplate='CLTV ~%{x:,.0f}€: %{y} clientes<extra></extra>'
        ))
        fig_hist.add_vline(
            x=val_clip,
            line_color=color, line_width=2.5, line_dash='dash',
        )
        fig_hist.add_annotation(
            x=val_clip,
            yref='paper', y=0.95,
            text=f"<b>{cliente['nombre'].split()[0]}</b><br>{cliente['cltv']:,.0f}€",
            showarrow=True, arrowhead=2, arrowcolor=color,
            font=dict(size=11, color=color),
            bgcolor='white', bordercolor=color, borderwidth=1,
            ax=40, ay=-30
        )
        fig_hist.update_layout(
            height=300, showlegend=False,
            paper_bgcolor='white', plot_bgcolor='white',
            xaxis=dict(title='CLTV (EUR) — excluye top 5% outliers',
                       gridcolor='#F0F0F0'),
            yaxis=dict(title='Nº clientes', gridcolor='#F0F0F0'),
            margin=dict(t=10, b=50, l=60, r=20),
            font=dict(family='Inter, sans-serif', color='#1A1A1A')
        )
        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})

    with col_spider:
        st.markdown('<div class="section-title">Perfil vs segmento</div>', unsafe_allow_html=True)
        seg_label  = cliente.get('cluster_label', 'Base')
        seg_means  = df[df['cluster_label'] == seg_label][
            ['cltv','aov','num_ventas','antiguedad_dias','frecuencia_mensual','return_rate']].mean()
        all_max    = df[['cltv','aov','num_ventas','antiguedad_dias','frecuencia_mensual','return_rate']].max()
        all_min    = df[['cltv','aov','num_ventas','antiguedad_dias','frecuencia_mensual','return_rate']].min()
        # Decidir si usar radar o tabla según si el cliente tiene valores suficientemente variados
        c_norm_sum = sum(abs((cliente[c] - all_min[c]) / (all_max[c] - all_min[c] + 1e-9))
                        for c in ['cltv','aov','num_ventas'])
        use_radar = c_norm_sum > 0.15  # cliente con suficiente varianza
        if use_radar:
            st.markdown('<div class="section-sub">Cliente vs media del segmento (normalizado)</div>', unsafe_allow_html=True)
            COLS_R   = ['cltv','aov','num_ventas','antiguedad_dias','frecuencia_mensual']
            LABELS_R = ['CLTV','AOV','Pedidos','Antigüedad','Frecuencia']
            all_max2 = df[COLS_R].max(); all_min2 = df[COLS_R].min()
            def norm2(vals):
                return [(v - all_min2[c]) / (all_max2[c] - all_min2[c] + 1e-9) for c, v in zip(COLS_R, vals)]
            c_vals = norm2([cliente[c] for c in COLS_R])
            s_vals = norm2(df[df['cluster_label']==seg_label][COLS_R].mean().values)
            def polar_trace(vals, name, col_r, dash=False):
                r = vals + vals[:1]; t = LABELS_R + [LABELS_R[0]]
                return go.Scatterpolar(
                    r=r, theta=t, name=name,
                    line=dict(color=col_r, width=2, dash='dot' if dash else 'solid'),
                    fill='toself' if not dash else 'none',
                    fillcolor=col_r if not dash else 'rgba(0,0,0,0)',
                    opacity=0.2 if not dash else 1)
            fig_sp = go.Figure([
                polar_trace(s_vals, f'Media {seg_label}', '#BBBBBB', dash=True),
                polar_trace(c_vals, cliente['nombre'].split()[0], color),
            ])
            fig_sp.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0,1], tickfont=dict(size=8, color='#999'), gridcolor='#E9ECEF'),
                    angularaxis=dict(tickfont=dict(size=10), gridcolor='#E9ECEF'), bgcolor='white'),
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=-0.2, font=dict(size=10)),
                paper_bgcolor='white', height=300,
                margin=dict(t=10, b=60, l=30, r=30),
                font=dict(family='Inter, sans-serif')
            )
            st.plotly_chart(fig_sp, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown('<div class="section-sub">Comparativa directa con la media del segmento</div>', unsafe_allow_html=True)
            COMP_COLS   = ['cltv','aov','num_ventas','recencia_dias','return_rate','antiguedad_dias']
            COMP_LABELS = ['CLTV','AOV','Pedidos','Recencia (d)','Return Rate (%)','Antigüedad (d)']
            rows_cmp = ""
            for col_k, lbl in zip(COMP_COLS, COMP_LABELS):
                c_val  = cliente[col_k]
                s_val  = seg_means[col_k] if col_k in seg_means.index else 0
                diff   = c_val - s_val
                diff_color = color if abs(diff) < s_val * 0.5 else ('#27A06B' if diff > 0 else '#E57373')
                rows_cmp += f"""<tr>
                  <td style="padding:8px 12px;color:#6C757D;font-size:0.82rem;">{lbl}</td>
                  <td style="padding:8px 12px;font-weight:700;color:#0D1117;">{c_val:,.1f}</td>
                  <td style="padding:8px 12px;color:#8B949E;">{s_val:,.1f}</td>
                  <td style="padding:8px 12px;color:{diff_color};font-weight:600;">{"+" if diff>=0 else ""}{diff:,.1f}</td>
                </tr>"""
            st.markdown(f"""
            <div style="border-radius:10px;border:1px solid #E9ECEF;overflow:hidden;margin-top:4px;">
              <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <thead><tr style="background:#F8F9FA;border-bottom:2px solid #E9ECEF;">
                  <th style="padding:9px 12px;text-align:left;color:#8B949E;font-size:0.70rem;text-transform:uppercase;letter-spacing:0.8px;">Métrica</th>
                  <th style="padding:9px 12px;text-align:left;color:#8B949E;font-size:0.70rem;text-transform:uppercase;letter-spacing:0.8px;">Cliente</th>
                  <th style="padding:9px 12px;text-align:left;color:#8B949E;font-size:0.70rem;text-transform:uppercase;letter-spacing:0.8px;">Media {seg_label}</th>
                  <th style="padding:9px 12px;text-align:left;color:#8B949E;font-size:0.70rem;text-transform:uppercase;letter-spacing:0.8px;">Diferencia</th>
                </tr></thead>
                <tbody>{rows_cmp}</tbody>
              </table>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detalle financiero ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Detalle financiero</div>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    def fin_card(col, label, value, sub="", color_val="#1A1A1A"):
        with col:
            st.markdown(f"""
            <div style="background:#F8F9FA;border-radius:10px;padding:14px 16px;border:1px solid #E9ECEF;">
              <div style="font-size:0.70rem;color:#6C757D;text-transform:uppercase;
                          letter-spacing:0.5px;margin-bottom:5px;">{label}</div>
              <div style="font-size:1.1rem;font-weight:700;color:{color_val};">{value}</div>
              {'<div style="font-size:0.77rem;color:#6C757D;margin-top:3px;">' + sub + '</div>' if sub else ''}
            </div>
            """, unsafe_allow_html=True)

    fin_card(col_f1, 'Ingresos brutos', f'{cliente["ingresos_brutos"]:,.2f}€')
    fin_card(col_f2, 'Ingresos netos', f'{cliente["ingresos_netos"]:,.2f}€',
             sub=f'Devoluciones: {cliente["ingresos_brutos"]-cliente["ingresos_netos"]:,.2f}€')
    fin_card(col_f3, 'Coste total', f'{cliente["coste_total"]:,.2f}€')
    margen_color = PALETA['secondary'] if cliente['margen_pct_medio'] > 30 else PALETA['warning']
    fin_card(col_f4, 'Margen bruto', f'{cliente["margen_bruto"]:,.2f}€',
             sub=f'{cliente["margen_pct_medio"]:.1f}% sobre ingresos brutos',
             color_val=margen_color)

else:
    # Estado vacío — invitación a buscar
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#6C757D;">
      <div style="font-size:3rem;margin-bottom:16px;">🔍</div>
      <div style="font-size:1.1rem;font-weight:600;color:#1A1A1A;margin-bottom:8px;">
        Busca un cliente para ver su ficha completa
      </div>
      <div style="font-size:0.88rem;">
        Escribe un nombre parcial o el ID numérico en el campo de búsqueda
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Preview de top 5 como sugerencia
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="text-align:center;">Top 5 clientes por CLTV</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub" style="text-align:center;">Haz clic en un nombre para buscarlo</div>', unsafe_allow_html=True)

    top5 = df.head(5)
    cols_top = st.columns(5)
    for col, (_, row) in zip(cols_top, top5.iterrows()):
        color = COLORES_CLUSTER.get(row.get('cluster_label', ''), PALETA['neutral'])
        with col:
            st.markdown(f"""
            <div style="background:white;border-radius:10px;padding:14px;
                        border:1px solid #E9ECEF;text-align:center;
                        border-top:3px solid {color};">
              <div style="font-size:0.82rem;font-weight:600;color:#1A1A1A;margin-bottom:6px;">
                {row['nombre'].split()[0]} {row['nombre'].split()[-1] if len(row['nombre'].split())>1 else ''}
              </div>
              <div style="font-size:1.0rem;font-weight:700;color:{color};">
                {row['cltv']:,.0f}€
              </div>
              <div style="font-size:0.72rem;color:#6C757D;margin-top:4px;">ID: {row['cliente_sk']}</div>
            </div>
            """, unsafe_allow_html=True)