"""
scripts/00_preparar_dados.py
════════════════════════════════════════════════════════════════════════════════
PASSO 1 — Prepara vetores e rasters brutos para o geoportal.

Antes de rodar:
  Coloque os 4 arquivos em data/raw/
    ESTADO_RO.gpkg
    TERRAS_INDIGENAS_RO.gpkg
    FLORESTA_SECUNDARIA_RO.tif
    POTENCIAL_RN_RO.tif

Como rodar:
  conda activate geo_stats_env
  python scripts/00_preparar_dados.py

Instalar extras se faltar:
  pip install rio-cogeo rasterstats --break-system-packages
════════════════════════════════════════════════════════════════════════════════
"""

import sys, json, time, shutil, warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

sys.path.insert(0, str(Path(__file__).parent))
from config import RAW, PROC, STATS, DIR_PROC, DIR_STATS
from config import CRS_WEB, CRS_AREA, SIMPLIFY_ESTADO, SIMPLIFY_TIS, TILE_SIZE

warnings.filterwarnings("ignore")

try:
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles
    HAS_COGEO = True
except ImportError:
    HAS_COGEO = False
    print("⚠  rio-cogeo não encontrado — COG via rasterio nativo")

try:
    from rasterstats import zonal_stats
    HAS_ZONAL = True
except ImportError:
    HAS_ZONAL = False
    print("⚠  rasterstats não encontrado — zonal stats via rasterio nativo")

# ── Helpers ───────────────────────────────────────────────────────────────────
def sep(t): print(f"\n{'═'*68}\n  {t}\n{'═'*68}")
def fmtb(p):
    b = Path(p).stat().st_size
    for u in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

# ══════════════════════════════════════════════════════════════════════════════
sep("ETAPA 1 — DIAGNÓSTICO")
# ══════════════════════════════════════════════════════════════════════════════

for k, p in RAW.items():
    if not p.exists():
        print(f"  ✗ {p}\n    → Copie os arquivos brutos para data/raw/")
        sys.exit(1)
    print(f"  ✓ {p.name}")

def diag_v(path, label):
    gdf = gpd.read_file(path)
    print(f"\n  [{label}]  {fmtb(path)}")
    print(f"    CRS     : {gdf.crs}  |  Feições: {len(gdf)}")
    print(f"    Colunas : {list(gdf.columns)}")
    return gdf

def diag_r(path, label):
    with rasterio.open(path) as s:
        print(f"\n  [{label}]  {fmtb(path)}")
        print(f"    CRS     : {s.crs}  |  dtype: {s.dtypes[0]}")
        print(f"    Tamanho : {s.width}×{s.height}  |  NoData: {s.nodata}")
        print(f"    Res     : {abs(s.res[0]):.8f}°")

gdf_estado = diag_v(RAW["estado"], "ESTADO_RO")
gdf_tis    = diag_v(RAW["tis"],    "TERRAS_INDIGENAS_RO")
diag_r(RAW["flor_sec"],  "FLORESTA_SECUNDARIA_RO")
diag_r(RAW["potencial"], "POTENCIAL_RN_RO")

# ══════════════════════════════════════════════════════════════════════════════
sep("ETAPA 2 — VETORES → EPSG:4326")
# ══════════════════════════════════════════════════════════════════════════════

DIR_PROC.mkdir(parents=True, exist_ok=True)

def proc_vetor(gdf, saida, tol):
    out = gdf.to_crs(CRS_WEB)
    n   = (~out.is_valid).sum()
    if n: out["geometry"] = out.geometry.buffer(0)
    out["geometry"] = out.geometry.simplify(tol, preserve_topology=True)
    out = out.dropna(axis=1, how="all")
    out.to_file(saida, driver="GPKG")
    print(f"  ✓ {saida.name}  ({fmtb(saida)})")
    return out

gdf_estado_proc = proc_vetor(gdf_estado, PROC["estado_4326"], SIMPLIFY_ESTADO)
gdf_tis_proc    = proc_vetor(gdf_tis,    PROC["tis_4326"],    SIMPLIFY_TIS)
print(f"\n  Colunas TIs: {list(gdf_tis_proc.columns)}")

# ══════════════════════════════════════════════════════════════════════════════
sep("ETAPA 3 — RASTERS → EPSG:4326")
# ══════════════════════════════════════════════════════════════════════════════

def reproj(src_path, dst_path, resample):
    with rasterio.open(src_path) as s:
        if str(s.crs).upper() == CRS_WEB.upper():
            print(f"  Já em {CRS_WEB} — copiando...")
            shutil.copy2(src_path, dst_path); return
        print(f"  {src_path.name}: {s.crs} → {CRS_WEB}")
        t, w, h = calculate_default_transform(s.crs, CRS_WEB, s.width, s.height, *s.bounds)
        meta = {**s.meta, "crs": CRS_WEB, "transform": t, "width": w, "height": h}
        t0 = time.time()
        with rasterio.open(dst_path, "w", **meta) as d:
            for i in range(1, s.count+1):
                reproject(rasterio.band(s,i), rasterio.band(d,i),
                          src_crs=s.crs, dst_crs=CRS_WEB, resampling=resample)
    print(f"  ✓ {dst_path.name}  ({fmtb(dst_path)})  [{time.time()-t0:.0f}s]")

_tmp_fs  = DIR_PROC / "_tmp_fs.tif"
_tmp_pot = DIR_PROC / "_tmp_pot.tif"
reproj(RAW["flor_sec"],  _tmp_fs,  Resampling.nearest)
reproj(RAW["potencial"], _tmp_pot, Resampling.bilinear)

