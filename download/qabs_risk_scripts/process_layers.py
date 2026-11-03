#!/usr/bin/env python3
"""QABS risk assessment - static layers on the corridor grid (100 m, UTM32N).
Terrain (elev/slope/aspect/hillshade) from AWS Terrarium DEM; fuel hazard from
ESA WorldCover 2021; ignition proximity + access remoteness from Geofabrik OSM
shapefiles; settlement population from WorldPop. Saves geo/out/layers.npz.
"""
import numpy as np
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin as tf_from_origin
from scipy import ndimage

ROOT = "/home/z/my-project/geo"
OUT = f"{ROOT}/out"
UTM = "EPSG:32632"
CORRIDOR = dict(lonmin=8.35, lonmax=9.45, latmin=36.55, latmax=37.25)
BBOX = (CORRIDOR["lonmin"], CORRIDOR["latmin"], CORRIDOR["lonmax"], CORRIDOR["latmax"])

m = np.load(f"{OUT}/grid_meta.npz")
X0, Y0, NX, NY, CELL = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"]), float(m["cell"])
grid_tf = tf_from_origin(X0, Y0 + NY * CELL, CELL, CELL)

def log(s): print(s, flush=True)

# ---------------------------------------------------------------- terrain
def terrain():
    d = np.load(f"{OUT}/dem.npz")
    dem, bounds = d["dem"], d["bounds"]
    lon_l, lat_b, lon_r, lat_t = [float(b) for b in bounds]
    src_tf = tf_from_origin(lon_l, lat_t, (lon_r - lon_l) / dem.shape[1], (lat_t - lat_b) / dem.shape[0])
    elev = np.full((NY, NX), np.nan, dtype=np.float32)
    reproject(dem, elev, src_transform=src_tf, src_crs="EPSG:4326",
              dst_transform=grid_tf, dst_crs=UTM, resampling=Resampling.bilinear,
              src_nodata=np.nan, dst_nodata=np.nan)
    # terrarium includes bathymetry: sea is negative -> set to 0, build land mask
    sea = elev < -1.0
    elev[sea] = 0.0
    gy, gx = np.gradient(elev, CELL, CELL)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    slope[sea] = np.nan
    # aspect: direction of steepest descent, converted to compass bearing
    asp = np.degrees(np.arctan2(gy, gx))
    aspect = (450.0 - asp) % 360.0
    aspect[slope < 0.5] = -1.0  # flat
    # south-facing dryness factor: S=1.0, E/W=0.6, N=0.2; flats 0.5
    af = np.full_like(slope, 0.5)
    ok = aspect >= 0
    af[ok] = 0.2 + 0.8 * (0.5 * (1 - np.cos(np.radians(aspect[ok] - 180.0))))
    # hillshade (az 315, alt 45)
    az, alt = np.radians(315.0), np.radians(45.0)
    shaded = (np.sin(alt) * np.cos(slope) +
              np.cos(alt) * np.sin(slope) * np.cos(az - np.radians(450.0 - asp)))
    hs = np.clip(shaded, 0, 1) * 255
    hs[sea] = 0
    np.savez_compressed(f"{OUT}/terrain.npz", elev=elev, slope=slope,
                        aspect=aspect, hillshade=hs.astype(np.uint8), sea=sea)
    log(f"terrain: elev {np.nanmax(elev):.0f} m max; slope p95 {np.nanpercentile(slope,95):.1f} deg")

# ---------------------------------------------------------------- fuel
# ESA WorldCover 2021 classes -> fuel hazard score 0..1 (cork-oak/pine forest high)
WC_FUEL = {10: 0.95, 95: 0.90, 20: 0.85, 30: 0.60, 40: 0.45, 50: 0.08,
           60: 0.15, 70: 0.30, 80: 0.00, 90: 0.05, 100: 0.20, 0: 0.40}
FUEL_NAME = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
             50: "Built-up", 60: "Bare", 80: "Water", 90: "Wetland", 0: "No data"}

def fuel():
    wc = np.load(f"{OUT}/worldcover.npz")["lc"]
    fuel = np.vectorize(WC_FUEL.get)(wc).astype(np.float32)
    np.savez_compressed(f"{OUT}/fuel.npz", fuel=fuel)
    for c in np.unique(wc):
        pct = np.mean(wc == c) * 100
        if pct >= 0.5:
            log(f"  WC {int(c):3d} {FUEL_NAME.get(int(c),'?'):12s} {pct:5.1f}%  fuel={WC_FUEL.get(int(c))}")
    log("fuel saved")

