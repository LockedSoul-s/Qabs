#!/usr/bin/env python3
"""QABS risk assessment - weighted multi-criteria fire-risk composite + zone ranking.
Risk = 100 * (0.35*fuel + 0.25*ignition + 0.20*terrain + 0.20*burn_activity)
Fire weather (Chandler Burning Index) is temporally uniform over the corridor and is
applied as seasonal context, not as a spatial layer (documented in the report).
Sensitivity check: +-0.05 weight perturbations -> rank stability of zones.
"""
import json
import numpy as np
from scipy import ndimage

OUT = "/home/z/my-project/geo/out"

def log(s): print(s, flush=True)

MASSIFS = {
    "Tabarka":          (36.954, 8.758),
    "Ain Draham":       (36.785, 8.467),
    "Fernana":          (36.648, 8.983),
    "Nefza-Cap Negro":  (37.070, 9.200),
    "Sejnane":          (37.185, 9.367),
}
PILOT = dict(lonmin=8.95, lonmax=9.30, latmin=36.98, latmax=37.20)

m = np.load(f"{OUT}/grid_meta.npz")
X0, Y0, NX, NY, CELL = float(m["x0"]), float(m["y0"]), int(m["nx"]), int(m["ny"]), float(m["cell"])

def weights_to_risk(w):
    fuel_h = 0.7 * fuel + 0.3 * (0.3 + 0.7 * np.clip(tslb, 0, 8) / 8.0)
    fuel_h = fuel_h * land
    terrain = (0.6 * np.clip(np.nan_to_num(slope) / 30.0, 0, 1) + 0.4 * af) * land
    burnact = np.clip(freq / 2.0, 0, 1) * land
    r = 100.0 * (w[0] * fuel_h + w[1] * ign + w[2] * terrain + w[3] * burnact)
    return np.clip(r, 0, 100).astype(np.float32)

if __name__ == "__main__":
    fuel = np.load(f"{OUT}/fuel.npz")["fuel"]
    t = np.load(f"{OUT}/terrain.npz")
    slope, sea = t["slope"], t["sea"]
    af = np.full_like(slope, 0.5); ok = t["aspect"] >= 0
    af[ok] = 0.2 + 0.8 * (0.5 * (1 - np.cos(np.radians(t["aspect"][ok] - 180.0))))
    o = np.load(f"{OUT}/osm_layers.npz", allow_pickle=True)
    ign = o["ign"]
    b = np.load(f"{OUT}/burns.npz")
    freq, tslb = b["freq"], b["tslb"]
    land = (~sea).astype(np.float32)
    wc = np.load(f"{OUT}/worldcover.npz")["lc"]
    land[wc == 0] = 0.0

    W = (0.35, 0.25, 0.20, 0.20)
    risk = weights_to_risk(W)

    # ---------------- zone map (nearest massif within 12 km, else 'Other corridor')
    yy, xx = np.mgrid[0:NY, 0:NX]
    lon = X0 + (xx + 0.5) * CELL
    lat = Y0 + (NY - yy - 0.5) * CELL
    import pyproj
    tr = pyproj.Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
    lon_g, lat_g = tr.transform(X0 + (xx + 0.5) * CELL, Y0 + (NY - yy - 0.5) * CELL)
    zone = np.full((NY, NX), "Other corridor", dtype=object)
    best = np.full((NY, NX), 1e9, np.float32)
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    for name, (mlat, mlon) in MASSIFS.items():
        az12, az21, dist = geod.inv(np.full(lon_g.shape, mlon), np.full(lat_g.shape, mlat), lon_g, lat_g)
        closer = (dist < best) & (dist <= 12000.0)
        zone[closer] = name
        best = np.where(closer, dist, best)

    # 2026 burns
    burn26 = b["burn_2026"] if "burn_2026" in b.files else np.zeros_like(freq, bool)

    def zone_stats(r):
        rows = []
        names = list(MASSIFS) + ["Other corridor"]
        for name in names:
            sel = (zone == name) & (land > 0) & (wc != 0)
            wild = sel & np.isin(wc, [10, 20, 30])
            if sel.sum() == 0:
                continue
            rows.append(dict(
                zone=name,
                area_ha=float(sel.sum() * 1.0),
                wildland_ha=float(wild.sum() * 1.0),
                mean_risk=float(np.nanmean(r[sel])),
                p90_risk=float(np.nanpercentile(r[sel], 90)),
                high_risk_ha=float(((r >= 70) & sel).sum() * 1.0),
                burn21_25_ha=float(((freq > 0) & sel).sum() * 1.0),
                burn2026_ha=float((burn26 & sel).sum() * 1.0),
                mean_tslb=float(np.nanmean(tslb[sel & wild]) if wild.sum() else 0)))
        return sorted(rows, key=lambda d: -d["mean_risk"])

    zs = zone_stats(risk)
    zs.sort(key=lambda r: -r["mean_risk"])
    for r in zs:
        log(f"{r['zone']:16s} mean {r['mean_risk']:5.1f}  hi-risk {r['high_risk_ha']:8,.0f} ha  "
            f"burned26 {r['burn2026_ha']:7,.0f} ha")

    # pilot AOI stats
    psel = ((lon_g >= PILOT["lonmin"]) & (lon_g <= PILOT["lonmax"]) &
            (lat_g >= PILOT["latmin"]) & (lat_g <= PILOT["latmax"]) & (land > 0) & (wc != 0))
    pilot_stats = dict(
        area_ha=float(psel.sum()),
        mean_risk=float(np.nanmean(risk[psel])),
        high_risk_ha=float(((risk >= 70) & psel).sum()),
        burn2026_ha=float((burn26 & psel).sum()),
        wildland_ha=float((psel & np.isin(wc, [10, 20, 30])).sum()))
    log(f"pilot AOI: mean {pilot_stats['mean_risk']:.1f}, hi-risk {pilot_stats['high_risk_ha']:,} ha, "
        f"burned26 {pilot_stats['burn2026_ha']:,} ha")

    # ---------------- sensitivity: weight perturbations
    perts = {"base": W,
             "fuel+0.05": (0.40, 0.25, 0.175, 0.175),
             "ign+0.05": (0.325, 0.30, 0.1875, 0.1875),
             "terrain+0.05": (0.325, 0.1875, 0.25, 0.1875),
             "burn+0.05": (0.325, 0.1875, 0.1875, 0.30)}
    samp = (slice(None, None, 7), slice(None, None, 7))  # decimated sample
    base_s = risk[samp]
    sens = []
    from scipy.stats import spearmanr
    for nm, w in perts.items():
        r2 = weights_to_risk(w)[samp]
        rho = spearmanr(base_s.ravel(), r2.ravel()).statistic
        rank_order = [d["zone"] for d in zone_stats(weights_to_risk(w)) ]
        sens.append(dict(name=nm, spearman=float(rho), zone_order=rank_order))
        log(f"sens {nm:14s} rho={rho:.4f}")
    base_order = [d["zone"] for d in zs]
    rank_stable = all(s["zone_order"][:5] == base_order[:5] for s in sens[1:])
    log(f"zone rank stability across perturbations: {rank_stable}")

    np.savez_compressed(f"{OUT}/risk.npz", risk=risk, zone=zone.astype(str),
                        burn2026=burn26)
    json.dump(dict(weights=W, zones=zs, pilot=pilot_stats, sensitivity=sens,
                   rank_stable=bool(rank_stable)),
              open(f"{OUT}/risk_stats.json", "w"), indent=1)
    log("saved risk.npz + risk_stats.json")
