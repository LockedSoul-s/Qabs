#!/usr/bin/env python3
"""
QABS Wildfire Risk Assessment - Data Fetch Pipeline
Public satellite / geodata sources (all open, no API keys):
  1. Sentinel-2 L2A COGs via Earth Search STAC (AWS Open Data)  -> NBR stack 2020-2026 (dNBR fire history)
  2. AWS Terrarium DEM tiles                                     -> elevation / slope
  3. ESA WorldCover 2021 (AWS open)                              -> fuel types
  4. WorldPop TUN 2020                                           -> population (last-mile exposure)
  5. Geofabrik OSM Tunisia extract (shapefiles)                  -> roads, tracks, trails, picnic sites, hamlets
Outputs cached under /home/z/my-project/geo/
"""
import io, json, os, sys, time, zipfile, urllib.request
import numpy as np

ROOT   = "/home/z/my-project/geo"
RAW    = f"{ROOT}/raw"
OUT    = f"{ROOT}/out"
os.makedirs(RAW, exist_ok=True); os.makedirs(OUT, exist_ok=True)

# ---------- AOIs ----------
CORRIDOR = dict(lonmin=8.35, lonmax=9.45, latmin=36.55, latmax=37.25)   # Kroumirie-Mogods + Sejnane
PILOT    = dict(lonmin=8.95, lonmax=9.30, latmin=36.98, latmax=37.20)   # Nefza / Cap Negro deep-dive
S2_TILES = ["32SMF", "32SMG", "32SNF", "32SNG"]
YEARS    = list(range(2020, 2027))   # 2020 baseline -> burn years 2021..2026
CELL     = 100.0                     # metres
UTM      = "EPSG:32632"

def log(msg): print(msg, flush=True)

def fetch(url, dest=None, tries=3, timeout=120):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "qabs-risk-mapping/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if dest:
                with open(dest, "wb") as f: f.write(data)
            return data
        except Exception as e:
            log(f"  retry {i+1} for {url[:80]}: {e}")
            time.sleep(4)
    raise RuntimeError(f"fetch failed: {url}")

# ---------------------------------------------------------------- grids
def corridor_grid():
    """(grid transform, nx, ny) for the corridor at 100 m in UTM 32N - cached npz."""
    p = f"{OUT}/grid_meta.npz"
    if os.path.exists(p):
        m = np.load(p); return m
    import rasterio
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", UTM, always_xy=True)
    x0, y0 = tr.transform(CORRIDOR["lonmin"], CORRIDOR["latmin"])
    x1, y1 = tr.transform(CORRIDOR["lonmax"], CORRIDOR["latmax"])
    nx, ny = int(round((x1 - x0) / CELL)), int(round((y1 - y0) / CELL))
    np.savez(p, x0=x0, y0=y0, nx=nx, ny=ny, cell=CELL)
    return np.load(p)

# ---------------------------------------------------------------- STAC: scene inventory
def stac_scene_inventory():
    """Best (lowest cloud) summer scene per S2 tile per year; save metadata."""
    inv_path = f"{OUT}/s2_scenes.json"
    if os.path.exists(inv_path):
        log("scene inventory cached"); return json.load(open(inv_path))
    inv = {}
    for yr in YEARS:
        dt = f"{yr}-06-15T00:00:00Z/{yr}-10-05T00:00:00Z"
        best = {}
        for page in range(1, 6):
            body = json.dumps({"bbox": [CORRIDOR["lonmin"], CORRIDOR["latmin"], CORRIDOR["lonmax"], CORRIDOR["latmax"]],
                               "datetime": dt, "collections": ["sentinel-2-l2a"], "limit": 100, "page": page}).encode()
            req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r: d = json.load(r)
            for f in d.get("features", []):
                tid = f["id"].split("_")[1]
                if tid not in S2_TILES: continue
                cc = f["properties"]["eo:cloud_cover"]
                ent = dict(id=f["id"], cc=round(cc, 1), datetime=f["properties"]["datetime"][:10],
                           assets={k: f["assets"][k]["href"] for k in
                                   ("nir", "swir22", "scl", "red", "green", "blue") if k in f["assets"]})
                lst = best.setdefault(tid, [])
                lst.append(ent); lst.sort(key=lambda e: e["cc"]); del lst[3:]
            if len(d.get("features", [])) < 100: break
        inv[str(yr)] = best
        log(f"{yr}: " + ", ".join(f"{t}={[e['cc'] for e in v]}" for t, v in best.items()))
    json.dump(inv, open(inv_path, "w"), indent=1)
    return inv

