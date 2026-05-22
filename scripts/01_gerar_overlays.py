"""
scripts/01_gerar_overlays.py
════════════════════════════════════════════════════════════════════════════════
PASSO 2 — Gera PNGs RGBA dos rasters recortados pelas TIs para exibição no mapa.

Rodar APÓS 00_preparar_dados.py:
  conda activate geo_stats_env
  python scripts/01_gerar_overlays.py

Instalar extras se faltar:
  pip install matplotlib Pillow --break-system-packages

Saída em data/processado/:
  OVERLAY_FLORESTA.png    ← floresta secundária em bordeaux, resto transparente
  OVERLAY_POTENCIAL.png   ← potencial RN em colormap YlOrBr, resto transparente
  overlay_bounds.json     ← bounds lat/lon para posicionar no mapa Folium
════════════════════════════════════════════════════════════════════════════════
"""

import sys, json, warnings
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rio_mask
from PIL import Image
from matplotlib import cm as mpl_cm
from matplotlib.colors import Normalize

sys.path.insert(0, str(Path(__file__).parent))
from config import PROC, OVERLAY_SCALE, CORES

warnings.filterwarnings("ignore")

# ── Helpers ───────────────────────────────────────────────────────────────────
def sep(t): print(f"\n{'═'*60}\n  {t}\n{'═'*60}")
def fmtb(p):
    kb = Path(p).stat().st_size / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"

def recortar(raster_path, gdf):
    """Recorta raster pela união de todas as TIs."""
    try:
        uniao = [gdf.union_all().__geo_interface__]       # geopandas >= 0.14
    except AttributeError:
        uniao = [gdf.unary_union.__geo_interface__]        # fallback

    with rasterio.open(raster_path) as src:
        arr, transform = rio_mask(src, uniao, crop=True,
                                  nodata=src.nodata or 0, filled=True)
        nodata = src.nodata or 0
        bounds = rasterio.transform.array_bounds(
            arr.shape[1], arr.shape[2], transform)         # minx,miny,maxx,maxy
    return arr[0].astype(np.float32), nodata, bounds

def downscale(arr, factor):
    """Reduz resolução pelo fator (0.25 = 25%)."""
    h = max(1, int(arr.shape[0] * factor))
    w = max(1, int(arr.shape[1] * factor))
    img = Image.fromarray(arr).resize((w, h), Image.NEAREST)
    return np.array(img)

def salvar_png(rgba, path):
    Image.fromarray(rgba, mode="RGBA").save(path, optimize=True, compress_level=9)
    print(f"  ✓ {Path(path).name}  ({fmtb(path)})")

# ══════════════════════════════════════════════════════════════════════════════
sep("Carregando TIs")
# ══════════════════════════════════════════════════════════════════════════════

gdf_tis = gpd.read_file(PROC["tis_4326"])
print(f"  {len(gdf_tis)} TIs  |  CRS: {gdf_tis.crs}")

bounds_out = {}

# ══════════════════════════════════════════════════════════════════════════════
sep("OVERLAY 1 — Floresta Secundária")
# ══════════════════════════════════════════════════════════════════════════════

arr_fs, nd_fs, bounds_fs = recortar(PROC["flor_sec_cog"], gdf_tis)
print(f"  Shape original  : {arr_fs.shape}")

arr_fs_ds = downscale(arr_fs, OVERLAY_SCALE)
print(f"  Shape reduzido  : {arr_fs_ds.shape}")
print(f"  Pixels válidos  : {(arr_fs_ds > 0).sum():,}")

# Cor única: bordeaux #8B1A2E
r, g, b = int(CORES["veg_secundaria"][1:3],16), \
          int(CORES["veg_secundaria"][3:5],16), \
          int(CORES["veg_secundaria"][5:7],16)

rgba_fs         = np.zeros((*arr_fs_ds.shape, 4), dtype=np.uint8)
valido          = arr_fs_ds > 0
rgba_fs[valido] = [r, g, b, 210]

salvar_png(rgba_fs, PROC["overlay_fs"])
bounds_out["floresta_secundaria"] = {
    "minx":bounds_fs[0], "miny":bounds_fs[1],
    "maxx":bounds_fs[2], "maxy":bounds_fs[3]}

# ══════════════════════════════════════════════════════════════════════════════
sep("OVERLAY 2 — Potencial de Restauração")
# ══════════════════════════════════════════════════════════════════════════════

arr_pot, nd_pot, bounds_pot = recortar(PROC["potencial_cog"], gdf_tis)
print(f"  Shape original  : {arr_pot.shape}")

arr_pot_ds = downscale(arr_pot, OVERLAY_SCALE)
print(f"  Shape reduzido  : {arr_pot_ds.shape}")

valido_pot = (arr_pot_ds > 0) & (~np.isnan(arr_pot_ds))
if valido_pot.any():
    vmin = float(arr_pot_ds[valido_pot].min())
    vmax = float(np.percentile(arr_pot_ds[valido_pot], 98))
    print(f"  Valores         : {vmin:.4f} – {vmax:.4f}")
else:
    vmin, vmax = 0.0, 1.0

norm    = Normalize(vmin=vmin, vmax=vmax, clip=True)
cmap    = mpl_cm.get_cmap("YlOrBr")
mapped  = cmap(norm(arr_pot_ds))              # float RGBA 0-1
rgba_pot = (mapped * 255).astype(np.uint8)
rgba_pot[~valido_pot, 3] = 0                   # fora das TIs → transparente
rgba_pot[valido_pot,  3] = 200

salvar_png(rgba_pot, PROC["overlay_pot"])
bounds_out["potencial_rn"] = {
    "minx":bounds_pot[0], "miny":bounds_pot[1],
    "maxx":bounds_pot[2], "maxy":bounds_pot[3]}

# ══════════════════════════════════════════════════════════════════════════════
sep("Salvando bounds")
# ══════════════════════════════════════════════════════════════════════════════

with open(PROC["overlay_bounds"], "w", encoding="utf-8") as f:
    json.dump(bounds_out, f, indent=2)
print(f"  ✓ overlay_bounds.json")

# ══════════════════════════════════════════════════════════════════════════════
sep("CONCLUÍDO")
# ══════════════════════════════════════════════════════════════════════════════
print("""
  Arquivos gerados em data/processado/:
    OVERLAY_FLORESTA.png
    OVERLAY_POTENCIAL.png
    overlay_bounds.json

  Próximo passo:
    git add data/processado/ data/estatisticas/
    git commit -m "dados processados e overlays"
    git push
""")
