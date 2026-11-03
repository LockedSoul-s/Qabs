#!/usr/bin/env python3
"""QABS dashboard data prep: GeoTIFF -> WGS84 PNG overlays + JSON data bundle.
Reads existing deliverables (download/) and geo/out intermediates; writes to public/.
Does NOT modify any existing file."""
import json, os, shutil
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import Affine
from PIL import Image

SRC_TIF = "/home/z/my-project/download/map_pack"
OUT = "/tmp/my-project/geo/out"
PUB = "/home/z/my-project/public"
LAY = f"{PUB}/layers"
DAT = f"{PUB}/data"
os.makedirs(LAY, exist_ok=True)
os.makedirs(DAT, exist_ok=True)

# land mask from the WorldCover intermediate (same 100 m grid as all layers)
GM = np.load(f"{OUT}/grid_meta.npz")
_lc = np.load(f"{OUT}/worldcover.npz")["lc"]
# sanity: top row (north) must be dominated by sea (class 80)
assert _lc[0].tolist().count(80) / _lc.shape[1] > 0.5, "unexpected lc orientation"
LAND = ((_lc != 80) & (_lc != 0)).astype("float64")

# ---------- 1. Raster -> WGS84 colored PNG overlays ----------
import matplotlib
matplotlib.use("Agg")
from matplotlib import cm

def hexify(cmap, x):
    r, g, b, _ = cmap(x)
    return (int(r * 255), int(g * 255), int(b * 255))

def warp_to_wgs84(path):
    with rasterio.open(path) as src:
        data = src.read(1).astype("float64")
        nodata = src.nodata
        mask = np.ones_like(data, bool) if nodata is None else (data != nodata)
        if np.isnan(data).any():
            mask &= ~np.isnan(data)
        left, bottom, right, top = src.bounds
        transform_w, w, h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
        dst = np.full((h, w), np.nan)
        reproject(data, dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform_w, dst_crs="EPSG:4326",
                  src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.bilinear)
        dmask = np.full((h, w), np.nan)
        reproject(mask.astype("float64"), dmask, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform_w, dst_crs="EPSG:4326",
                  src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest)
        # land mask from ESA WorldCover grid (exclude open water=80, nodata=0)
        # lc grid: x0,y0 (SW corner), 100 m cells -> affine with north = y0 + ny*cell
        land_dst = np.zeros((h, w))
        reproject(LAND.astype("float64"), land_dst,
                  src_transform=Affine(GM["cell"], 0, GM["x0"], 0, -GM["cell"], GM["y0"] + GM["ny"] * GM["cell"]),
                  src_crs="EPSG:32632",
                  dst_transform=transform_w, dst_crs="EPSG:4326",
                  src_nodata=np.nan, dst_nodata=0, resampling=Resampling.nearest)
        valid = (dmask > 0.5) & (land_dst > 0.5)
        wgs_bounds = (transform_w.c, transform_w.f + h * transform_w.e,
                      transform_w.c + w * transform_w.a, transform_w.f)
        return dst, valid, wgs_bounds

LAYERS = [
    dict(id="risk",     tif="qabs_composite_fire_risk.tif",   cmap="YlOrRd",  vmin=0, vmax=100, alpha=0.62, unit="0-100", opac_default=0.55, on=True),
    dict(id="fuel",     tif="qabs_fuel_hazard.tif",           cmap="YlOrBr",  vmin=0, vmax=1,   alpha=0.6,  unit="0-1",   opac_default=0.45, on=False),
    dict(id="ignition", tif="qabs_ignition_proximity.tif",    cmap="viridis", vmin=0, vmax=1,   alpha=0.6,  unit="0-1",   opac_default=0.45, on=False),
    dict(id="burnfreq", tif="qabs_burn_frequency_2021_2025.tif", cmap="Reds", vmin=0, vmax=3,   alpha=0.6,  unit="fires", opac_default=0.5,  on=False),
    dict(id="burn26",   tif="qabs_burned_2026.tif",           cmap=None,      vmin=0, vmax=1,   alpha=0.55, unit="1=burned", opac_default=0.7, on=True),
    dict(id="tslb",     tif="qabs_time_since_burn.tif",       cmap="Greens",  vmin=0, vmax=6,   alpha=0.6,  unit="years", opac_default=0.45, on=False),
    dict(id="elev",     tif="qabs_elevation.tif",             cmap="terrain", vmin=None, vmax=None, alpha=0.55, unit="m",   opac_default=0.4,  on=False),
    dict(id="slope",    tif="qabs_slope_degrees.tif",         cmap="Purples", vmin=None, vmax=None, alpha=0.55, unit="deg", opac_default=0.4,  on=False),
]