# ---------------------------------------------------------------- Sentinel-2 NBR stack
def s2_nbr_stack(inv):
    """Decimated windowed reads (B08,B12,SCL) per tile/year -> annual NBR mosaics on the corridor grid.
    Per-year caching: geo/out/nbr_{year}.npz so re-runs skip completed years."""
    out_path = f"{OUT}/nbr_stack.npz"
    if os.path.exists(out_path):
        log("NBR stack cached"); return np.load(out_path)
    import rasterio
    from rasterio.warp import reproject, Resampling, transform_bounds as tb
    from rasterio.windows import from_bounds, bounds as win_bounds

    m = corridor_grid(); x0, y0, nx, ny = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"])
    grid_tf = rasterio.transform.from_origin(x0, y0 + ny * CELL, CELL, CELL)

    def read_band(src, href_label, scale=True):
        b = tb(src.crs, UTM, *src.bounds, densify_pts=21)
        # intersect with corridor bbox in UTM
        b = (max(b[0], x0), max(b[1], y0), min(b[2], x0 + nx * CELL), min(b[3], y0 + ny * CELL))
        if b[2] <= b[0] or b[3] <= b[1]: return None
        win = from_bounds(*b, src.transform)
        scale_f = 40.0  # decimate ~40x (10m -> ~400m), then average-reproject to 100 m grid
        out_h = max(1, int(win.height / scale_f)); out_w = max(1, int(win.width / scale_f))
        small = src.read(1, window=win, out_shape=(out_h, out_w)).astype(np.float32)
        if scale:
            if small.min() < 0:  # processing baseline >= 04.00 offset
                small = small + 1000.0
            small = np.clip(small, 0, 10000) / 10000.0
        wb = win_bounds(win, src.transform)
        stf = rasterio.transform.from_origin(wb[0], wb[3], (wb[2] - wb[0]) / out_w, (wb[3] - wb[1]) / out_h)
        dst = np.full((ny, nx), np.nan, dtype=np.float32)
        reproject(small, dst, src_transform=stf, src_crs=src.crs, dst_transform=grid_tf, dst_crs=UTM,
                  resampling=Resampling.average if scale else Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
        return dst

    stack = np.full((len(YEARS), ny, nx), np.nan, dtype=np.float32)
    targets = [(yi, yr) for yi, yr in enumerate(YEARS)]
    for yi, yr in targets:
        yc = f"{OUT}/nbr_{yr}.npz"
        if os.path.exists(yc):
            stack[yi] = np.load(yc)["nbr"]
            log(f"NBR {yr}: cached")
            continue
        for tid, scenes in inv[str(yr)].items():
            merged = np.full((ny, nx), np.nan, dtype=np.float32)
            for si, meta in enumerate(scenes):
                try:
                    bands = {}
                    for key in ("nir", "swir22", "scl"):
                        with rasterio.open(meta["assets"][key]) as src:
                            bands[key] = read_band(src, key, scale=(key != "scl"))
                    if bands["nir"] is None: continue
                    nir, swir, scl = bands["nir"], bands["swir22"], bands["scl"]
                    den = nir + swir
                    nbr = np.where((den > 0.02) & ~np.isnan(den), (nir - swir) / den, np.nan)
                    scl_v = np.where(np.isnan(scl), 255.0, scl)
                    bad = np.isin(scl_v.astype(np.uint8), [0, 1, 3, 8, 9, 10, 255])
                    nbr[bad] = np.nan
                    msk = ~np.isnan(nbr) & np.isnan(merged)
                    merged[msk] = nbr[msk]
                    if np.mean(~np.isnan(merged)) > 0.85:
                        break
                except Exception as e:
                    log(f"  WARN {yr}/{tid}/{meta['id']}: {e}"); continue
            msk = ~np.isnan(merged)
            stack[yi][msk] = np.where(np.isnan(stack[yi][msk]), merged[msk], (stack[yi][msk] + merged[msk]) / 2.0)
        np.savez_compressed(yc, nbr=stack[yi])
        log(f"NBR {yr}: valid {np.mean(~np.isnan(stack[yi]))*100:.1f}%")
    np.savez_compressed(out_path, nbr=stack, years=np.array(YEARS))
    return np.load(out_path)

# ---------------------------------------------------------------- DEM
def fetch_dem():
    out_path = f"{OUT}/dem.npz"
    if os.path.exists(out_path):
        log("DEM cached"); return np.load(out_path)
    import math
    from PIL import Image
    Z = 12
    def ll2tile(lat, lon, z):
        n = 2 ** z
        return ((lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    tx0, ty0 = ll2tile(CORRIDOR["latmax"], CORRIDOR["lonmin"], Z)
    tx1, ty1 = ll2tile(CORRIDOR["latmin"], CORRIDOR["lonmax"], Z)
    rows = []
    for y in range(int(ty0), int(ty1) + 1):
        row = []
        for x in range(int(tx0), int(tx1) + 1):
            data = fetch(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png")
            im = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float32)
            row.append(im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768)
        rows.append(np.hstack(row))
    dem = np.vstack(rows)
    n = 2 ** Z
    lon_l = int(tx0) / n * 360 - 180
    lon_r = (int(tx1) + 1) / n * 360 - 180
    lat_t = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * int(ty0) / n))))
    lat_b = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (int(ty1) + 1) / n))))
    np.savez_compressed(out_path, dem=dem, bounds=[lon_l, lat_b, lon_r, lat_t])
    log(f"DEM {dem.shape} bounds {lon_l:.3f},{lat_b:.3f},{lon_r:.3f},{lat_t:.3f}")
    return np.load(out_path)