# ---------------------------------------------------------------- OSM
def osm_layers():
    import geopandas as gpd
    import pyogrio
    CRS_LATLON = "EPSG:4326"

    def read(fname, layer_filter=None):
        path = f"{ROOT}/raw/tunisia-latest-free/{fname}"
        g = pyogrio.read_dataframe(path, bbox=BBOX)
        if layer_filter is not None:
            g = g[g["fclass"].isin(layer_filter)]
        if len(g) == 0:
            return g
        return g.to_crs(UTM)

    trails  = read("gis_osm_roads_free_1.shp", ["track", "path", "footway", "bridleway", "steps", "pedestrian"])
    minor   = read("gis_osm_roads_free_1.shp", ["unclassified", "service", "living_street", "residential",
                                                "tertiary", "tertiary_link"])
    major   = read("gis_osm_roads_free_1.shp", ["secondary", "secondary_link", "primary", "primary_link",
                                                "trunk", "trunk_link", "motorway", "motorway_link"])
    pois    = read("gis_osm_pois_free_1.shp", ["picnic_site", "camp_site", "viewpoint", "attraction"])
    places  = read("gis_osm_places_free_1.shp", ["town", "village", "hamlet", "suburb", "isolated_dwelling"])
    towers  = read("gis_osm_pois_free_1.shp", ["communications_tower", "mast"])
    log(f"osm: trails {len(trails)}, minor {len(minor)}, major {len(major)}, "
        f"poi {len(pois)}, places {len(places)}, towers {len(towers)}")

    def line_mask(gdf):
        if gdf is None or len(gdf) == 0:
            return np.zeros((NY, NX), dtype=bool)
        shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
        return rasterize_all(shapes)

    def rasterize_all(shapes):
        from rasterio.features import rasterize
        msk = rasterize(shapes, out_shape=(NY, NX), transform=grid_tf,
                        fill=0, all_touched=True, dtype="uint8")
        return msk.astype(bool)

    def point_mask(gdf):
        if gdf is None or len(gdf) == 0:
            return np.zeros((NY, NX), dtype=bool)
        shapes = [(geom, 1) for geom in gdf.geometry if geom is not None]
        return rasterize_all(shapes)

    def dist(mask):
        return ndimage.distance_transform_edt(~mask, sampling=(CELL, CELL)).astype(np.float32)

    m_trail, m_minor, m_major = line_mask(trails), line_mask(minor), line_mask(major)
    m_poi, m_place = point_mask(pois), point_mask(places)
    # residential areas as settlement proxy
    try:
        res = read("gis_osm_landuse_a_free_1.shp", ["residential"])
        m_res = line_mask(res) if False else (rasterize_all([(g, 1) for g in res.geometry if g is not None])
                                              if len(res) else np.zeros((NY, NX), bool))
    except Exception:
        m_res = np.zeros((NY, NX), bool)
    m_settle = m_place | m_res

    d_trail, d_minor, d_major = dist(m_trail), dist(m_minor), dist(m_major)
    d_poi = dist(ndimage.binary_dilation(m_poi, iterations=1))
    d_settle = dist(m_settle)

    # ignition proximity: max of weighted exponential decays around human ignition points
    ign = np.zeros((NY, NX), dtype=np.float32)
    for wgt, dec, distf in ((1.00, 250.0, d_poi),      # picnic / camp sites (doc: designated bbq spots)
                            (1.00, 250.0, d_trail),    # tracks, paths, footways
                            (0.90, 350.0, d_minor),    # minor roads, forest tracks
                            (0.50, 200.0, d_major),    # roadside (power-line sparks, cigarettes)
                            (0.80, 400.0, d_settle)):  # field edges, cooking near hamlets
        ign = np.maximum(ign, (wgt * np.exp(-distf / dec)).astype(np.float32))
    ign[~m_res] = ign[~m_res]
    d_access = np.minimum(d_minor, d_major).astype(np.float32)  # motorable access distance

    # settlement table with population (WorldPop sum in 2 km)
    pop = np.load(f"{OUT}/worldpop.npz")["pop"]
    rows = []
    for _, r in places.iterrows():
        col = int((r.geometry.x - X0) // CELL); row_ = int((Y0 + NY * CELL - r.geometry.y) // CELL)
        if not (0 <= col < NX and 0 <= row_ < NY):
            continue
        r0, r1 = max(0, row_ - 20), min(NY, row_ + 20)
        c0, c1 = max(0, col - 20), min(NX, col + 20)
        p = float(pop[r0:r1, c0:c1].sum())
        rows.append(dict(name=str(r.get("name", "")), fclass=str(r["fclass"]), lon=float(r.geometry.x),
                         lat=float(r.geometry.y), row=row_, col=col, pop2km=round(p)))
    np.savez_compressed(f"{OUT}/osm_layers.npz",
                        ign=ign, d_trail=d_trail, d_minor=d_minor, d_major=d_major,
                        d_poi=d_poi, d_settle=d_settle, d_access=d_access,
                        m_settle=m_settle, settlements=np.array(rows, dtype=object),
                        poi=np.array([dict(name=str(r.get("name", "")), fclass=str(r["fclass"]),
                                           lon=float(r.geometry.x), lat=float(r.geometry.y))
                                      for _, r in pois.iterrows()], dtype=object),
                        towers=np.array([dict(lon=float(r.geometry.x), lat=float(r.geometry.y))
                                         for _, r in towers.iterrows()], dtype=object))
    log(f"ignition score: p95={np.percentile(ign,95):.2f} max={ign.max():.2f}; "
        f"settlements kept: {len(rows)}")

if __name__ == "__main__":
    terrain(); fuel(); osm_layers()
    log("layers done")