# ══════════════════════════════════════════════════════════════════════════════
sep("ETAPA 4 — COG")
# ══════════════════════════════════════════════════════════════════════════════

def fazer_cog(src, dst):
    print(f"\n  {Path(src).name} → {Path(dst).name}")
    if HAS_COGEO:
        try:
            cog_translate(src, dst, cog_profiles.get("deflate"),
                          overview_resampling="nearest", quiet=False)
            print(f"  ✓ ({fmtb(dst)})"); return
        except Exception as e:
            print(f"  ⚠ {e} — fallback")
    t0 = time.time()
    with rasterio.open(src) as s:
        meta = {**s.meta, "driver":"GTiff","compress":"lzw","tiled":True,
                "blockxsize":TILE_SIZE,"blockysize":TILE_SIZE,"interleave":"band"}
        with rasterio.open(dst,"w",**meta) as d:
            for i in range(1,s.count+1): d.write(s.read(i),i)
            d.build_overviews([2,4,8,16,32], Resampling.nearest)
            d.update_tags(ns="rio_overview", resampling="nearest")
    print(f"  ✓ ({fmtb(dst)})  [{time.time()-t0:.0f}s]")

fazer_cog(_tmp_fs,  PROC["flor_sec_cog"])
fazer_cog(_tmp_pot, PROC["potencial_cog"])
for t in [_tmp_fs, _tmp_pot]:
    if t.exists(): t.unlink()

# ══════════════════════════════════════════════════════════════════════════════
sep("ETAPA 5 — ZONAL STATS POR TI")
# ══════════════════════════════════════════════════════════════════════════════

DIR_STATS.mkdir(parents=True, exist_ok=True)

CANDS    = ["terrai_nom","nome","name","NOME","TI_NOME","NO_TI"]
col_nome = next((c for c in CANDS if c in gdf_tis_proc.columns), gdf_tis_proc.columns[0])
print(f"  Campo nome: '{col_nome}'")

gdf_area = gdf_tis_proc.to_crs(CRS_AREA).copy()
gdf_area["area_ti_ha"] = (gdf_area.geometry.area / 10_000).round(2)

with rasterio.open(PROC["flor_sec_cog"]) as s:
    res = abs(s.res[0])
PX_HA = (res*111_000)*(res*109_000)/10_000
print(f"  {res:.8f}° → {PX_HA:.6f} ha/pixel")

def zonal(raster, label):
    print(f"\n  {label}...")
    if HAS_ZONAL:
        st = zonal_stats(gdf_tis_proc.to_crs(CRS_WEB), str(raster),
                         stats=["count"], geojson_out=False)
        ha = pd.Series([(s["count"] or 0)*PX_HA for s in st],
                       index=gdf_tis_proc[col_nome].values, name=label).round(2)
    else:
        from rasterio.mask import mask as rmask
        vals = []
        with rasterio.open(raster) as s:
            nd = s.nodata or 0
            for _, row in gdf_tis_proc.to_crs(CRS_WEB).iterrows():
                try:
                    a, _ = rmask(s, [row.geometry.__geo_interface__], crop=True, nodata=nd)
                    vals.append(round(int(((a[0]!=nd)&(a[0]>0)).sum())*PX_HA, 2))
                except: vals.append(0.0)
        ha = pd.Series(vals, index=gdf_tis_proc[col_nome].values, name=label)
    print(f"  ✓ Total: {ha.sum():,.1f} ha  |  TIs: {(ha>0).sum()}")
    return ha

s_fs  = zonal(PROC["flor_sec_cog"],  "veg_secundaria_ha")
s_pot = zonal(PROC["potencial_cog"], "potencial_rn_ha")

df = (gdf_area[[col_nome,"area_ti_ha"]].rename(columns={col_nome:"nome_ti"})
      .set_index("nome_ti").join(s_fs.rename_axis("nome_ti"))
      .join(s_pot.rename_axis("nome_ti")).fillna(0)
      .assign(total_restauravel_ha=lambda d:(d.veg_secundaria_ha+d.potencial_rn_ha).round(2))
      .sort_values("total_restauravel_ha",ascending=False).reset_index())

df.to_csv(STATS["por_ti"], index=False, encoding="utf-8-sig")

kpis = {"veg_secundaria_total_ha": round(float(df.veg_secundaria_ha.sum()),2),
        "potencial_rn_total_ha"  : round(float(df.potencial_rn_ha.sum()),2),
        "total_restauravel_ha"   : round(float(df.total_restauravel_ha.sum()),2),
        "n_tis"                  : int(len(df)),
        "col_nome_ti"            : col_nome}
with open(STATS["kpis"],"w",encoding="utf-8") as f:
    json.dump(kpis,f,ensure_ascii=False,indent=2)

print(f"\n{df.head(8).to_string(index=False)}")

# ══════════════════════════════════════════════════════════════════════════════
sep("CONCLUÍDO")
# ══════════════════════════════════════════════════════════════════════════════
print(f"""
  Vegetação secundária : {kpis['veg_secundaria_total_ha']:>14,.1f} ha
  Potencial de RN      : {kpis['potencial_rn_total_ha']:>14,.1f} ha
  Total restaurável    : {kpis['total_restauravel_ha']:>14,.1f} ha
  Nº TIs               : {kpis['n_tis']:>14,}

  ✓ Próximo passo → python scripts/01_gerar_overlays.py
""")