# ---------------------------------------------------------------- WorldCover
def fetch_worldcover():
    out_path = f"{OUT}/worldcover.npz"
    if os.path.exists(out_path):
        log("WorldCover cached"); return np.load(out_path)
    import rasterio
    from rasterio.warp import reproject, Resampling
    m = corridor_grid(); x0, y0, nx, ny = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"])
    grid_tf = rasterio.transform.from_origin(x0, y0 + ny * CELL, CELL, CELL)
    lc = np.zeros((ny, nx), dtype=np.uint8)
    for tile in ["N36E006", "N36E009"]:
        url = f"/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
        with rasterio.open(url) as src:
            dst = np.zeros((ny, nx), dtype=np.uint8)
            reproject(rasterio.band(src, 1), dst, dst_transform=grid_tf, dst_crs=UTM,
                      resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
            lc[lc == 0] = dst[lc == 0]
    np.savez_compressed(out_path, lc=lc)
    log(f"WorldCover classes: {np.unique(lc)}")
    return np.load(out_path)

# ---------------------------------------------------------------- WorldPop
def fetch_worldpop():
    out_path = f"{OUT}/worldpop.npz"
    if os.path.exists(out_path):
        log("WorldPop cached"); return np.load(out_path)
    import rasterio
    from rasterio.warp import reproject, Resampling
    m = corridor_grid(); x0, y0, nx, ny = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"])
    grid_tf = rasterio.transform.from_origin(x0, y0 + ny * CELL, CELL, CELL)
    url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/TUN/tun_ppp_2020.tif"
    local = f"{RAW}/tun_ppp_2020.tif"
    if not os.path.exists(local):
        log("downloading WorldPop TUN (~95 MB, resume-safe)...")
        fetch(url, local, timeout=600)
    with rasterio.open(local) as src:
        log(f"worldpop res {src.res} {src.crs}")
        pop = np.zeros((ny, nx), dtype=np.float32)
        reproject(rasterio.band(src, 1), pop, dst_transform=grid_tf, dst_crs=UTM,
                  resampling=Resampling.bilinear, src_nodata=-99999.0, dst_nodata=0.0)
    pop[pop < 0] = 0
    np.savez_compressed(out_path, pop=pop)
    log(f"WorldPop total in corridor: {pop.sum():,.0f}")
    return np.load(out_path)

# ---------------------------------------------------------------- OSM (Geofabrik)
def fetch_osm():
    zip_path = f"{RAW}/tunisia-latest-free.shp.zip"
    if not os.path.exists(f"{RAW}/tunisia-latest-free/gis_osm_roads_free_1.shp"):
        if not os.path.exists(zip_path):
            log("downloading Geofabrik Tunisia (~175 MB)...")
            fetch("https://download.geofabrik.de/africa/tunisia-latest-free.shp.zip", zip_path, timeout=600)
        with zipfile.ZipFile(zip_path) as z: z.extractall(f"{RAW}/tunisia-latest-free")
    log("OSM extract ready")

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("all", "osm"):        fetch_osm()
    if step in ("all", "dem"):        fetch_dem()
    if step in ("all", "worldcover"): fetch_worldcover()
    if step in ("all", "worldpop"):   fetch_worldpop()
    if step in ("all", "s2"):
        inv = stac_scene_inventory()
        s2_nbr_stack(inv)
    log("DONE")
