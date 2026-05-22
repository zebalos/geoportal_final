"""
scripts/config.py
Caminhos e constantes centralizados. Importado por todos os scripts e pelo app.
"""

from pathlib import Path

ROOT      = Path(__file__).parent.parent   # raiz do repositório
DIR_RAW   = ROOT / "data" / "raw"
DIR_PROC  = ROOT / "data" / "processado"
DIR_STATS = ROOT / "data" / "estatisticas"

# ── Entradas brutas ───────────────────────────────────────────────────────────
RAW = {
    "estado"   : DIR_RAW / "ESTADO_RO.gpkg",
    "tis"      : DIR_RAW / "TERRAS_INDIGENAS_RO.gpkg",
    "flor_sec" : DIR_RAW / "FLORESTA_SECUNDARIA_RO.tif",
    "potencial": DIR_RAW / "POTENCIAL_RN_RO.tif",
}

# ── Saídas processadas ────────────────────────────────────────────────────────
PROC = {
    "estado_4326"    : DIR_PROC / "ESTADO_RO_4326.gpkg",
    "tis_4326"       : DIR_PROC / "TIS_RO_4326.gpkg",
    "flor_sec_cog"   : DIR_PROC / "FLORESTA_SECUNDARIA_COG.tif",
    "potencial_cog"  : DIR_PROC / "POTENCIAL_RN_COG.tif",
    "overlay_fs"     : DIR_PROC / "OVERLAY_FLORESTA.png",
    "overlay_pot"    : DIR_PROC / "OVERLAY_POTENCIAL.png",
    "overlay_bounds" : DIR_PROC / "overlay_bounds.json",
}

STATS = {
    "por_ti" : DIR_STATS / "stats_por_ti.csv",
    "kpis"   : DIR_STATS / "kpis_globais.json",
}

# ── Referências espaciais ─────────────────────────────────────────────────────
CRS_WEB  = "EPSG:4326"
CRS_AREA = "EPSG:5880"   # Policônico IBGE — área em m²

# ── Processamento ─────────────────────────────────────────────────────────────
SIMPLIFY_ESTADO = 0.0005
SIMPLIFY_TIS    = 0.0001
TILE_SIZE       = 512
OVERLAY_SCALE   = 0.25   # fração de downscale para os PNGs (0.25 = 25% do original)

# ── Paleta ────────────────────────────────────────────────────────────────────
CORES = {
    "veg_secundaria" : "#8B1A2E",
    "potencial_rn"   : "#D4A017",
    "ti_borda"       : "#2D6A4F",
    "ti_fill"        : "#B7E4C7",
}
