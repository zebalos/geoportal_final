"""
app.py — Geoportal · Potencial de Restauração em Terras Indígenas de Rondônia
Ecoporé · Projeto Tawi

Deploy: Streamlit Community Cloud
"""

import json, sys, base64
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import folium
import branca.colormap as cm
from folium.features import GeoJsonTooltip
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from config import PROC, STATS, CORES

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Geoportal TIs · Rondônia",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

[data-testid="stSidebar"] {
  background-color: #0b1a0e;
  border-right: 1px solid #1f3d25;
}
[data-testid="stSidebar"] * { color: #c8e6c9 !important; }
[data-testid="stSidebar"] .stSelectbox label {
  font-size: 0.72rem; letter-spacing: 0.07em;
  text-transform: uppercase; color: #5a9464 !important;
}

.kpi-card {
  background: linear-gradient(160deg, #0d2312 0%, #122918 100%);
  border: 1px solid #244d2c; border-radius: 12px;
  padding: 16px 20px 14px; height: 108px;
  display: flex; flex-direction: column; justify-content: space-between;
}
.kpi-label { font-size: 0.68rem; letter-spacing: 0.09em; text-transform: uppercase; color: #5a9464; font-weight: 600; }
.kpi-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.65rem; font-weight: 500; line-height: 1; }
.kpi-unit  { font-size: 0.85rem; font-weight: 300; color: #7dc487; margin-left: 3px; }

.sec-header {
  font-size: 0.65rem; letter-spacing: 0.13em; text-transform: uppercase;
  color: #3d6b43; font-weight: 700; margin-bottom: 8px;
  border-bottom: 1px solid #1f3d25; padding-bottom: 5px;
}
.block-container { padding-top: 1.4rem; padding-bottom: 0.5rem; }
.badge { background:#3b1500; border:1px solid #8f3a00; color:#f4934a;
         font-size:0.68rem; font-weight:700; letter-spacing:0.06em;
         text-transform:uppercase; padding:3px 9px; border-radius:4px;
         display:inline-block; margin-top:6px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DADOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_tis():
    return gpd.read_file(PROC["tis_4326"])

@st.cache_data
def load_estado():
    return gpd.read_file(PROC["estado_4326"])

@st.cache_data
def load_stats():
    return pd.read_csv(STATS["por_ti"])

@st.cache_data
def load_kpis():
    with open(STATS["kpis"], encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_overlays():
    """Carrega PNGs como base64. Retorna None se ainda não gerados."""
    if not PROC["overlay_bounds"].exists():
        return None
    with open(PROC["overlay_bounds"]) as f:
        bounds = json.load(f)
    def b64(p):
        if not p.exists(): return None
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return {
        "fs"    : b64(PROC["overlay_fs"]),
        "pot"   : b64(PROC["overlay_pot"]),
        "bounds": bounds,
    }

gdf_tis    = load_tis()
gdf_estado = load_estado()
df_stats   = load_stats()
kpis       = load_kpis()
overlays   = load_overlays()

# Mesclar stats no GeoDataFrame
gdf_tis = gdf_tis.merge(
    df_stats[["nome_ti","veg_secundaria_ha","potencial_rn_ha","total_restauravel_ha"]],
    left_on="terrai_nom", right_on="nome_ti", how="left",
).fillna({"veg_secundaria_ha":0,"potencial_rn_ha":0,"total_restauravel_ha":0})


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='padding:8px 0 18px'>
      <div style='font-size:1.2rem;font-weight:700;color:#e8f5e9;
                  letter-spacing:-0.02em;line-height:1.3'>
        Levantamento de áreas passíveis de restauração em
        <span style='color:#7dc487'> Terras Indígenas</span>
      </div>
      <div style='font-size:0.74rem;color:#3d6b43;margin-top:6px'>Rondônia</div>
      <div class='badge'>⚠ Dados Preliminares</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="sec-header">Terra Indígena</div>', unsafe_allow_html=True)
    opcoes_ti = ["Todas as TIs"] + sorted(gdf_tis["terrai_nom"].dropna().unique().tolist())
    ti_sel = st.selectbox("TI", opcoes_ti, label_visibility="collapsed")

    st.markdown('<div class="sec-header" style="margin-top:14px">Município</div>',
                unsafe_allow_html=True)
    municipios = ["Todos"] + sorted(
        gdf_tis["municipio_"].dropna().str.strip().unique().tolist()
    )
    mun_sel = st.selectbox("Município", municipios, label_visibility="collapsed")

    st.markdown("---")

    st.markdown('<div class="sec-header">Legenda</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:0.8rem;line-height:2.3'>
      <span style='display:inline-block;width:13px;height:13px;
            background:{CORES["veg_secundaria"]};border-radius:3px;
            vertical-align:middle;margin-right:8px'></span>Vegetação secundária<br>
      <span style='display:inline-block;width:13px;height:13px;
            background:{CORES["potencial_rn"]};border-radius:3px;
            vertical-align:middle;margin-right:8px'></span>Potencial de restauração<br>
      <span style='display:inline-block;width:13px;height:13px;
            background:{CORES["ti_borda"]};border-radius:3px;
            vertical-align:middle;margin-right:8px'></span>Terra Indígena
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.67rem;color:#2d5233;line-height:1.8'>"
        "Fonte: MapBiomas Rondônia 2024<br>FUNAI · Ecoporé<br>Versão: maio/2026"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FILTRAGEM
# ══════════════════════════════════════════════════════════════════════════════

gdf_f = gdf_tis.copy()
df_f  = df_stats.copy()

if ti_sel != "Todas as TIs":
    gdf_f = gdf_f[gdf_f["terrai_nom"] == ti_sel]
    df_f  = df_f[df_f["nome_ti"]      == ti_sel]

if mun_sel != "Todos":
    gdf_f = gdf_f[gdf_f["municipio_"].str.strip() == mun_sel]
    df_f  = df_f[df_f["nome_ti"].isin(gdf_f["terrai_nom"])]

kpi_fs   = df_f["veg_secundaria_ha"].sum()
kpi_pot  = df_f["potencial_rn_ha"].sum()
kpi_tot  = df_f["total_restauravel_ha"].sum()
kpi_ntis = len(df_f)


# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════

c1, c2, c3, c4 = st.columns(4)

def kpi_card(col, icon, label, value, unit="ha", color="#7dc487"):
    val_str = f"{int(value):,}" if unit == "" else f"{value:,.1f}"
    unit_html = f"<span class='kpi-unit'>{unit}</span>" if unit else ""
    col.markdown(f"""
    <div class='kpi-card'>
      <div style='font-size:1rem'>{icon}</div>
      <div>
        <div class='kpi-value' style='color:{color}'>{val_str}{unit_html}</div>
        <div class='kpi-label'>{label}</div>
      </div>
    </div>""", unsafe_allow_html=True)

kpi_card(c1, "🌿", "Vegetação Secundária",    kpi_fs,   color="#d4f5d8")
kpi_card(c2, "🌱", "Potencial de Restauração", kpi_pot,  color="#ffd97d")
kpi_card(c3, "🌳", "Total Restaurável",        kpi_tot,  color="#7dc487")
kpi_card(c4, "🗺️",  "Terras Indígenas",        kpi_ntis, unit="",  color="#7dc487")

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAPA + TABELA
# ══════════════════════════════════════════════════════════════════════════════

col_mapa, col_tab = st.columns([6, 4], gap="medium")

with col_mapa:
    st.markdown('<div class="sec-header">Mapa</div>', unsafe_allow_html=True)

    if len(gdf_f) > 0:
        b      = gdf_f.total_bounds
        center = [(b[1]+b[3])/2, (b[0]+b[2])/2]
        zoom   = 7 if ti_sel == "Todas as TIs" else 9
    else:
        center, zoom = [-10.9, -63.3], 7

    m = folium.Map(location=center, zoom_start=zoom,
                   tiles="CartoDB dark_matter", control_scale=True)

    # Contorno do estado
    folium.GeoJson(
        gdf_estado.__geo_interface__,
        name="Estado de Rondônia",
        style_function=lambda _: {
            "fillColor":"transparent","color":"#3d6b43",
            "weight":1.5,"dashArray":"6 4"},
    ).add_to(m)

    # ── Overlays raster ───────────────────────────────────────────────────────
    if overlays:
        bd = overlays["bounds"]

        if overlays["fs"]:
            bf = bd["floresta_secundaria"]
            folium.raster_layers.ImageOverlay(
                image   = overlays["fs"],
                bounds  = [[bf["miny"], bf["minx"]], [bf["maxy"], bf["maxx"]]],
                opacity = 0.85,
                name    = "Vegetação Secundária",
                show    = True,
            ).add_to(m)

        if overlays["pot"]:
            bp = bd["potencial_rn"]
            folium.raster_layers.ImageOverlay(
                image   = overlays["pot"],
                bounds  = [[bp["miny"], bp["minx"]], [bp["maxy"], bp["maxx"]]],
                opacity = 0.80,
                name    = "Potencial de Restauração",
                show    = True,
            ).add_to(m)

    # ── TIs (contorno + choropleth) ───────────────────────────────────────────
    vmax     = max(float(gdf_f["total_restauravel_ha"].max()), 1.0)
    colormap = cm.LinearColormap(
        colors=["#0d2312","#1f4d28","#2d6a4f","#52b788","#d4f5d8"],
        vmin=0, vmax=vmax, caption="Total restaurável (ha)")

    folium.GeoJson(
        gdf_f.__geo_interface__,
        name="Terras Indígenas",
        style_function=lambda feat: {
            "fillColor"  : colormap(feat["properties"].get("total_restauravel_ha") or 0),
            "fillOpacity": 0.45,
            "color"      : CORES["ti_borda"],
            "weight"     : 2.0,
        },
        highlight_function=lambda _: {
            "fillOpacity":0.75, "weight":3, "color":"#e8f5e9"},
        tooltip=GeoJsonTooltip(
            fields  = ["terrai_nom","etnia_nome","fase_ti",
                       "veg_secundaria_ha","potencial_rn_ha","total_restauravel_ha"],
            aliases = ["Terra Indígena","Etnia","Fase",
                       "Veg. Sec. (ha)","Potencial RN (ha)","Total (ha)"],
            localize=True, sticky=True,
            style=("font-family:'IBM Plex Sans',sans-serif;font-size:12px;"
                   "background:#0b1a0e;color:#c8e6c9;"
                   "border:1px solid #1f3d25;border-radius:6px;padding:8px;"),
        ),
    ).add_to(m)

    colormap.add_to(m)
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    st_folium(m, height=500, width="100%", returned_objects=[])


# ══════════════════════════════════════════════════════════════════════════════
# TABELA
# ══════════════════════════════════════════════════════════════════════════════

with col_tab:
    st.markdown('<div class="sec-header">Tabela por Terra Indígena</div>',
                unsafe_allow_html=True)

    df_exib = (
        df_f[["nome_ti","veg_secundaria_ha","potencial_rn_ha","total_restauravel_ha"]]
        .rename(columns={
            "nome_ti"              : "Terra Indígena",
            "veg_secundaria_ha"    : "Veg. Sec. (ha)",
            "potencial_rn_ha"      : "Potencial RN (ha)",
            "total_restauravel_ha" : "Total (ha)",
        })
        .sort_values("Total (ha)", ascending=False)
        .reset_index(drop=True)
    )
    for col in ["Veg. Sec. (ha)","Potencial RN (ha)","Total (ha)"]:
        df_exib[col] = df_exib[col].map(lambda x: f"{x:,.1f}")

    st.dataframe(df_exib, height=450, hide_index=True,
                 use_container_width=True)

    csv = df_stats.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇  Baixar dados completos (.csv)", csv,
        "potencial_restauracao_tis_ro.csv", "text/csv",
        use_container_width=True,
    )