bounds_union = None
meta = []
for L in LAYERS:
    arr, valid, ub = warp_to_wgs84(f"{SRC_TIF}/{L['tif']}")
    b = [ub[1], ub[0], ub[3], ub[2]]  # south, west, north, east
    if bounds_union is None:
        bounds_union = list(b)
    else:
        bounds_union = [min(bounds_union[0], b[0]), min(bounds_union[1], b[1]),
                        max(bounds_union[2], b[2]), max(bounds_union[3], b[3])]
    v = arr[valid]
    vmin, vmax = L["vmin"], L["vmax"]
    if vmin is None: vmin = float(np.nanpercentile(v, 2))
    if vmax is None: vmax = float(np.nanpercentile(v, 98))
    rng = vmax - vmin if vmax > vmin else 1.0
    h, w = arr.shape
    if L["cmap"] is None:  # binary burned: solid scarlet
        img = np.zeros((h, w, 4), dtype=np.uint8)
        img[valid & (arr > 0.5)] = (220, 38, 38, int(255 * L["alpha"]))
        legend = dict(kind="binary", stops=[dict(v=1, color="#dc2626")])
    else:
        cmap = cm.get_cmap(L["cmap"])
        norm = np.clip((arr - vmin) / rng, 0, 1)
        norm[norm < 0.004] = 0  # kill denormal near-zero pixels (sea artifacts)
        rgba = cmap(norm)
        a = (norm * L["alpha"]) * 255
        a[~valid] = 0
        a[(valid) & (a > 0) & (a < 46)] = 46
        img = (rgba * 255).astype(np.uint8)
        img[..., 3] = a.astype(np.uint8)
        legend = dict(kind="gradient", stops=[dict(v=float(vmin + (vmax - vmin) * i / 4),
                     color='#%02x%02x%02x' % hexify(cmap, i / 4)[:3]) for i in range(5)])
    im = Image.fromarray(img, "RGBA")
    im = im.resize((w * 2, h * 2), Image.NEAREST)
    im.save(f"{LAY}/{L['id']}.png")
    meta.append(dict(id=L["id"], png=f"/layers/{L['id']}.png", bounds=b, vmin=float(vmin), vmax=float(vmax),
                     unit=L["unit"], opacity=L["opac_default"], on=L["on"], legend=legend))
    print(f"{L['id']:9s} {w}x{h} -> bounds {b} vmin={vmin:.2f} vmax={vmax:.2f}")

with open(f"{DAT}/layers.json", "w") as f:
    json.dump(dict(corridor=bounds_union, layers=meta), f)

# ---------- 2. Fire weather CSVs -> JSON ----------
stations = ["Nefza", "Tabarka", "Fernana", "Ain_Draham"]
fw = {}
xstats = {}
for st in stations:
    fw[st] = {}
    xstats[st] = {}
    for yr in ["2025", "2026"]:
        rows = []
        with open(f"/home/z/my-project/download/fireweather_{st}_{yr}.csv") as f:
            hdr = f.readline().strip().split(",")
            for line in f:
                p = line.strip().split(",")
                if len(p) != len(hdr): continue
                rows.append(dict(date=p[0], tmax=float(p[1]), rh=float(p[2]), wind=float(p[3]),
                                 precip=float(p[4]), cbi=float(p[5])))
        fw[st][yr] = rows
        cbi = [r["cbi"] for r in rows]
        xstats[st][yr] = dict(extreme_days=int(sum(c >= 90 for c in cbi)),
                              high_days=int(sum(70 <= c < 90 for c in cbi)),
                              peak_cbi=round(max(cbi), 1),
                              peak_tmax=round(max(r["tmax"] for r in rows), 1),
                              n=len(rows))
with open(f"{DAT}/fireweather.json", "w") as f:
    json.dump(dict(stations=stations, series=fw, stats=xstats), f)
print("weather:", json.dumps(xstats))

# ---------- 3. Sites ----------
s = json.load(open(f"{OUT}/siting.json"))
sirens_named = []
fallback = ["Coastal hamlet", "Sidi Mechreg", "Nefza"]
for i, sr in enumerate(s["sirens"]):
    nm = sr["name"] if sr["name"] not in ("", "unnamed hamlet") else fallback[i % 3]
    sirens_named.append(dict(id=f"S{i+1}", name=nm, lat=sr["lat"], lon=sr["lon"], pop2km=sr["pop2km"]))
sites = dict(nodes=s["nodes"], gateways=s["gateways"], sirens=sirens_named, coverage=s["coverage"])
with open(f"{DAT}/sites.json", "w") as f:
    json.dump(sites, f)

# ---------- 4. Analysis bundle ----------
burn = json.load(open(f"{OUT}/burn_stats.json"))
risk = json.load(open(f"{OUT}/risk_stats.json"))
with open(f"{DAT}/analysis.json", "w") as f:
    json.dump(dict(burn=burn, risk=risk), f)

# ---------- 5. PDF ----------
os.makedirs(f"{PUB}/report", exist_ok=True)
shutil.copy("/home/z/my-project/download/QABS_Wildfire_Risk_Atlas.pdf", f"{PUB}/report/QABS_Wildfire_Risk_Atlas.pdf")
print("PDF copied", os.path.getsize(f"{PUB}/report/QABS_Wildfire_Risk_Atlas.pdf"), "bytes")
print("DONE")
